// Kịch bản kiểm thử E2E (CodeceptJS + Playwright) cho phân hệ Orders
// Phân tích giá trị biên (BVA: Standard 4n+1 và Robustness 6n+1)
//
// Chuẩn bị: python manage.py seed_orders_bva
// Chạy:     npx codeceptjs run tests/orders_checkout_bva_test.js --steps
import assert from 'assert';

const PASSWORD = 'Order@12345';

function login(I, username) {
  I.clearCookie();
  I.amOnPage('/accounts/login/');
  I.fillField('username', username);
  I.fillField('password', PASSWORD);
  I.click('.auth-submit-btn');
  I.waitInUrl('/', 10);
}

Feature('BVA - Kiểm thử giá trị biên phân hệ Đặt hàng & Thanh toán (Orders)');

// =========================================================================
// 1. KIỂM THỬ GIÁ TRỊ BIÊN CHO BIẾN TỔNG TIỀN (total_price)
// Miền hợp lệ: [1, 2.147.483.647] VND
// Các điểm biên: min- (0đ), min (1đ), min+ (2đ), nom (100.000đ), max (2.147.483.647đ), max+ (2.147.483.648đ)
// =========================================================================

Scenario('TC-RBVA-01 - Tổng tiền min- (0 VND / giỏ rỗng): Chuyển hướng về /cart/', ({ I }) => {
  login(I, 'order_bva_empty');
  I.amOnPage('/orders/checkout/');
  I.waitInUrl('/cart/', 10);
  I.see('Giỏ hàng của bạn đang trống');
});

Scenario('TC-BVA-01 - Tổng tiền min (1 VND): Chấp nhận đặt hàng thành công', ({ I }) => {
  login(I, 'order_bva_min');
  I.amOnPage('/orders/checkout/');
  I.see('1 VND');
  I.fillField('full_name', 'Nguyen Van A');
  I.fillField('phone', '0912345678');
  I.fillField('address', '123 Duong Bien Min, Quan 1, TP.HCM');
  I.click('Xác nhận đặt hàng');
  I.waitInUrl('/orders/success/', 10);
  I.see('Đặt hàng thành công');
});

Scenario('TC-BVA-02 - Tổng tiền min+ (2 VND): Chấp nhận đặt hàng thành công', ({ I }) => {
  login(I, 'order_bva_min_plus');
  I.amOnPage('/orders/checkout/');
  I.see('2 VND');
  I.fillField('full_name', 'Le Thi B');
  I.fillField('phone', '0987654321');
  I.fillField('address', '456 Duong Bien Min Plus, Quan 3');
  I.click('Xác nhận đặt hàng');
  I.waitInUrl('/orders/success/', 10);
  I.see('Đặt hàng thành công');
});

Scenario('TC-BVA-03 - Tổng tiền nominal (100.000 VND): Đặt hàng thành công', ({ I }) => {
  login(I, 'order_bva_nom');
  I.amOnPage('/orders/checkout/');
  I.see('100,000 VND');
  I.fillField('full_name', 'Tran Van Danh Nghia');
  I.fillField('phone', '0901234567');
  I.fillField('address', '789 Duong Nominal, Quan 5');
  I.click('Xác nhận đặt hàng');
  I.waitInUrl('/orders/success/', 10);
  I.see('Đặt hàng thành công');
});

Scenario('TC-BVA-05 - Tổng tiền max (2.147.483.647 VND): Chấp nhận tại ngưỡng ORDER_TOTAL_MAX', ({ I }) => {
  login(I, 'order_bva_max');
  I.amOnPage('/orders/checkout/');
  I.dontSee('vượt quá giới hạn');
  I.fillField('full_name', 'Hoang Van Max');
  I.fillField('phone', '0911223344');
  I.fillField('address', '101 Duong Max Int, Quan 7');
  I.click('Xác nhận đặt hàng');
  I.waitInUrl('/orders/success/', 10);
  I.see('Đặt hàng thành công');
});

Scenario('TC-RBVA-07 - Tổng tiền max+ (2.147.483.648 VND): Báo lỗi vượt giới hạn, không tạo đơn', ({ I }) => {
  login(I, 'order_bva_overflow');
  I.amOnPage('/orders/checkout/');
  I.see('vượt quá giới hạn');
  I.fillField('full_name', 'Vu Over Flow');
  I.fillField('phone', '0999888777');
  I.fillField('address', '999 Duong Overflow, Binh Thanh');
  I.click('Xác nhận đặt hàng');
  // Mong đợi: Server render lại form với thông báo lỗi, không redirect sang success
  I.seeInCurrentUrl('/orders/checkout/');
  I.see('vượt quá giới hạn');
});

