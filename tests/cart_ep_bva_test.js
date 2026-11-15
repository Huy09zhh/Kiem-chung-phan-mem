// Kiểm thử hộp đen FR3 - Giỏ hàng: 33 test case EP & BVA trong docs/TestCase_FR3_Cart_EP_BVA.md.
//
// Chuẩn bị:   python manage.py seed_cart_test
// Chạy:       npx codeceptjs run tests/cart_ep_bva_test.js --steps
import assert from 'assert';
import {
  A, AT_MAX, AT_MAX_MINUS_1, B, CHECKOUT_TEXT, EMPTY_MSG, QTY_MAX,
  clearCart, fillCart, login, minusButton, plusButton, productIds, qtyLocator, qtyOf,
  removeButton, totalOnPage, visit,
} from './_cart_helpers.js';

const INT64_MAX = '9223372036854775807';
const INT64_OVERFLOW = '9223372036854775808';
const USER = 'cart_tester';

let ids;

const assertStatus = async (I, url, expected) => {
  const { status } = await visit(I, url);
  assert.strictEqual(status, expected, `GET ${url}: mong đợi ${expected}, thực tế ${status}`);
};

// ---------- Khách chưa đăng nhập ----------
Feature('Giỏ hàng - EP: khách chưa đăng nhập');

Before(async ({ I }) => {
  login(I, USER);
  ids = await productIds(I);
  await clearCart(I);
  I.clearCookie();
});

Scenario('TC-CART-EP-01 - Khách thêm SP: chuyển login kèm next, không tạo CartItem', async ({ I }) => {
  const a = ids.byName[A];
  I.amOnPage(`/cart/add/${a}/`);
  I.seeInCurrentUrl(`/accounts/login/?next=/cart/add/${a}/`);
  I.clearCookie();
  login(I, USER);
  assert.strictEqual(await qtyOf(I, A), null);
});

Scenario('TC-CART-EP-02 - Khách xem giỏ: chuyển login', ({ I }) => {
  I.amOnPage('/cart/');
  I.seeInCurrentUrl('/accounts/login/');
});

Scenario('TC-CART-EP-03 - Khách tăng số lượng: chuyển login', ({ I }) => {
  I.amOnPage(`/cart/increase/${ids.byName[A]}/`);
  I.seeInCurrentUrl('/accounts/login/');
});

// ---------- Đã đăng nhập, giỏ trống ở đầu mỗi test ----------
Feature('Giỏ hàng - EP & BVA: đã đăng nhập');

Before(async ({ I }) => {
  login(I, USER);
  ids = await productIds(I);
  await clearCart(I);
});

Scenario('TC-CART-EP-04 - Thêm SP mới: quantity = 1', async ({ I }) => {
  I.amOnPage(`/cart/add/${ids.byName[A]}/`);
  I.seeInCurrentUrl('/cart/');
  assert.strictEqual(await qtyOf(I, A), 1);
});

Scenario('TC-CART-EP-05 - Thêm SP đã có: quantity = 2, vẫn 1 dòng', async ({ I }) => {
  await fillCart(I, ids.byName[A], 1);
  I.amOnPage(`/cart/add/${ids.byName[A]}/`);
  assert.strictEqual(await qtyOf(I, A), 2);
  I.seeNumberOfElements(qtyLocator(A), 1);
});

Scenario('TC-CART-EP-06 - Thêm SP không tồn tại: 404, không tạo CartItem', async ({ I }) => {
  await assertStatus(I, `/cart/add/${ids.sorted.at(-1) + 100}/`, 404);
  I.amOnPage('/cart/');
  I.see(EMPTY_MSG);
});

Scenario('TC-CART-EP-07 - product_id âm: 404', async ({ I }) => {
  await assertStatus(I, '/cart/add/-1/', 404);
});

Scenario('TC-CART-EP-08 - product_id không phải số: 404', async ({ I }) => {
  await assertStatus(I, '/cart/add/abc/', 404);
});

