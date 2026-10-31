import os

import pytest
from playwright.sync_api import sync_playwright

from catalog_scraper.platforms.musinsa.browser import SNAPSHOT_JS, collect_product_links
from catalog_scraper.platforms.musinsa.parser import parse_product


@pytest.fixture
def page():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=os.getenv("SCRAPER_BROWSER_CHANNEL") or None)
        page = browser.new_page()
        page.route("**/*", lambda route: route.abort())
        try:
            yield page
        finally:
            browser.close()


def test_dom_extraction_ignores_recommendations_and_reads_notice(page):
    # A local fixture, not a network test: recreate the observed DOM boundaries.
    page.set_content("""
      <script type="application/ld+json">{"@type":"Product","sku":"7428042","name":"보라색 티셔츠","brand":{"name":"런던다다"},"offers":{"price":75910,"priceCurrency":"KRW"}}</script>
      <main>
        <span class="GoodsName-sc-random">보라색 티셔츠</span>
        <div class="Category__Wrap-sc-random">
          <a data-button-id="category_navi" data-section-name="cate_navi" data-category-name="상의" href="https://www.musinsa.com/category/001">상의</a>
          <a data-button-id="category_navi" data-section-name="cate_navi" data-category-name="긴소매 티셔츠" href="https://www.musinsa.com/category/001010">긴소매 티셔츠</a>
        </div>
        <dl><div><dt>시즌</dt><dd>2025 FW</dd></div></dl>
        <div data-pdp-image-surface="main">
          <img src="https://image.msscdn.net/images/goods_img/20260930/7428042/front.jpg?w=1200">
        </div>
        <img src="https://image.msscdn.net/images/goods_img/20260930/7428042/recommendation.jpg">
        <button aria-controls="notice">상품 고시 정보안내</button>
        <div id="notice"><dl><dt>제품 소재</dt><dd>울 20%</dd></dl></div>
        <div class="ActualSizeTable__Wrap-sc-random">
          <ul><li>cm</li><li>내 사이즈</li><li>S</li></ul>
          <table><thead><tr><th>1총장</th></tr></thead>
          <tbody><tr><td>사이즈를 직접 입력해주세요</td></tr><tr><td>60</td></tr></tbody></table>
        </div>
      </main>
    """)
    snapshot = page.evaluate(SNAPSHOT_JS, "https://www.musinsa.com/products/7428042")
    product = parse_product(snapshot)
    assert product.name == "보라색 티셔츠"
    assert product.notice == {"제품 소재": "울 20%"}
    assert product.season_raw == "2025 FW"
    assert product.image_urls == [
        "https://image.msscdn.net/images/goods_img/20260930/7428042/front.jpg?w=1200"
    ]
    assert product.sizes[0].measurements == {"총장": 60}


def test_list_limits_unique_products_and_preserves_order(page):
    page.set_content("""<main>
      <a href="https://www.musinsa.com/products/10">A</a>
      <a href="https://www.musinsa.com/products/10">A duplicate</a>
      <a href="https://www.musinsa.com/products/20?ref=list">B</a>
      <a href="https://evil.test/products/30">external</a>
      <a href="https://www.musinsa.com/products/40">C</a>
    </main>""")
    assert collect_product_links(page, limit=2) == [
        "https://www.musinsa.com/products/10",
        "https://www.musinsa.com/products/20",
    ]


def test_collector_rejects_redirect_to_another_product(page):
    from catalog_scraper.platforms.musinsa.browser import collect_product

    page.unroute("**/*")
    page.route(
        "**/products/7428042",
        lambda route: route.fulfill(
            status=302, headers={"location": "https://www.musinsa.com/products/999"}
        ),
    )
    page.route(
        "**/products/999",
        lambda route: route.fulfill(
            content_type="text/html", body='<span class="GoodsName-sc-other">다른 상품</span>'
        ),
    )
    with pytest.raises(ValueError, match="상품 URL"):
        collect_product(page, "https://www.musinsa.com/products/7428042")


def test_category_path_excludes_other_sections_and_brand_filter_links(page):
    page.set_content("""
      <main>
        <a href="https://www.musinsa.com/category/104">더보기</a>
        <div class="Category__Wrap-sc-random">
          <span><a data-button-id="category_navi" data-section-name="cate_navi" data-category-name="상의" href="https://www.musinsa.com/category/001">상의</a></span>
          <span><a data-button-id="category_navi" data-section-name="cate_navi" data-category-name="긴소매 티셔츠" href="https://www.musinsa.com/category/001010">긴소매 티셔츠</a></span>
          <a href="https://www.musinsa.com/category/001010?brand=londondada">(런던다다)</a>
        </div>
        <a href="https://www.musinsa.com/category/002">추천 아우터</a>
        <a href="https://www.musinsa.com/category/001010?brand=other">(다른 브랜드)</a>
      </main>
    """)
    result = page.evaluate(SNAPSHOT_JS, "https://www.musinsa.com/products/7428042")
    assert result["categories"] == [
        {"code": "001", "name": "상의"},
        {"code": "001010", "name": "긴소매 티셔츠"},
    ]


def test_material_info_reads_only_selected_fit_cells_with_random_classes(page):
    page.set_content("""
      <main>
        <div class="MaterialInfo__MaterialWrap-random">
          <ul class="MaterialInfo__RowHeaderWrap-random"><li>핏</li><li>계절</li></ul>
          <table class="MaterialInfo__MaterialTable-random"><tbody>
            <tr>
              <td style="background-color:white">슬림</td>
              <td class="random-active" style="background-color:rgba(36,94,255,.1)">레귤러</td>
              <td class="random-active" style="background-color:rgba(36,94,255,.1)">루즈</td>
              <td style="background-color:white">오버 사이즈</td>
            </tr>
            <tr><td style="background-color:rgba(36,94,255,.1)">겨울</td></tr>
          </tbody></table>
        </div>
        <aside><table><tr><td style="background-color:rgba(36,94,255,.1)">오버 사이즈</td></tr></table></aside>
      </main>""")
    result = page.evaluate(SNAPSHOT_JS, "https://www.musinsa.com/products/7428042")
    assert result["material_info"]["핏"] == ["레귤러", "루즈"]


def test_material_info_without_selected_cells_stays_unknown(page):
    page.set_content("""<main><div class="MaterialInfo__MaterialWrap-random">
      <ul class="MaterialInfo__RowHeaderWrap-random"><li>핏</li></ul>
      <table class="MaterialInfo__MaterialTable-random"><tr>
        <td style="background-color:white">레귤러</td><td style="background-color:white">루즈</td>
      </tr></table></div></main>""")
    assert (
        page.evaluate(SNAPSHOT_JS, "https://www.musinsa.com/products/7428042")["material_info"][
            "핏"
        ]
        == []
    )
