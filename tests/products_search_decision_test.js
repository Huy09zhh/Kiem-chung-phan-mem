Feature('Products & Search - Black-box Decision Table & Search/Filter (TC-PS)');

Scenario('TC-PS-044 (R1): Mở danh sách sản phẩm mặc định không lọc/sắp xếp', ({ I }) => {
  I.amOnPage('/products/');
  I.see('Tất cả sản phẩm');
  I.seeElement('.product-grid-list');
  I.dontSee('Server Error');
});

Scenario('TC-PS-045 (R2): Tìm kiếm sản phẩm theo từ khóa q trên thanh tìm kiếm', ({ I }) => {
  I.amOnPage('/products/');
  I.fillField('#navbar-search-input', 'cây');
  I.click('#navbar-search-box button[type="submit"]');
  I.seeInCurrentUrl('q=c%C3%A2y');
  I.see('Kết quả tìm kiếm cho:');
});

Scenario('TC-PS-046 (R3): Sắp xếp sản phẩm giá thấp đến cao (sort=price_asc)', ({ I }) => {
  I.amOnPage('/products/?category=1');
  I.click('Giá thấp đến cao');
  I.seeInCurrentUrl('sort=price_asc');
  I.see('Tất cả sản phẩm');
});

Scenario('TC-PS-047 (R4): Tổ hợp q + category sai định dạng (abc) + sort=name_asc không crash 500', ({ I }) => {
  I.amOnPage('/products/?q=a&category=abc&sort=name_asc');
  I.see('Tất cả sản phẩm');
  I.dontSee('ValueError');
  I.dontSee('Server Error');
});

Scenario('TC-PS-048 (R5): Tìm từ khóa không tồn tại hiển thị hộp danh sách rỗng an toàn', ({ I }) => {
  I.amOnPage('/products/?q=KhongTonTaiSanPhamNao9999');
  I.see('Chưa tìm thấy sản phẩm phù hợp');
});

Scenario('TC-PS-004: Gợi ý tìm kiếm tức thì (Live Search AJAX) hiển thị dropdown', ({ I }) => {
  I.amOnPage('/');
  I.fillField('#navbar-search-input', 'cây');
  I.waitForElement('#navbar-search-dropdown', 5);
});

Scenario('TC-PS-007 & TC-PS-010: Xem chi tiết sản phẩm hợp lệ và ID không tồn tại (404)', ({ I }) => {
  I.amOnPage('/products/');
  I.click('.home-product-card h3 a');
  I.seeElement('.detail-title');

  I.amOnPage('/products/999999/');
  I.see('404');
});

