// Hàm dùng chung cho các test CodeceptJS của giỏ hàng.
// Tên file không kết thúc bằng _test.js nên CodeceptJS không chạy nó như một bộ test.
export const PASSWORD = 'Cart@12345';
export const QTY_MAX = 2147483647;
export const A = 'Cart Test A';           // 50.000 VND
export const B = 'Cart Test B';           // 30.000 VND
export const AT_MAX_MINUS_1 = 'Cart Test Max-1';
export const AT_MAX = 'Cart Test Max';
export const EMPTY_MSG = 'Giỏ hàng của bạn đang trống';
export const CHECKOUT_TEXT = 'Tiếp tục thanh toán';
export const BADGE = "//i[contains(@class,'icon-shopping-cart')]/following-sibling::span";

const itemRow = (name) =>
  `//div[contains(concat(' ',normalize-space(@class),' '),' cart-item ')][.//h3[normalize-space()='${name}']]`;

export const qtyLocator = (name) => `${itemRow(name)}//span[contains(@class,'qty-number')]`;
export const plusButton = (name) => `${itemRow(name)}//a[@aria-label='Tăng số lượng']`;
export const minusButton = (name) => `${itemRow(name)}//a[@aria-label='Giảm số lượng']`;
export const removeButton = (name) => `${itemRow(name)}//a[contains(@class,'remove-btn')]`;

export function login(I, username) {
  I.amOnPage('/accounts/login/');
  I.fillField('username', username);
  I.fillField('password', PASSWORD);
  I.click('.auth-submit-btn');
  I.waitUrlEquals('/', 10);
}

// Gửi GET từ trình duyệt để đọc mã HTTP và URL cuối cùng (sau khi đi theo redirect).
export function visit(I, url) {
  return I.executeScript(async (target) => {
    const res = await fetch(target, { credentials: 'same-origin', cache: 'no-store' });
    return { status: res.status, url: new URL(res.url).pathname + new URL(res.url).search };
  }, url);
}

export async function productIds(I) {
  const products = await I.executeScript(async () => (await fetch('/products/api/')).json());
  const byName = Object.fromEntries(products.map((p) => [p.name, p.id]));
  return { byName, sorted: products.map((p) => p.id).sort((x, y) => x - y) };
}

export async function clearCart(I) {
  I.amOnPage('/cart/');
  const links = await I.grabAttributeFromAll('.remove-btn', 'href');
  for (const link of links) {
    await visit(I, link);
  }
}

// Đưa một sản phẩm về số lượng n bằng cách gọi /cart/add/ n lần (giỏ phải chưa có sản phẩm này).
export async function fillCart(I, productId, n) {
  for (let i = 0; i < n; i += 1) {
    await visit(I, `/cart/add/${productId}/`);
  }
}

// Số lượng đang hiển thị trên /cart/, null nếu sản phẩm không có trong giỏ.
export async function qtyOf(I, name) {
  I.amOnPage('/cart/');
  const texts = await I.grabTextFromAll(qtyLocator(name));
  return texts.length ? parseInt(texts[0], 10) : null;
}

export async function totalOnPage(I) {
  I.amOnPage('/cart/');
  const text = await I.grabTextFrom('.summary-total');
  return parseInt(text.replace(/\D/g, ''), 10);
}
