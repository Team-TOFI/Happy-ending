const form = document.querySelector('#recommendation-form');
const submit = document.querySelector('#submit-button');
const submitLabel = document.querySelector('#submit-label');
const results = document.querySelector('.results');
const status = document.querySelector('#status');
const outfits = document.querySelector('#outfits');
const notices = document.querySelector('#notices');
const rawDetails = document.querySelector('#response-details');
const raw = document.querySelector('#raw-response');
const countLabel = document.querySelector('#result-count');
const groups = {TOP:'상의',BOTTOM:'하의',SHOES:'신발',OUTER:'아우터',BAG:'가방'};
const terms = {RELAXED:'루즈핏',REGULAR:'레귤러핏',FITTED:'슬림핏',OVERSIZED:'오버사이즈',SOLID:'무지',CHECK:'체크',STRIPE:'줄무늬',GRAPHIC:'그래픽',FLORAL:'꽃무늬',DOT:'도트'};
const omissions = {NO_CANDIDATES:'상품 없음',EXCLUDED_BY_CONSTRAINTS:'조건 미충족',NOT_SELECTED:'이번 조합에서 생략'};
let busy = false;

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function secureUrl(value) {
  try { const url = new URL(value); return url.protocol === 'https:' ? url.href : null; }
  catch { return null; }
}

function setStatus(kind, title, message, questions = []) {
  status.hidden = false;
  status.className = `status ${kind}`;
  const heading = node('h3', kind === 'loading' ? 'loading-dots' : '', title);
  status.replaceChildren(heading, node('p', '', message));
  if (questions.length) {
    const list = node('ul');
    for (const question of questions) list.append(node('li', '', question));
    status.append(list);
  }
}

function attribute(item, key) {
  const attr = item.attributes?.[key];
  if (!attr || attr.review_status === 'rejected' || attr.value == null) return null;
  return (Array.isArray(attr.value) ? attr.value : [attr.value]).map(value => terms[value] || value).join('·');
}

function price(text) {
  const match = String(text || '').replaceAll(',', '').match(/^(\d+(?:\.\d+)?)\s*(?:KRW|원)$/i);
  return match ? `${new Intl.NumberFormat('ko-KR').format(Number(match[1]))}원` : (text || '가격 미확인');
}

function product(item) {
  const article = node('article', 'product');
  const link = node('a');
  const href = secureUrl(item.product_url);
  if (href) { link.href = href; link.target = '_blank'; link.rel = 'noopener noreferrer'; }
  const figure = node('figure');
  const src = (item.image_urls || []).map(secureUrl).find(Boolean);
  if (src) {
    const image = node('img');
    image.src = src;
    image.alt = item.name;
    image.loading = 'lazy';
    image.referrerPolicy = 'no-referrer';
    image.addEventListener('error', () => figure.replaceChildren(node('span', 'image-unavailable', '이미지를 불러올 수 없어요')), {once:true});
    figure.append(image);
  } else figure.append(node('span', 'image-unavailable', '이미지 없음'));
  link.append(figure, node('p', 'category', groups[item.service_category] || item.service_category), node('p', 'brand', item.brand || '브랜드 미확인'), node('p', 'name', item.name), node('p', 'price', price(item.price_text)));
  const facts = [attribute(item, 'fit'), attribute(item, 'pattern') || '패턴 미확인'].filter(Boolean);
  article.append(link, node('p', 'facts', facts.join(' · ')));
  return article;
}

