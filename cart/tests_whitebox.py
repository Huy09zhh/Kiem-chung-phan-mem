"""
Kiểm thử hộp trắng (Chương 4, IV.4 – Control Flow Testing) cho 2 chức năng giỏ hàng đã kiểm thử hộp đen.

Phân hệ FR3: Quản lý giỏ hàng.
  1. Thêm sản phẩm vào giỏ: cart.views.cart_add       (dòng 16–32)
     9 câu lệnh, 2 quyết định (4 nhánh), V(G) = 3
  2. Giảm số lượng        : cart.views.cart_decrease  (dòng 57–70)
     8 câu lệnh, 1 quyết định (2 nhánh), V(G) = 2

Mã test case trong report (sheet WhiteBox_Phong): test_wb_add_s1 → WB-ADD-S1, test_wb_add_b3 → WB-ADD-B3,
test_c1_... của CartAddConditionTests → WB-ADD-C1..C3, test_wb_dec_s1/s2 → WB-DEC-S1/S2.

Mỗi class là một bộ test trả lời câu hỏi "tối thiểu bao nhiêu test case để bao phủ 100%":
  CartAddStatementTests      : 2 test -> bao phủ câu lệnh 100% (nhánh mới 3/4)
  CartAddBranchTests         : 3 test -> bao phủ nhánh 100% (4/4)
  CartAddConditionTests      : 3 test -> bao phủ nhánh – điều kiện / tổ hợp điều kiện của D2 (not created and quantity < MAX)
  CartDecreaseStatementTests : 2 test -> bao phủ câu lệnh 100% và nhánh 100% (2/2)

Chạy tất cả:   python manage.py test cart.tests_whitebox -v 2
Đo độ phủ một bộ (ví dụ bộ phủ câu lệnh của cart_add):
  coverage erase
  coverage run --branch --source=cart manage.py test cart.tests_whitebox.CartAddStatementTests
  coverage json -o coverage.json
  python tools/build_cart_whitebox_report.py --measure coverage.json cart_add
"""
from .models import CartItem
from .tests import CartTestBase, QTY_MAX


class CartWhiteBoxBase(CartTestBase):
    """Dữ liệu chung lấy từ bộ hộp đen: user cartuser, sản phẩm A (p_a) giá 50.000."""

    def assert_back_to_cart(self, resp):
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], '/cart/')


# ---------------------------------------------------------------------------
# 1. THÊM SẢN PHẨM VÀO GIỎ (cart_add)
#    D1: not request.user.is_authenticated?
#    D2: not created (A) and cart_item.quantity < MAX_QUANTITY (B)?
# ---------------------------------------------------------------------------
class CartAddBase(CartWhiteBoxBase):
    def add(self):
        return self.client.get(f'/cart/add/{self.p_a.id}/')


class CartAddStatementTests(CartAddBase):
    """Tối thiểu 2 test để bao phủ 100% câu lệnh. Nhánh False của D2 chưa chạy (3/4 nhánh)."""

    def test_wb_add_s1_chua_dang_nhap(self):
        # D1 T
        resp = self.add()
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], f'/accounts/login/?next=/cart/add/{self.p_a.id}/')
        self.assertFalse(CartItem.objects.exists())

    def test_wb_add_s2_san_pham_da_co_trong_gio(self):
        # D1 F, D2 T (A T, B T)
        self.login()
        self.set_qty(self.p_a, 1)
        self.assert_back_to_cart(self.add())
        self.assertEqual(self.qty(self.p_a), 2)


class CartAddBranchTests(CartAddStatementTests):
    """Tối thiểu 3 test để bao phủ 100% nhánh (2 test kế thừa ở trên + 1 test dưới)."""

    def test_wb_add_b3_gio_rong(self):
        # D1 F, D2 F (A F)
        self.login()
        self.assert_back_to_cart(self.add())
        self.assertEqual(self.qty(self.p_a), 1)


class CartAddConditionTests(CartAddBase):
    """Tổ hợp điều kiện của D2: A = not created (SP đã có trong giỏ), B = quantity < MAX_QUANTITY."""

    def test_c1_a_dung_b_dung(self):        # SP đã có, q = 1 -> D2 T, tăng lên 2
        self.login()
        self.set_qty(self.p_a, 1)
        self.assert_back_to_cart(self.add())
        self.assertEqual(self.qty(self.p_a), 2)

    def test_c2_a_dung_b_sai(self):         # SP đã có, q = MAX -> D2 F, giữ MAX (BUG-CART-01 đã sửa)
        self.login()
        self.set_qty(self.p_a, QTY_MAX)
        self.assert_back_to_cart(self.add())
        self.assertEqual(self.qty(self.p_a), QTY_MAX)

    def test_c3_a_sai(self):                # SP mới -> D2 F, B không được xét (and ngắt mạch)
        self.login()
        self.assert_back_to_cart(self.add())
        # Dòng vừa tạo luôn có q = 1 < MAX, nên tổ hợp A F – B F không xảy ra được
        self.assertEqual(self.qty(self.p_a), 1)
        self.assertLess(self.qty(self.p_a), QTY_MAX)


# ---------------------------------------------------------------------------
# 2. GIẢM SỐ LƯỢNG (cart_decrease)
#    D1: cart_item.quantity <= 0 (sau khi đã trừ 1)?
# ---------------------------------------------------------------------------
class CartDecreaseStatementTests(CartWhiteBoxBase):
    """Tối thiểu 2 test để bao phủ 100% câu lệnh; 2 test này cũng bao phủ 100% nhánh (2/2)."""

    def decrease(self):
        return self.client.get(f'/cart/decrease/{self.p_a.id}/')

    def test_wb_dec_s1_so_luong_1_bi_xoa(self):        # D1 T
        self.login()
        self.set_qty(self.p_a, 1)
        self.assert_back_to_cart(self.decrease())
        self.assertIsNone(self.qty(self.p_a))

    def test_wb_dec_s2_so_luong_2_con_1(self):         # D1 F
        self.login()
        self.set_qty(self.p_a, 2)
        self.assert_back_to_cart(self.decrease())
        self.assertEqual(self.qty(self.p_a), 1)
