// Test case sinh từ BẢNG QUYẾT ĐỊNH của chức năng "Tìm kiếm và lọc đơn hàng" (TC-BS1 → BS7).
// Bổ sung cho 14 TC BVA để phủ các nhánh BVA chưa chạm tới: bộ lọc trạng thái, bộ lọc thanh toán,
// từ khóa dạng #số và từ khóa chữ.
//
// Chuẩn bị:   python manage.py seed_bva_orders
// Chạy:       npx codeceptjs run tests/search_order_decision_test.js --steps
import assert from 'assert';

const ADMIN_USER = process.env.BVA_ADMIN || 'bva_admin';
const ADMIN_PASS = process.env.BVA_PASSWORD || 'Bva@12345';
const SEED_NAME = 'Nguyen Van BVA';           // đơn QR, Đã thanh toán, do seed_bva_orders tạo
const EMPTY_MSG = 'Chưa có đơn hàng nào.';
const ID_CELLS = 'tbody tr td:first-child';

Feature('Bảng quyết định - Tìm kiếm và lọc đơn hàng (admin)');

Before(({ I }) => {
  I.amOnPage('/accounts/login/');
  I.fillField('username', ADMIN_USER);
  I.fillField('password', ADMIN_PASS);
  I.click('.auth-submit-btn');
  I.waitInUrl('/admin-panel/', 10);
  I.amOnPage('/admin-panel/orders/');
  I.dontSeeInCurrentUrl('/accounts/login');
});

const idsOf = async (I) =>
  (await I.grabTextFromAll(ID_CELLS)).map((t) => parseInt(t.replace('#', ''), 10)).filter((n) => !Number.isNaN(n));

// R1: từ khóa dạng #số -> lọc đúng mã đơn
Scenario('TC-BS1 - Từ khóa dạng #số (#5)', async ({ I }) => {
  const existing = await idsOf(I);
  I.amOnPage('/admin-panel/orders/?keyword=%235');
  const found = await idsOf(I);
  assert.deepStrictEqual(found, existing.includes(5) ? [5] : [], `Mong đợi chỉ đơn #5 (nếu có), thực tế: [${found}]`);
});

// R3: từ khóa chữ, dài >= 6 -> tìm theo tên
Scenario('TC-BS2 - Từ khóa chữ, dài >= 6 ký tự (Nguyen)', ({ I }) => {
  I.amOnPage('/admin-panel/orders/?keyword=Nguyen');
  I.see(SEED_NAME);
  I.dontSee('Server Error');
});

// R5: từ khóa chữ, ngắn < 6 -> chỉ tìm theo tên
Scenario('TC-BS3 - Từ khóa chữ, ngắn < 6 ký tự (Ng)', ({ I }) => {
  I.amOnPage('/admin-panel/orders/?keyword=Ng');
  I.see(SEED_NAME);
  I.dontSee('Server Error');
});

// Bộ lọc trạng thái hợp lệ
Scenario('TC-BS4 - Lọc trạng thái hợp lệ (status=paid)', async ({ I }) => {
  I.amOnPage('/admin-panel/orders/?status=paid');
  I.see(SEED_NAME);
  const cells = await I.grabTextFromAll('tbody tr td:nth-child(5)');
  assert.ok(cells.length > 0 && cells.every((t) => t.includes('Đã thanh toán')),
    `Mọi dòng phải là "Đã thanh toán", thực tế: ${JSON.stringify(cells)}`);
});

// Bộ lọc trạng thái không hợp lệ
Scenario('TC-BS5 - Lọc trạng thái không hợp lệ (status=hacked)', ({ I }) => {
  I.amOnPage('/admin-panel/orders/?status=hacked');
  I.see(EMPTY_MSG);
  I.dontSee('Server Error');
});

// Bộ lọc thanh toán hợp lệ
Scenario('TC-BS6 - Lọc thanh toán hợp lệ (payment_method=qr)', async ({ I }) => {
  I.amOnPage('/admin-panel/orders/?payment_method=qr');
  I.see(SEED_NAME);
  const cells = await I.grabTextFromAll('tbody tr td:nth-child(4)');
  assert.ok(cells.length > 0 && cells.every((t) => t.includes('QR')),
    `Mọi dòng phải thanh toán QR, thực tế: ${JSON.stringify(cells)}`);
});

// Bộ lọc thanh toán không hợp lệ
Scenario('TC-BS7 - Lọc thanh toán không hợp lệ (payment_method=hacked)', ({ I }) => {
  I.amOnPage('/admin-panel/orders/?payment_method=hacked');
  I.see(EMPTY_MSG);
  I.dontSee('Server Error');
});
