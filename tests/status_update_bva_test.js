// BVA (Robustness, 7 điểm) cho chức năng "Cập nhật trạng thái đơn hàng"
// URL: POST /admin-panel/orders/<mã đơn>/status/      Phân hệ 6: Admin Orders & Analytics
//
// Biến thử: mã đơn trên URL (số nguyên). Trạng thái gửi lên là giá trị không hợp lệ
// ("bva_noop") nên với đơn có thật hệ thống bỏ qua, KHÔNG làm đổi trạng thái đơn nào.
//   - đơn tồn tại      -> chuyển hướng về danh sách đơn, trang cuối cùng trả 200
//   - đơn không tồn tại -> 404
//
// Chuẩn bị:   python manage.py seed_bva_orders
// Chạy:       npx codeceptjs run tests/status_update_bva_test.js --steps
import assert from 'assert';

const ADMIN_USER = process.env.BVA_ADMIN || 'bva_admin';
const ADMIN_PASS = process.env.BVA_PASSWORD || 'Bva@12345';
const ID_CELLS = 'tbody tr td:first-child';

Feature('BVA - Cập nhật trạng thái đơn hàng (mã đơn trên URL)');

Before(({ I }) => {
  I.amOnPage('/accounts/login/');
  I.fillField('username', ADMIN_USER);
  I.fillField('password', ADMIN_PASS);
  I.click('.auth-submit-btn');
  I.waitInUrl('/admin-panel/', 10);
  I.amOnPage('/admin-panel/orders/');
  I.dontSeeInCurrentUrl('/accounts/login');
});

const cases = [
  ['TC01', 'Mã đơn min- (0)', () => 0],
  ['TC02', 'Mã đơn min (1)', () => 1],
  ['TC03', 'Mã đơn min+ (2)', () => 2],
  ['TC04', 'Mã đơn nominal (4)', () => 4],
  ['TC05', 'Mã đơn max- (mã lớn nhất - 1)', (max) => max - 1],
  ['TC06', 'Mã đơn max (mã lớn nhất)', (max) => max],
  ['TC07', 'Mã đơn max+ (mã lớn nhất + 1)', (max) => max + 1],
];

for (const [id, name, pick] of cases) {
  Scenario(`${id} - ${name}`, async ({ I }) => {
    const texts = await I.grabTextFromAll(ID_CELLS);
    const existing = texts.map((t) => parseInt(t.replace('#', ''), 10)).filter((n) => !Number.isNaN(n));
    const k = pick(Math.max(...existing));
    const csrf = (await I.grabCookie('csrftoken')).value;

    const status = await I.executeScript(async ({ pk, token }) => {
      const res = await fetch(`/admin-panel/orders/${pk}/status/`, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': token, 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'status=bva_noop',
      });
      return res.status;
    }, { pk: k, token: csrf });

    if (existing.includes(k)) {
      assert.strictEqual(status, 200, `Đơn #${k} có thật, mong đợi chuyển về danh sách (200), thực tế: ${status}`);
    } else {
      assert.strictEqual(status, 404, `Đơn #${k} không tồn tại, mong đợi 404, thực tế: ${status}`);
    }
  });
}