function render(data) {
  raw.textContent = JSON.stringify(data, null, 2);
  rawDetails.hidden = false;
  if (data.status !== 'ok' || !data.outfits?.length) {
    const needs = data.status === 'needs_information';
    setStatus('information', needs ? '조금 더 확인이 필요해요' : '조건에 맞는 상품이 없어요', needs ? '확인되지 않은 정보로 상품을 추천하지 않았어요.' : '상황·취향·예산을 조정해 다시 요청해 주세요.', data.questions || []);
    countLabel.textContent = '추천 보류';
  } else {
    status.hidden = true;
    countLabel.textContent = `코디 ${data.outfits.length}개`;
    data.outfits.forEach((outfit, index) => {
      const section = node('section', 'outfit');
      const heading = node('div', 'outfit-heading');
      heading.append(node('h3', '', `코디 ${String(index + 1).padStart(2, '0')}`), node('p', '', outfit.summary));
      const list = node('div', 'products');
      for (const item of outfit.items) list.append(product(item));
      section.append(heading, list);
      if (outfit.omitted_categories?.length) {
        section.append(node('p', 'omission', outfit.omitted_categories.map(item => `${groups[item.category]} ${omissions[item.reason] || item.reason}`).join(' · ')));
      }
      outfits.append(section);
    });
  }
  const messages = [...(data.warnings || [])];
  if (data.omitted_categories?.length) messages.push(data.omitted_categories.map(item => `${groups[item.category]}: ${omissions[item.reason] || item.reason}`).join(' · '));
  notices.replaceChildren(...[...new Set(messages)].map(message => node('p', '', message)));
  notices.hidden = messages.length === 0;
}

const presets = {
  daily: {tpo:'주말 카페와 산책', aesthetic:'편안한 미니멀', context:''},
  funeral: {tpo:'장례식 조문', aesthetic:'차분한 복장', context:'빨간색과 눈에 띄는 패턴은 피하고 싶어요.'},
};
for (const button of document.querySelectorAll('[data-preset]')) {
  button.addEventListener('click', () => {
    for (const [key, value] of Object.entries(presets[button.dataset.preset])) form.elements[key].value = value;
  });
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  if (busy) return;
  for (const id of ['tpo', 'aesthetic']) {
    const field = document.getElementById(id);
    field.setCustomValidity(field.value.trim() ? '' : '내용을 입력해 주세요.');
    if (!field.reportValidity()) return;
  }
  if (!form.reportValidity()) return;
  const payload = {
    body_type:{overall:form.elements.body_type.value},
    tpo:form.elements.tpo.value.trim(),
    aesthetic:form.elements.aesthetic.value.trim(),
    context:form.elements.context.value.trim(),
    count:Number(form.elements.count.value),
  };
  const profile = {};
  if (form.elements.height.value !== '') profile.height_cm = Number(form.elements.height.value);
  if (form.elements.weight.value !== '') profile.weight_kg = Number(form.elements.weight.value);
  if (Object.keys(profile).length) payload.profile = profile;
  if (form.elements.budget.value !== '') payload.budget_max_krw = Number(form.elements.budget.value);
  busy = true;
  for (const input of form.querySelectorAll('input,textarea,button,select')) input.disabled = true;
  results.setAttribute('aria-busy', 'true');
  submitLabel.textContent = '추천을 구성하고 있어요';
  outfits.replaceChildren(); notices.hidden = true; rawDetails.hidden = true; rawDetails.open = false; countLabel.textContent = '';
  setStatus('loading', '상품을 살펴보고 있어요', '조건을 확인하고 코디를 구성하고 있어요. 잠시만 기다려 주세요.');
  if (window.matchMedia('(max-width: 680px)').matches) {
    results.scrollIntoView({behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block:'start'});
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 190000);
  try {
    const response = await fetch('/api/recommendations', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:controller.signal});
    let data;
    try { data = await response.json(); } catch { throw new Error('추천 서버의 응답을 확인할 수 없습니다. 잠시 후 다시 시도해 주세요.'); }
    if (!response.ok) {
      const message = typeof data.detail === 'string' ? data.detail : '입력 내용을 확인하고 다시 요청해 주세요.';
      throw new Error(message);
    }
    render(data);
  } catch (error) {
    setStatus('error', '추천을 완료하지 못했어요', error.name === 'AbortError' ? '응답 시간이 길어졌어요. 잠시 후 다시 시도해 주세요.' : error.message);
  } finally {
    clearTimeout(timer);
    busy = false;
    for (const input of form.querySelectorAll('input,textarea,button,select')) input.disabled = false;
    results.setAttribute('aria-busy', 'false');
    submitLabel.textContent = '코디 추천받기';
  }
});

for (const field of [form.elements.tpo, form.elements.aesthetic]) field.addEventListener('input', () => field.setCustomValidity(''));
