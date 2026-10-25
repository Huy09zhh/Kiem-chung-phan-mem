Feature('Green Shop - Smoke Test');

Scenario('Trang chủ mở được', ({ I }) => {
  I.amOnPage('/');
  I.seeElement('body');
});