Scenario('TC-CART-EP-09 - Bấm "+" khi A x2: quantity = 3', async ({ I }) => {
  await fillCart(I, ids.byName[A], 2);
  I.amOnPage('/cart/');
  I.click(plusButton(A));
  I.waitForText('3', 5, qtyLocator(A));
  assert.strictEqual(await qtyOf(I, A), 3);
});

Scenario('TC-CART-EP-10 - Tăng SP không có trong giỏ: 404', async ({ I }) => {
  await assertStatus(I, `/cart/increase/${ids.byName[A]}/`, 404);
});

Scenario('TC-CART-EP-11 - Giảm SP không có trong giỏ: 404', async ({ I }) => {
  await assertStatus(I, `/cart/decrease/${ids.byName[A]}/`, 404);
});

Scenario('TC-CART-EP-12 - Bấm "Xóa khỏi giỏ hàng" khi A x5: xóa hẳn', async ({ I }) => {
  await fillCart(I, ids.byName[A], 5);
  I.amOnPage('/cart/');
  I.click(removeButton(A));
  I.waitForText(EMPTY_MSG, 5);
  assert.strictEqual(await qtyOf(I, A), null);
});

Scenario('TC-CART-EP-13 - Xóa SP không có trong giỏ: về /cart/, không lỗi', async ({ I }) => {
  const { status, url } = await visit(I, `/cart/remove/${ids.byName[A]}/`);
  assert.strictEqual(status, 200);
  assert.strictEqual(url, '/cart/');
});

Scenario('TC-CART-EP-14 - Giỏ trống: có thông báo, không có nút đặt hàng', ({ I }) => {
  I.amOnPage('/cart/');
  I.see(EMPTY_MSG);
  I.dontSee(CHECKOUT_TEXT);
});

Scenario('TC-CART-EP-15 - Giỏ tách biệt theo user', async ({ I }) => {
  const a = ids.byName[A];
  await fillCart(I, a, 1);
  I.clearCookie();
  login(I, 'cart_other');
  I.amOnPage('/cart/');
  I.dontSee(A);
  await assertStatus(I, `/cart/increase/${a}/`, 404);
  I.clearCookie();
  login(I, USER);
  assert.strictEqual(await qtyOf(I, A), 1);
});

Scenario('TC-CART-BVA-01 - product_id = 0: 404', async ({ I }) => {
  await assertStatus(I, '/cart/add/0/', 404);
});

const idCases = [
  ['TC-CART-BVA-02', 'product_id = min', (s) => s[0]],
  ['TC-CART-BVA-03', 'product_id = max', (s) => s.at(-1)],
  ['TC-CART-BVA-14', 'product_id = min + 1', (s) => s[1]],
  ['TC-CART-BVA-15', 'product_id = max - 1', (s) => s.at(-2)],
];
for (const [id, name, pick] of idCases) {
  Scenario(`${id} - ${name}: thêm thành công, quantity = 1`, async ({ I }) => {
    const productId = pick(ids.sorted);
    I.amOnPage(`/cart/add/${productId}/`);
    I.seeInCurrentUrl('/cart/');
    I.seeNumberOfElements('.qty-number', 1);
    I.see('1', '.qty-number');
  });
}

Scenario('TC-CART-BVA-04 - product_id = max + 1: 404', async ({ I }) => {
  await assertStatus(I, `/cart/add/${ids.sorted.at(-1) + 1}/`, 404);
});

Scenario('TC-CART-BVA-05 - product_id = 2^63 - 1: 404', async ({ I }) => {
  await assertStatus(I, `/cart/add/${INT64_MAX}/`, 404);
});

Scenario('TC-CART-BVA-06 - product_id = 2^63 trên cả 4 endpoint: 404, không 500', async ({ I }) => {
  for (const action of ['add', 'increase', 'decrease', 'remove']) {
    await assertStatus(I, `/cart/${action}/${INT64_OVERFLOW}/`, 404);
  }
});

