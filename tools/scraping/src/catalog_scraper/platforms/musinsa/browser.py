"""Public-page browser collector. No login, private endpoints, or challenge bypass."""

import re

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from .parser import validate_source_url

CATEGORY_SELECTOR = (
    'main [class*="Category__Wrap-"] '
    'a[data-button-id="category_navi"][data-section-name="cate_navi"]'
)

SNAPSHOT_JS = r"""(productUrl) => {
    const text = node => node?.textContent?.trim() || '';
    const definitions = root => Object.fromEntries(
        Array.from(root?.querySelectorAll('dt') || [], dt =>
            [text(dt), text(dt.nextElementSibling?.tagName === 'DD' ? dt.nextElementSibling : null)])
    );
    const id = new URL(productUrl).pathname.split('/').filter(Boolean).pop();
    let structured = null;
    for (const script of document.querySelectorAll('script[type="application/ld+json"]')) {
        let data;
        try { data = JSON.parse(script.textContent); } catch { continue; }
        const entries = Array.isArray(data) ? data : (data['@graph'] || [data]);
        structured = entries.find(entry => entry['@type'] === 'Product' &&
            (String(entry.sku) === id || entry['@id'] === productUrl || entry.url === productUrl));
        if (structured) break;
    }
    const gallery = document.querySelector('[data-pdp-image-surface="main"]');
    const noticeButton = Array.from(document.querySelectorAll('button'))
        .find(button => text(button) === '상품 고시 정보안내');
    const notice = noticeButton ? document.getElementById(noticeButton.getAttribute('aria-controls')) : null;
    const tableWrap = document.querySelector('[class*="ActualSizeTable__Wrap"]');
    const standard = document.querySelector('[class*="StandardSizeTable__Wrap"]');
    const categoryMap = new Map();
    for (const link of document.querySelectorAll(
        'main [class*="Category__Wrap-"] a[data-button-id="category_navi"][data-section-name="cate_navi"]'
    )) {
        const url = new URL(link.href);
        if (url.protocol !== 'https:' || !['www.musinsa.com', 'musinsa.com'].includes(url.hostname)
            || url.searchParams.has('brand')) continue;
        const code = url.pathname.match(/^\/category\/(\d+)\/?$/)?.[1];
        const name = link.getAttribute('data-category-name')?.trim() || text(link);
        if (code && name && !categoryMap.has(code)) categoryMap.set(code, {code, name});
    }
    const materialInfo = {};
    for (const header of document.querySelectorAll('main ul[class^="MaterialInfo__RowHeaderWrap-"]')) {
        const wrap = header.closest('[class^="MaterialInfo__MaterialWrap-"]');
        const labels = Array.from(header.children, text);
        const rows = wrap?.querySelectorAll('table[class^="MaterialInfo__MaterialTable-"] tr') || [];
        const fitIndex = labels.indexOf('핏');
        if (fitIndex < 0 || !rows[fitIndex]) continue;
        const selected = Array.from(rows[fitIndex].querySelectorAll('td')).filter(td => {
            if (td.getAttribute('aria-selected') === 'true' || td.dataset.selected === 'true') return true;
            // Observed selected-cell background; random generated class suffixes are not stable.
            return getComputedStyle(td).backgroundColor.replace(/\s/g, '') === 'rgba(36,94,255,0.1)';
        }).map(text).filter(Boolean);
        materialInfo['핏'] = Array.from(new Set([...(materialInfo['핏'] || []), ...selected]));
    }
    const offer = Array.isArray(structured?.offers) ? structured.offers[0] : structured?.offers;
    return {
        product_url: productUrl,
        name: text(document.querySelector('[class*="GoodsName-"]')) || structured?.name || '',
        brand: structured?.brand?.name || document.querySelector('meta[property="product:brand"]')?.content || null,
        categories: Array.from(categoryMap.values()),
        details: definitions(document.querySelector('main')),
        price_text: offer?.price != null ? `${offer.price} ${offer.priceCurrency || ''}`.trim() : null,
        price_source: offer?.price != null ? 'json_ld.offers' : null,
        images: Array.from(gallery?.querySelectorAll('img') || [], img => img.currentSrc || img.src),
        notice: definitions(notice),
        material_info: materialInfo,
        size_table: tableWrap ? {
            labels: Array.from(tableWrap.querySelectorAll('ul li'), text),
            headers: Array.from(tableWrap.querySelectorAll('thead th'), text),
            rows: Array.from(tableWrap.querySelectorAll('tbody tr'), row =>
                Array.from(row.querySelectorAll('td'), text))
        } : null,
        size_guide: standard ? {
            row_labels: Array.from(standard.querySelectorAll(':scope > ul > li'), text),
            rows: Array.from(standard.querySelectorAll('table tr'), row =>
                Array.from(row.querySelectorAll('th,td'), text)),
            description: Array.from(standard.querySelectorAll('[class*="DescriptionLi"]'), text).join('\n'),
        } : null,
        actual_size_tab_present: Array.from(document.querySelectorAll('[role="tab"]'))
            .some(tab => text(tab) === '실측 사이즈'),
        structured_data: structured,
    };
}"""


