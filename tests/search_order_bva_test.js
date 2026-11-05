// BVA (Robustness, 7 điểm) cho chức năng "Tìm kiếm đơn hàng" - /admin-panel/orders/
// Phân hệ 6: Admin Orders & Analytics. Mỗi Scenario ứng với một dòng TC01..TC14 trong file Excel.
//
// Chuẩn bị:   python manage.py seed_bva_orders
// Chạy:       npx codeceptjs run tests/search_order_bva_test.js --steps
import assert from 'assert';

const ADMIN_USER = process.env.BVA_ADMIN || 'bva_admin';
const ADMIN_PASS = process.env.BVA_PASSWORD || 'Bva@12345';
const SEED_NAME = 'BVA Seed';                  // đơn mẫu có SĐT 0912345678
const PHONE = '09123456781234567890';          // chuỗi 20 ký tự, cắt theo độ dài cần thử
const EMPTY_MSG = 'Chưa có đơn hàng nào.';
const ID_CELLS = 'tbody tr td:first-child';

Feature('BVA - Tìm kiếm đơn hàng (admin)');

Before(({ I }) => {
  I.amOnPage('/accounts/login/');
  I.fillField('username', ADMIN_USER);
  I.fillField('password', ADMIN_PASS);
  // Trang có 2 nút chứa chữ "Đăng nhập" (nút Google và nút đăng nhập thường),
  // nên chọn đúng nút của form bằng class.
  I.click('.auth-submit-btn');
  // Tài khoản staff được chuyển tới /admin-panel/dashboard/ sau khi đăng nhập thành công.
  I.waitInUrl('/admin-panel/', 10);
  I.amOnPage('/admin-panel/orders/');
  I.dontSeeInCurrentUrl('/accounts/login');
});

// ---------- Biến 1: độ dài từ khóa SĐT (min=6, max=20) ----------
const phoneCases = [
  ['TC01', 'SĐT nominal (10 ký tự)', 10, true],
  ['TC02', 'SĐT min- (5 ký tự)', 5, false],
  ['TC03', 'SĐT min (6 ký tự)', 6, true],
  ['TC04', 'SĐT min+ (7 ký tự)', 7, true],
  ['TC05', 'SĐT max- (19 ký tự)', 19, false],
  ['TC06', 'SĐT max (20 ký tự)', 20, false],
  ['TC07', 'SĐT max+ (21 ký tự)', 21, false],
];
for (const [id, name, len, found] of phoneCases) {
  Scenario(`${id} - ${name}`, ({ I }) => {
    I.amOnPage(`/admin-panel/orders/?keyword=${PHONE.slice(0, len)}`);
    if (found) {
      I.see(SEED_NAME);                       // tìm thấy đơn theo SĐT
    } else {
      I.dontSee(SEED_NAME);                   // không có đơn khớp, không lỗi máy chủ
      I.see(EMPTY_MSG);
    }
    I.dontSee('Server Error');
  });
}

// ---------- Biến 2: mã đơn (min=1, max=mã đơn lớn nhất đang có) ----------
const idCases = [
  ['TC08', 'Mã đơn min- (0)', () => 0],
  ['TC09', 'Mã đơn min (1)', () => 1],
  ['TC10', 'Mã đơn min+ (2)', () => 2],
  ['TC11', 'Mã đơn nominal (4)', () => 4],
  ['TC12', 'Mã đơn max- (mã lớn nhất - 1)', (max) => max - 1],
  ['TC13', 'Mã đơn max (mã lớn nhất)', (max) => max],
  ['TC14', 'Mã đơn max+ (mã lớn nhất + 1)', (max) => max + 1],
];
for (const [id, name, pick] of idCases) {
  Scenario(`${id} - ${name}`, async ({ I }) => {
    const texts = await I.grabTextFromAll(ID_CELLS);
    const existing = texts.map((t) => parseInt(t.replace('#', ''), 10)).filter((n) => !Number.isNaN(n));
    const max = Math.max(...existing);
    const k = pick(max);

    I.amOnPage(`/admin-panel/orders/?keyword=${k}`);
    const found = (await I.grabTextFromAll(ID_CELLS))
      .map((t) => parseInt(t.replace('#', ''), 10))
      .filter((n) => !Number.isNaN(n));
    // Từ khóa toàn chữ số còn khớp theo tên khách (ví dụ tên có chữ số "1"),
    // nên không đòi danh sách chỉ có đúng một đơn; chỉ kiểm tra có/không có đơn #k.
    if (existing.includes(k)) {
      assert.ok(found.includes(k), `Mong đợi có đơn #${k}, thực tế: [${found}]`);
    } else {
      assert.ok(!found.includes(k), `Đơn #${k} không tồn tại nhưng vẫn xuất hiện: [${found}]`);
    }
  });
}