// Test case sinh từ BẢNG QUYẾT ĐỊNH của giỏ hàng, chỉ gồm các luật mà 33 TC EP & BVA chưa kiểm tra.
// Bảng đầy đủ R1..R25: docs/TestCase_FR3_Cart_StateTransition_DecisionTable.md.
//
// Chuẩn bị:   python manage.py seed_cart_test
// Chạy:       npx codeceptjs run tests/cart_decision_test.js --steps
import assert from 'assert';
import {
  A, B, BADGE, CHECKOUT_TEXT, clearCart, fillCart, login, productIds, totalOnPage, visit,
} from './_cart_helpers.js';

const USER = 'cart_tester';
let ids;
let missingId;

const assertStatus = async (I, url, expected) => {
  const { status } = await visit(I, url);
  assert.strictEqual(status, expected, `GET ${url}: mong đợi ${expected}, thực tế ${status}`);
};

const badgeValue = async (I) => {
  I.amOnPage('/');
  return parseInt(await I.grabTextFrom(BADGE), 10);
};

Feature('Bảng quyết định - Giỏ hàng: khách chưa đăng nhập');

Before(async ({ I }) => {
  I.amOnPage('/');
  ids = await productIds(I);
  missingId = ids.sorted.at(-1) + 100;
});

// Luật R1, R6, R11, R16 không phụ thuộc sản phẩm có tồn tại hay không
for (const [id, action] of [['R1', 'add'], ['R6', 'increase'], ['R11', 'decrease'], ['R16', 'remove']]) {
  Scenario(`TC-CART-DT-${id} - Khách ${action} SP không tồn tại: chuyển login, không 404`, ({ I }) => {
    I.amOnPage(`/cart/${action}/${missingId}/`);
    I.seeInCurrentUrl(`/accounts/login/?next=/cart/${action}/${missingId}/`);
  });
}

Scenario('TC-CART-DT-R23 - Khách: biểu tượng giỏ hàng hiện 0', async ({ I }) => {
  assert.strictEqual(await badgeValue(I), 0);
});

Feature('Bảng quyết định - Giỏ hàng: đã đăng nhập');

Before(async ({ I }) => {
  login(I, USER);
  ids = await productIds(I);
  missingId = ids.sorted.at(-1) + 100;
  await clearCart(I);
});

// Luật R7, R12, R17: id nằm trong miền số nguyên hợp lệ nhưng không có sản phẩm
for (const [id, action] of [['R7', 'increase'], ['R12', 'decrease'], ['R17', 'remove']]) {
  Scenario(`TC-CART-DT-${id} - ${action} SP không tồn tại: 404`, async ({ I }) => {
    await assertStatus(I, `/cart/${action}/${missingId}/`, 404);
  });
}

Scenario('TC-CART-DT-R22 - Giỏ có SP: hiện tổng tiền và nút đặt hàng', async ({ I }) => {
  await fillCart(I, ids.byName[A], 2);
  await fillCart(I, ids.byName[B], 1);
  assert.strictEqual(await totalOnPage(I), 130000);
  I.see(CHECKOUT_TEXT);
});

Scenario('TC-CART-DT-R25 - Biểu tượng giỏ hàng là tổng số lượng, không phải số dòng', async ({ I }) => {
  await fillCart(I, ids.byName[A], 2);
  await fillCart(I, ids.byName[B], 3);
  assert.strictEqual(await badgeValue(I), 5);
});

Feature('Bảng quyết định - Giỏ hàng: tài khoản chưa từng có giỏ');

Scenario('TC-CART-DT-R24 - Chưa có bản ghi Cart: biểu tượng hiện 0, không lỗi', async ({ I }) => {
  login(I, 'cart_fresh');
  assert.strictEqual(await badgeValue(I), 0);
});
