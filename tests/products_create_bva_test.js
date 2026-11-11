Feature('Products & Search - Black-box EP & BVA Thêm sản phẩm mới (TC-PS-021 -> TC-PS-032)');

Before(({ I }) => {
  I.amOnPage('/accounts/login/');
  I.fillField('#id_username', 'test_admin');
  I.fillField('#id_password', 'admin123');
  I.click('.auth-submit-btn');
  I.waitForText('Tổng quan', 5);
});

Scenario('TC-PS-021 (TC01): Gộp tất cả tại min (Tên 2 ký tự, Giá 1.000, Giá cũ 50.001)', ({ I }) => {
  I.amOnPage('/admin-panel/products/create/');
  I.fillField('#id_name', 'AB');
  I.fillField('#id_price', '1000');
  I.fillField('#id_old_price', '50001');
  I.click('Lưu sản phẩm');
  I.seeInCurrentUrl('/admin-panel/products/');
  I.see('AB');
});

Scenario('TC-PS-022 (TC02): Gộp tất cả tại min+ (Tên 3 ký tự, Giá 1.001, Giá cũ 50.002)', ({ I }) => {
  I.amOnPage('/admin-panel/products/create/');
  I.fillField('#id_name', 'ABC');
  I.fillField('#id_price', '1001');
  I.fillField('#id_old_price', '50002');
  I.click('Lưu sản phẩm');
  I.seeInCurrentUrl('/admin-panel/products/');
  I.see('ABC');
});

Scenario('TC-PS-023 (TC03): Gộp tất cả tại nominal (Tên 20 ký tự, Giá 50.000, Giá cũ 70.000)', ({ I }) => {
  I.amOnPage('/admin-panel/products/create/');
  I.fillField('#id_name', 'Cây Kim Tiền Để Bàn');
  I.fillField('#id_price', '50000');
  I.fillField('#id_old_price', '70000');
  I.click('Lưu sản phẩm');
  I.seeInCurrentUrl('/admin-panel/products/');
  I.see('Cây Kim Tiền Để Bàn');
});

Scenario('TC-PS-026 (TC06): Tên max 255 ký tự, Giá bán max 100.000.000, Giá cũ trống', ({ I }) => {
  I.amOnPage('/admin-panel/products/create/');
  I.fillField('#id_name', 'B'.repeat(255));
  I.fillField('#id_price', '100000000');
  I.fillField('#id_old_price', '');
  I.click('Lưu sản phẩm');
  I.seeInCurrentUrl('/admin-panel/products/');
});

Scenario('TC-PS-028 (TC08): Tên max+ (256 ký tự) bị chặn và báo lỗi form', ({ I }) => {
  I.amOnPage('/admin-panel/products/create/');
  I.executeScript(() => document.getElementById('id_name').removeAttribute('maxlength'));
  I.fillField('#id_name', 'C'.repeat(256));
  I.fillField('#id_price', '50000');
  I.fillField('#id_old_price', '70000');
  I.click('Lưu sản phẩm');
  I.seeInCurrentUrl('/admin-panel/products/create/');
  I.see('Không lưu được sản phẩm');
});

Scenario('TC-PS-031 (TC11): Giá cũ bằng Giá bán (50.000 <= 50.000) bị ProductForm chặn', ({ I }) => {
  I.amOnPage('/admin-panel/products/create/');
  I.fillField('#id_name', 'Cây Trầu Bà Xanh Trồng Đất');
  I.fillField('#id_price', '50000');
  I.fillField('#id_old_price', '50000');
  I.click('Lưu sản phẩm');
  I.see('Giá cũ phải lớn hơn giá bán.');
});