// =========================================================================
// 2. KIỂM THỬ GIÁ TRỊ BIÊN CHO BIẾN HỌ TÊN (full_name) VÀ SĐT (phone)
// =========================================================================

Scenario('TC-BVA-FN-01 - Họ tên min (1 ký tự: "A"): Đặt hàng thành công', ({ I }) => {
  login(I, 'order_bva_fn_min');
  I.amOnPage('/orders/checkout/');
  I.fillField('full_name', 'A');
  I.fillField('phone', '0912345678');
  I.fillField('address', '123 Duong Bien Min Ten');
  I.click('Xác nhận đặt hàng');
  I.waitInUrl('/orders/success/', 10);
  I.see('Đặt hàng thành công');
});

Scenario('TC-BVA-FN-05 - Họ tên max (255 ký tự): Đặt hàng thành công', ({ I }) => {
  login(I, 'order_bva_fn_max');
  I.amOnPage('/orders/checkout/');
  const maxName = 'N'.repeat(255);
  I.fillField('full_name', maxName);
  I.fillField('phone', '0912345678');
  I.fillField('address', '123 Duong Bien Max Ten');
  I.click('Xác nhận đặt hàng');
  I.waitInUrl('/orders/success/', 10);
  I.see('Đặt hàng thành công');
});

Scenario('TC-BVA-PH-01 - SĐT min (1 ký tự: "0"): Đặt hàng thành công', ({ I }) => {
  login(I, 'order_bva_phone_min');
  I.amOnPage('/orders/checkout/');
  I.fillField('full_name', 'Nguyen Phone Min');
  I.fillField('phone', '0');
  I.fillField('address', '123 Duong Phone Min');
  I.click('Xác nhận đặt hàng');
  I.waitInUrl('/orders/success/', 10);
  I.see('Đặt hàng thành công');
});

Scenario('TC-BVA-PH-05 - SĐT max (20 ký tự): Đặt hàng thành công', ({ I }) => {
  login(I, 'order_bva_phone_max');
  I.amOnPage('/orders/checkout/');
  I.fillField('full_name', 'Nguyen Phone Max');
  I.fillField('phone', '01234567890123456789');
  I.fillField('address', '123 Duong Phone Max');
  I.click('Xác nhận đặt hàng');
  I.waitInUrl('/orders/success/', 10);
  I.see('Đặt hàng thành công');
});

// =========================================================================
// 3. KIỂM THỬ CÁC KÊNH THANH TOÁN (COD / VietQR / Mock Payment)
// =========================================================================

Scenario('TC-BVA-PAY-01 - Kênh VietQR: Checkout -> Hiển thị mã QR -> Xác nhận chuyển khoản', ({ I }) => {
  login(I, 'order_bva_qr');
  I.amOnPage('/orders/checkout/');
  I.fillField('full_name', 'Khach Hang VietQR');
  I.fillField('phone', '0912345678');
  I.fillField('address', '456 Duong QR Code');
  I.checkOption('input[name="payment_method"][value="qr"]');
  I.click('Xác nhận đặt hàng');
  // Chuyển hướng sang trang hiển thị mã VietQR
  I.waitInUrl('/orders/qr/', 10);
  I.see('Chuyển khoản bằng QR');
  I.see('Nội dung chuyển khoản');
  // Nhấn xác nhận đã chuyển khoản
  I.click('Tôi đã chuyển khoản');
  I.waitInUrl('/orders/success/', 10);
  I.see('Đặt hàng thành công');
});

Scenario('TC-BVA-PAY-02 - Kênh Mock: Checkout -> Mở Sandbox Mock -> Xác nhận thành công', ({ I }) => {
  login(I, 'order_bva_mock');
  I.amOnPage('/orders/checkout/');
  I.fillField('full_name', 'Khach Hang Mock');
  I.fillField('phone', '0912345678');
  I.fillField('address', '789 Duong Mock Sandbox');
  I.checkOption('input[name="payment_method"][value="mock"]');
  I.click('Xác nhận đặt hàng');
  // Chuyển hướng sang trang Mock Sandbox
  I.waitInUrl('/orders/mock/', 10);
  I.see('Thanh toán online mô phỏng');
  I.see('Mô phỏng thanh toán thành công');
  // Bấm nút thành công
  I.click('Mô phỏng thanh toán thành công');
  I.waitInUrl('/orders/success/', 10);
  I.see('Đặt hàng thành công');
});