Scenario('TC-CART-BVA-07 - Bấm "−" khi A x1: xóa khỏi giỏ', async ({ I }) => {
  await fillCart(I, ids.byName[A], 1);
  I.amOnPage('/cart/');
  I.click(minusButton(A));
  I.waitForText(EMPTY_MSG, 5);
  assert.strictEqual(await qtyOf(I, A), null);
});

Scenario('TC-CART-BVA-08 - Bấm "−" khi A x2: quantity = 1', async ({ I }) => {
  await fillCart(I, ids.byName[A], 2);
  I.amOnPage('/cart/');
  I.click(minusButton(A));
  I.waitForText('1', 5, qtyLocator(A));
  assert.strictEqual(await qtyOf(I, A), 1);
});

Scenario('TC-CART-BVA-09 - Bấm "−" khi A x3: quantity = 2', async ({ I }) => {
  await fillCart(I, ids.byName[A], 3);
  I.amOnPage('/cart/');
  I.click(minusButton(A));
  I.waitForText('2', 5, qtyLocator(A));
  assert.strictEqual(await qtyOf(I, A), 2);
});

Scenario('TC-CART-BVA-10 - Bấm "+" khi A x1: quantity = 2', async ({ I }) => {
  await fillCart(I, ids.byName[A], 1);
  I.amOnPage('/cart/');
  I.click(plusButton(A));
  I.waitForText('2', 5, qtyLocator(A));
  assert.strictEqual(await qtyOf(I, A), 2);
});

Scenario('TC-CART-BVA-11 - Giỏ 1 SP (A x1): tổng 50.000', async ({ I }) => {
  await fillCart(I, ids.byName[A], 1);
  assert.strictEqual(await totalOnPage(I), 50000);
});

Scenario('TC-CART-BVA-12 - Giỏ 2 SP (A x2, B x1): tổng 130.000', async ({ I }) => {
  await fillCart(I, ids.byName[A], 2);
  await fillCart(I, ids.byName[B], 1);
  assert.strictEqual(await totalOnPage(I), 130000);
});

Scenario('TC-CART-BVA-13 - Xóa SP cuối cùng: giỏ trống', async ({ I }) => {
  await fillCart(I, ids.byName[A], 1);
  I.amOnPage(`/cart/remove/${ids.byName[A]}/`);
  I.see(EMPTY_MSG);
});

// ---------- Biên trên của quantity: dùng số lượng có sẵn do seed_cart_test tạo ----------
Feature('Giỏ hàng - BVA: biên trên của số lượng');

Before(async ({ I }) => {
  login(I, 'cart_max');
  ids = await productIds(I);
});

Scenario('TC-CART-BVA-16 - Bấm "+" khi quantity = MAX - 1: lên MAX', async ({ I }) => {
  I.amOnPage('/cart/');
  I.click(plusButton(AT_MAX_MINUS_1));
  I.waitForText(String(QTY_MAX), 5, qtyLocator(AT_MAX_MINUS_1));
  assert.strictEqual(await qtyOf(I, AT_MAX_MINUS_1), QTY_MAX);
  // Trả số lượng về MAX - 1 để chạy lại được mà không cần seed lại
  await visit(I, `/cart/decrease/${ids.byName[AT_MAX_MINUS_1]}/`);
  assert.strictEqual(await qtyOf(I, AT_MAX_MINUS_1), QTY_MAX - 1);
});

Scenario('TC-CART-BVA-17 - Bấm "+" khi quantity = MAX: giữ nguyên, không 500', async ({ I }) => {
  await assertStatus(I, `/cart/increase/${ids.byName[AT_MAX]}/`, 200);
  assert.strictEqual(await qtyOf(I, AT_MAX), QTY_MAX);
});

Scenario('TC-CART-BVA-18 - Thêm SP khi quantity = MAX: giữ nguyên, không 500', async ({ I }) => {
  await assertStatus(I, `/cart/add/${ids.byName[AT_MAX]}/`, 200);
  assert.strictEqual(await qtyOf(I, AT_MAX), QTY_MAX);
});