def navigate(page: Page, url: str) -> None:
    response = page.goto(url, wait_until="domcontentloaded", timeout=45000)
    if response is None or response.status >= 400:
        raise ValueError(f"상품 페이지 응답 오류: {response.status if response else 'no response'}")


def collect_product_links(page: Page, limit: int) -> list[str]:
    if limit <= 0:
        raise ValueError("limit은 1 이상이어야 합니다")
    urls: dict[str, None] = {}
    stale_scrolls = 0
    for _ in range(100):
        before = len(urls)
        for url in page.locator('main a[href*="/products/"]').evaluate_all(
            "links => links.map(link => link.href)"
        ):
            try:
                urls[validate_source_url(url, "product")] = None
            except ValueError:
                continue
            if len(urls) >= limit:
                return list(urls)
        stale_scrolls = stale_scrolls + 1 if len(urls) == before else 0
        if stale_scrolls >= 3:
            break
        page.mouse.wheel(0, 1600)
        page.wait_for_timeout(1000)
    return list(urls)


def collect_product(page: Page, url: str) -> dict:
    url = validate_source_url(url, "product")
    navigate(page, url)
    if validate_source_url(page.url, "product") != url:
        raise ValueError("요청한 상품 URL과 최종 상품 URL이 다릅니다")
    # Wait for hydrated product-specific elements, rather than unrelated recommendations.
    page.locator('[class*="GoodsName-"]').first.wait_for(timeout=30000)
    page.locator(CATEGORY_SELECTOR).first.wait_for(timeout=15000)
    page.locator('[data-pdp-image-surface="main"] img').first.wait_for(timeout=15000)
    size_button = page.get_by_role("button", name="사이즈", exact=True)
    if size_button.count():
        size_button.click()
    missing_evidence = None
    try:
        page.wait_for_function(
            """() =>
            document.querySelector('[class*="ActualSizeTable__Wrap"] tbody tr') ||
            document.querySelector('[class*="StandardSizeTable__Wrap"] table tr')
        """,
            timeout=15000,
        )
        actual_tab = page.get_by_role("tab", name="실측 사이즈", exact=True)
        if (
            actual_tab.count()
            and not page.locator('[class*="ActualSizeTable__Wrap"] tbody tr').count()
        ):
            actual_tab.click()
            page.locator('[class*="ActualSizeTable__Wrap"] tbody tr').first.wait_for(timeout=15000)
    except PlaywrightTimeoutError as error:
        missing = page.get_by_text(
            re.compile(r"(?:등록된 )?(?:실측 )?사이즈 정보가 없습니다|실측 정보를 제공하지")
        )
        if not missing.count():
            raise ValueError("실측 표 로딩 실패: 사이즈 없음으로 저장하지 않습니다") from error
        missing_evidence = missing.first.inner_text()
    notice_button = page.get_by_role("button", name="상품 고시 정보안내", exact=True)
    if notice_button.count():
        if notice_button.get_attribute("aria-expanded") != "true":
            notice_button.click()
        region_id = notice_button.get_attribute("aria-controls")
        page.locator(f'[id="{region_id}"] dt').first.wait_for(timeout=15000)
    snapshot = page.evaluate(SNAPSHOT_JS, url)
    snapshot["size_missing_evidence"] = None if snapshot["size_table"] else missing_evidence
    return snapshot


def collect_category(page: Page, url: str, limit: int) -> list[str]:
    url = validate_source_url(url, "category")
    navigate(page, url)
    page.locator('main a[href*="/products/"]').first.wait_for(timeout=30000)
    return collect_product_links(page, limit)


def collect_material_info(page: Page, url: str) -> dict:
    """Refresh selected product fit cells without replacing images or measurements."""
    url = validate_source_url(url, "product")
    navigate(page, url)
    if validate_source_url(page.url, "product") != url:
        raise ValueError("요청한 상품 URL과 최종 상품 URL이 다릅니다")
    page.locator('[class*="GoodsName-"]').first.wait_for(timeout=30000)
    page.locator(CATEGORY_SELECTOR).first.wait_for(timeout=15000)
    page.locator('[data-pdp-image-surface="main"] img').first.wait_for(timeout=15000)
    button = page.get_by_role("button", name="사이즈", exact=True)
    if button.count():
        button.click()
        page.wait_for_function(
            """() => document.querySelector('ul[class^="MaterialInfo__RowHeaderWrap-"]') ||
            document.querySelector('[class*="ActualSizeTable__Wrap"] tbody tr') ||
            document.querySelector('[class*="StandardSizeTable__Wrap"] table tr')""",
            timeout=15000,
        )
    # Give the product-specific panel time to hydrate; unknown remains unknown.
    page.wait_for_timeout(1000)
    return page.evaluate(SNAPSHOT_JS, url)["material_info"]
