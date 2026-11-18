"""Kiểm thử hộp trắng FR3 - Giỏ hàng: CFG (đường cơ sở), Phủ điều kiện / MC/DC, Kiểm thử vòng lặp.

Mỗi test ứng với 1 test case trong docs/TestCase_FR3_Cart_WhiteBox.md và sheet
"Phong_CFG_MCDC_Loop" của docs/Report.xlsx.

Chạy:          python manage.py test cart.tests_whitebox -v 2
Đo độ phủ:     python -m coverage run --branch --source=cart manage.py test cart.tests_whitebox
               python -m coverage report -m
Tạo report:    python tools/build_cart_whitebox_report.py
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import RequestFactory

from products.models import Product
from .models import Cart, CartItem
from .tests import CartTestBase, QTY_MAX
from .views import get_user_cart

MISSING_ID = 999999


def vnd(value):
    """Định dạng số kiểu Việt Nam: 1234567 -> '1.234.567'."""
    return f'{value:,.0f}'.replace(',', '.')

# Kết quả thực tế của từng ca, dùng để ghi cột "Thực tế" khi tạo report.
OBSERVED = {}


class WhiteBoxBase(CartTestBase):
    def record(self, tc_id, actual):
        OBSERVED[tc_id] = actual

    def get(self, url):
        return self.client.get(url)

    def describe(self, response, product=None):
        """Mô tả kết quả: mã HTTP, nơi chuyển hướng, số lượng của SP sau request."""
        text = str(response.status_code)
        if response.status_code == 302:
            text += f" → {response['Location']}"
        if product is not None:
            q = self.qty(product)
            text += "; không có trong giỏ" if q is None else f"; q = {q}"
        return text

    def assert_login_redirect(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith('/accounts/login/'), response['Location'])
        self.assertIn('next=', response['Location'])

    def assert_back_to_cart(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/cart/')

    def badge(self):
        return self.client.get('/').context['cart_item_count']


# ---------------------------------------------------------------------------
# PHẦN 1. CFG - mỗi test đi đúng 1 đường cơ sở (basis path) của đồ thị luồng điều khiển
# ---------------------------------------------------------------------------
class GetUserCartPathTests(WhiteBoxBase):
    """get_user_cart (views.py:11-13): V(G) = 1."""

    def test_cfg_guc_p1_get_or_create_once(self):
        """WB-CFG-GUC-P1: 1 → E. Gọi 2 lần chỉ tạo 1 Cart."""
        user = User.objects.create_user('wb_guc', password='User@12345')
        first = get_user_cart(user)
        second = get_user_cart(user)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Cart.objects.filter(user=user).count(), 1)
        self.record('WB-CFG-GUC-P1', f"Cùng 1 Cart (id = {first.pk}); số Cart của user = 1")


class CartAddPathTests(WhiteBoxBase):
    """cart_add (views.py:16-32): V(G) = 5."""

    def test_cfg_add_p1_guest(self):
        """WB-CFG-ADD-P1: 1(T) → 2 → E."""
        r = self.get(f'/cart/add/{self.p_a.id}/')
        self.assert_login_redirect(r)
        self.assertFalse(CartItem.objects.exists())
        self.record('WB-CFG-ADD-P1', self.describe(r) + "; không tạo CartItem")

    def test_cfg_add_p2_missing_product(self):
        """WB-CFG-ADD-P2: 1(F) → 3(không thấy) → 4 → E."""
        self.login()
        r = self.get(f'/cart/add/{MISSING_ID}/')
        self.assertEqual(r.status_code, 404)
        self.assertFalse(CartItem.objects.exists())
        self.record('WB-CFG-ADD-P2', self.describe(r) + "; không tạo CartItem")

    def test_cfg_add_p3_new_item(self):
        """WB-CFG-ADD-P3: 1(F) → 3 → 5 → 6(F) → 9 → E."""
        self.login()
        r = self.get(f'/cart/add/{self.p_a.id}/')
        self.assert_back_to_cart(r)
        self.assertEqual(self.qty(self.p_a), 1)
        self.record('WB-CFG-ADD-P3', self.describe(r, self.p_a))

    def test_cfg_add_p4_existing_below_max(self):
        """WB-CFG-ADD-P4: 1(F) → 3 → 5 → 6(T) → 7(T) → 8 → 9 → E."""
        self.login()
        self.set_qty(self.p_a, 1)
        r = self.get(f'/cart/add/{self.p_a.id}/')
        self.assert_back_to_cart(r)
        self.assertEqual(self.qty(self.p_a), 2)
        self.record('WB-CFG-ADD-P4', self.describe(r, self.p_a))

    def test_cfg_add_p5_existing_at_max(self):
        """WB-CFG-ADD-P5: 1(F) → 3 → 5 → 6(T) → 7(F) → 9 → E."""
        self.login()
        self.set_qty(self.p_a, QTY_MAX)
        r = self.get(f'/cart/add/{self.p_a.id}/')
        self.assert_back_to_cart(r)
        self.assertEqual(self.qty(self.p_a), QTY_MAX)
        self.record('WB-CFG-ADD-P5', self.describe(r, self.p_a))


class CartRemovePathTests(WhiteBoxBase):
    """cart_remove (views.py:35-41): V(G) = 3."""

    def test_cfg_rem_p1_guest(self):
        """WB-CFG-REM-P1: 1(F) → 2 → E."""
        r = self.get(f'/cart/remove/{self.p_a.id}/')
        self.assert_login_redirect(r)
        self.record('WB-CFG-REM-P1', self.describe(r))

    def test_cfg_rem_p2_missing_product(self):
        """WB-CFG-REM-P2: 1(T) → 3(không thấy) → 4 → E."""
        self.login()
        r = self.get(f'/cart/remove/{MISSING_ID}/')
        self.assertEqual(r.status_code, 404)
        self.record('WB-CFG-REM-P2', self.describe(r))

    def test_cfg_rem_p3_delete(self):
        """WB-CFG-REM-P3: 1(T) → 3 → 5 → E."""
        self.login()
        self.set_qty(self.p_a, 5)
        r = self.get(f'/cart/remove/{self.p_a.id}/')
        self.assert_back_to_cart(r)
        self.assertIsNone(self.qty(self.p_a))
        self.record('WB-CFG-REM-P3', self.describe(r, self.p_a))


class CartIncreasePathTests(WhiteBoxBase):
    """cart_increase (views.py:44-54): V(G) = 5."""

    def test_cfg_inc_p1_guest(self):
        """WB-CFG-INC-P1: 1(F) → 2 → E."""
        r = self.get(f'/cart/increase/{self.p_a.id}/')
        self.assert_login_redirect(r)
        self.record('WB-CFG-INC-P1', self.describe(r))

    def test_cfg_inc_p2_missing_product(self):
        """WB-CFG-INC-P2: 1(T) → 3(không thấy) → 4 → E."""
        self.login()
        r = self.get(f'/cart/increase/{MISSING_ID}/')
        self.assertEqual(r.status_code, 404)
        self.record('WB-CFG-INC-P2', self.describe(r))

    def test_cfg_inc_p3_not_in_cart(self):
        """WB-CFG-INC-P3: 1(T) → 3 → 5(không thấy) → 4 → E."""
        self.login()
        r = self.get(f'/cart/increase/{self.p_a.id}/')
        self.assertEqual(r.status_code, 404)
        self.assertIsNone(self.qty(self.p_a))
        self.record('WB-CFG-INC-P3', self.describe(r, self.p_a))

    def test_cfg_inc_p4_below_max(self):
        """WB-CFG-INC-P4: 1(T) → 3 → 5 → 6(T) → 7 → 8 → E."""
        self.login()
        self.set_qty(self.p_a, 2)
        r = self.get(f'/cart/increase/{self.p_a.id}/')
        self.assert_back_to_cart(r)
        self.assertEqual(self.qty(self.p_a), 3)
        self.record('WB-CFG-INC-P4', self.describe(r, self.p_a))

    def test_cfg_inc_p5_at_max(self):
        """WB-CFG-INC-P5: 1(T) → 3 → 5 → 6(F) → 8 → E."""
        self.login()
        self.set_qty(self.p_a, QTY_MAX)
        r = self.get(f'/cart/increase/{self.p_a.id}/')
        self.assert_back_to_cart(r)
        self.assertEqual(self.qty(self.p_a), QTY_MAX)
        self.record('WB-CFG-INC-P5', self.describe(r, self.p_a))


class CartDecreasePathTests(WhiteBoxBase):
    """cart_decrease (views.py:57-70): V(G) = 5."""

    def test_cfg_dec_p1_guest(self):
        """WB-CFG-DEC-P1: 1(F) → 2 → E."""
        r = self.get(f'/cart/decrease/{self.p_a.id}/')
        self.assert_login_redirect(r)
        self.record('WB-CFG-DEC-P1', self.describe(r))

    def test_cfg_dec_p2_missing_product(self):
        """WB-CFG-DEC-P2: 1(T) → 3(không thấy) → 4 → E."""
        self.login()
        r = self.get(f'/cart/decrease/{MISSING_ID}/')
        self.assertEqual(r.status_code, 404)
        self.record('WB-CFG-DEC-P2', self.describe(r))

    def test_cfg_dec_p3_not_in_cart(self):
        """WB-CFG-DEC-P3: 1(T) → 3 → 5(không thấy) → 4 → E."""
        self.login()
        r = self.get(f'/cart/decrease/{self.p_a.id}/')
        self.assertEqual(r.status_code, 404)
        self.record('WB-CFG-DEC-P3', self.describe(r, self.p_a))

    def test_cfg_dec_p4_quantity_one_deletes(self):
        """WB-CFG-DEC-P4: 1(T) → 3 → 5 → 6(T) → 7 → 9 → E."""
        self.login()
        self.set_qty(self.p_a, 1)
        r = self.get(f'/cart/decrease/{self.p_a.id}/')
        self.assert_back_to_cart(r)
        self.assertIsNone(self.qty(self.p_a))
        self.record('WB-CFG-DEC-P4', self.describe(r, self.p_a))

    def test_cfg_dec_p5_quantity_above_one_saves(self):
        """WB-CFG-DEC-P5: 1(T) → 3 → 5 → 6(F) → 8 → 9 → E."""
        self.login()
        self.set_qty(self.p_a, 3)
        r = self.get(f'/cart/decrease/{self.p_a.id}/')
        self.assert_back_to_cart(r)
        self.assertEqual(self.qty(self.p_a), 2)
        self.record('WB-CFG-DEC-P5', self.describe(r, self.p_a))


class CartDetailPathTests(WhiteBoxBase):
    """cart_detail (views.py:73-82): V(G) = 3."""

    def test_cfg_det_p1_guest(self):
        """WB-CFG-DET-P1: 1(F) → 2 → E."""
        r = self.get('/cart/')
        self.assert_login_redirect(r)
        self.record('WB-CFG-DET-P1', self.describe(r))

    def test_cfg_det_p2_empty_cart_skips_loop(self):
        """WB-CFG-DET-P2: 1(T) → 3 → 4(F) → 6 → E (vòng lặp chạy 0 lần)."""
        self.login()
        r = self.get('/cart/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['total_price'], 0)
        self.assertContains(r, 'Giỏ hàng của bạn đang trống')
        self.record('WB-CFG-DET-P2', f"200; total_price = {r.context['total_price']}; hiện giỏ trống")

    def test_cfg_det_p3_one_item_loop_once(self):
        """WB-CFG-DET-P3: 1(T) → 3 → 4(T) → 5 → 4(F) → 6 → E (vòng lặp chạy 1 lần)."""
        self.login()
        self.set_qty(self.p_a, 2)
        r = self.get('/cart/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['total_price'], Decimal('100000'))
        self.record('WB-CFG-DET-P3', f"200; total_price = {vnd(r.context['total_price'])}")


class CartItemCountPathTests(WhiteBoxBase):
    """cart_item_count (context_processors.py:3-11): V(G) = 4."""

    def test_cfg_cic_p1_guest(self):
        """WB-CFG-CIC-P1: 1(F) → 7 → E."""
        count = self.badge()
        self.assertEqual(count, 0)
        self.record('WB-CFG-CIC-P1', f"cart_item_count = {count}")

    def test_cfg_cic_p2_no_cart_row(self):
        """WB-CFG-CIC-P2: 1(T) → 2(ngoại lệ DoesNotExist) → 6 → E."""
        user = User.objects.create_user('wb_no_cart', password='User@12345')
        self.client.force_login(user)
        count = self.badge()
        self.assertEqual(count, 0)
        self.assertFalse(Cart.objects.filter(user=user).exists())
        self.record('WB-CFG-CIC-P2', f"cart_item_count = {count}; không lỗi 500, không tạo Cart")

    def test_cfg_cic_p3_cart_without_items(self):
        """WB-CFG-CIC-P3: 1(T) → 2 → 3(F) → 5 → E (vòng lặp chạy 0 lần)."""
        Cart.objects.create(user=self.user)
        self.login()
        count = self.badge()
        self.assertEqual(count, 0)
        self.record('WB-CFG-CIC-P3', f"cart_item_count = {count}")

    def test_cfg_cic_p4_cart_with_items(self):
        """WB-CFG-CIC-P4: 1(T) → 2 → 3(T) → 4 → 3(F) → 5 → E."""
        self.login()
        self.set_qty(self.p_a, 2)
        self.set_qty(self.p_b, 3)
        count = self.badge()
        self.assertEqual(count, 5)
        self.record('WB-CFG-CIC-P4', f"cart_item_count = {count}")


class ModelMethodPathTests(WhiteBoxBase):
    """Các hàm 1 đường của models.py: Cart.__str__, CartItem.__str__, CartItem.total_price (V(G) = 1)."""

    def test_cfg_mod_p1_cart_str(self):
        """WB-CFG-MOD-P1: Cart.__str__."""
        cart = Cart.objects.create(user=self.user)
        self.assertEqual(str(cart), 'Cart - cartuser')
        self.record('WB-CFG-MOD-P1', f'"{cart}"')

    def test_cfg_mod_p2_cart_item_str(self):
        """WB-CFG-MOD-P2: CartItem.__str__."""
        cart = Cart.objects.create(user=self.user)
        item = CartItem.objects.create(cart=cart, product=self.p_a, quantity=3)
        self.assertEqual(str(item), 'Bình nước tre x 3')
        self.record('WB-CFG-MOD-P2', f'"{item}"')

    def test_cfg_mod_p3_cart_item_total_price(self):
        """WB-CFG-MOD-P3: CartItem.total_price."""
        cart = Cart.objects.create(user=self.user)
        item = CartItem.objects.create(cart=cart, product=self.p_a, quantity=3)
        self.assertEqual(item.total_price, Decimal('150000'))
        self.record('WB-CFG-MOD-P3', f"total_price = {vnd(item.total_price)}")


# ---------------------------------------------------------------------------
# PHẦN 2. Phủ điều kiện / MC/DC
#   D2 - views.py:28  `not created and cart_item.quantity < MAX_QUANTITY`
#        A = not created (SP đã có trong giỏ), B = quantity < MAX
#   D3 - views.py:50  `cart_item.quantity < MAX_QUANTITY`
#   D4 - views.py:65  `cart_item.quantity <= 0` (sau khi đã trừ 1)
#   D1, D5, D6 và các điều kiện ẩn chỉ có 1 điều kiện đơn: dùng các ca CFG ở trên.
# ---------------------------------------------------------------------------
class CartAddMcdcTests(WhiteBoxBase):
    """D2 - views.py:28: 2 điều kiện, MC/DC cần tối thiểu n + 1 = 3 ca."""

    def test_mcdc_d2_tc1_a_true_b_true(self):
        """WB-MCDC-D2-01: A = T, B = T → quyết định T: q 1 → 2."""
        self.login()
        self.set_qty(self.p_a, 1)
        r = self.get(f'/cart/add/{self.p_a.id}/')
        self.assertEqual(self.qty(self.p_a), 2)
        self.record('WB-MCDC-D2-01', self.describe(r, self.p_a))

    def test_mcdc_d2_tc2_a_true_b_false(self):
        """WB-MCDC-D2-02: A = T, B = F → quyết định F: giữ q = MAX."""
        self.login()
        self.set_qty(self.p_a, QTY_MAX)
        r = self.get(f'/cart/add/{self.p_a.id}/')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.qty(self.p_a), QTY_MAX)
        self.record('WB-MCDC-D2-02', self.describe(r, self.p_a))

    def test_mcdc_d2_tc3_a_false(self):
        """WB-MCDC-D2-03: A = F (B không được đánh giá do ngắn mạch) → quyết định F: tạo q = 1."""
        self.login()
        r = self.get(f'/cart/add/{self.p_a.id}/')
        self.assertEqual(self.qty(self.p_a), 1)
        self.record('WB-MCDC-D2-03', self.describe(r, self.p_a))

    def test_mcdc_d2_tc4_b_boundary_max_minus_1(self):
        """WB-MCDC-D2-04: A = T, B = T tại biên MAX − 1 → q lên đúng MAX."""
        self.login()
        self.set_qty(self.p_a, QTY_MAX - 1)
        r = self.get(f'/cart/add/{self.p_a.id}/')
        self.assertEqual(self.qty(self.p_a), QTY_MAX)
        self.record('WB-MCDC-D2-04', self.describe(r, self.p_a))

    def test_mcdc_d2_tc5_a_false_b_false_is_infeasible(self):
        """WB-MCDC-D2-05: A = F kéo theo SP mới có q = default 1 < MAX, nên tổ hợp (F, F) không thể xảy ra."""
        self.assertEqual(CartItem._meta.get_field('quantity').default, 1)
        self.login()
        self.get(f'/cart/add/{self.p_a.id}/')
        q = self.qty(self.p_a)
        self.assertLess(q, QTY_MAX)
        self.record('WB-MCDC-D2-05', f"SP mới luôn có q = {q} < MAX → B luôn T khi A = F")


class CartIncreaseMcdcTests(WhiteBoxBase):
    """D3 - views.py:50: 1 điều kiện, cần 2 ca; chọn đúng biên MAX − 1 / MAX."""

    def test_mcdc_d3_tc1_true_at_max_minus_1(self):
        """WB-MCDC-D3-01: q = MAX − 1 → T: q lên MAX."""
        self.login()
        self.set_qty(self.p_a, QTY_MAX - 1)
        r = self.get(f'/cart/increase/{self.p_a.id}/')
        self.assertEqual(self.qty(self.p_a), QTY_MAX)
        self.record('WB-MCDC-D3-01', self.describe(r, self.p_a))

    def test_mcdc_d3_tc2_false_at_max(self):
        """WB-MCDC-D3-02: q = MAX → F: giữ nguyên, không lỗi 500."""
        self.login()
        self.set_qty(self.p_a, QTY_MAX)
        r = self.get(f'/cart/increase/{self.p_a.id}/')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.qty(self.p_a), QTY_MAX)
        self.record('WB-MCDC-D3-02', self.describe(r, self.p_a))


class CartDecreaseMcdcTests(WhiteBoxBase):
    """D4 - views.py:65: 1 điều kiện quan hệ `<= 0`; thêm ca q = 0 để kiểm tra toán tử."""

    def test_mcdc_d4_tc1_true_quantity_one(self):
        """WB-MCDC-D4-01: q = 1 → sau khi trừ còn 0 → T: xóa CartItem."""
        self.login()
        self.set_qty(self.p_a, 1)
        r = self.get(f'/cart/decrease/{self.p_a.id}/')
        self.assertIsNone(self.qty(self.p_a))
        self.record('WB-MCDC-D4-01', self.describe(r, self.p_a))

    def test_mcdc_d4_tc2_false_quantity_two(self):
        """WB-MCDC-D4-02: q = 2 → sau khi trừ còn 1 → F: lưu q = 1."""
        self.login()
        self.set_qty(self.p_a, 2)
        r = self.get(f'/cart/decrease/{self.p_a.id}/')
        self.assertEqual(self.qty(self.p_a), 1)
        self.record('WB-MCDC-D4-02', self.describe(r, self.p_a))

    def test_mcdc_d4_tc3_true_quantity_zero(self):
        """WB-MCDC-D4-03: q = 0 (dữ liệu bất thường, PositiveIntegerField cho phép) → −1 → T: xóa, không 500.

        Nếu điều kiện bị viết thành `== 0` thì −1 sẽ được lưu và vi phạm ràng buộc quantity >= 0.
        """
        self.login()
        self.set_qty(self.p_a, 0)
        r = self.get(f'/cart/decrease/{self.p_a.id}/')
        self.assert_back_to_cart(r)
        self.assertIsNone(self.qty(self.p_a))
        self.record('WB-MCDC-D4-03', self.describe(r, self.p_a))


class ContextProcessorMcdcTests(WhiteBoxBase):
    """D5 - context_processors.py:4 `is_authenticated` gọi trực tiếp hàm (không qua view)."""

    def test_mcdc_d5_tc1_authenticated_false(self):
        """WB-MCDC-D5-01: is_authenticated = F → 0."""
        from django.contrib.auth.models import AnonymousUser
        from .context_processors import cart_item_count
        request = RequestFactory().get('/')
        request.user = AnonymousUser()
        result = cart_item_count(request)
        self.assertEqual(result, {'cart_item_count': 0})
        self.record('WB-MCDC-D5-01', str(result))

    def test_mcdc_d5_tc2_authenticated_true(self):
        """WB-MCDC-D5-02: is_authenticated = T, có Cart → tổng quantity."""
        from .context_processors import cart_item_count
        self.set_qty(self.p_a, 4)
        request = RequestFactory().get('/')
        request.user = self.user
        result = cart_item_count(request)
        self.assertEqual(result, {'cart_item_count': 4})
        self.record('WB-MCDC-D5-02', str(result))


# ---------------------------------------------------------------------------
# PHẦN 3. Kiểm thử vòng lặp
#   L1 - views.py:77                 sum(price × quantity) theo từng CartItem (+ vòng {% for %} của template)
#   L2 - context_processors.py:7     sum(quantity) theo từng CartItem
# Cả hai là vòng lặp đơn, số lần lặp = số dòng CartItem của giỏ.
# Vì unique_together (cart, product), số lần lặp tối đa n = số sản phẩm trong hệ thống = 10.
# Dữ liệu: SP thứ i (theo id) có giá PRICES[i - 1] và số lượng q = i.
# ---------------------------------------------------------------------------
EXTRA_PRICES = [15000, 25000, 35000, 40000, 55000, 60000]
PRICES = [50000, 30000, 20000, 45000] + EXTRA_PRICES   # 4 SP đầu tạo trong CartTestBase
N_LOOP = len(PRICES)                                     # n = 10

# Số lần lặp k → (tổng tiền mong đợi, tổng quantity mong đợi), với q_i = i
LOOP_EXPECTED = {
    0: (0, 0),
    1: (50000, 1),
    2: (110000, 3),
    5: (425000, 15),
    9: (1635000, 45),
    10: (2235000, 55),
}


class CartLoopTests(WhiteBoxBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        for i, price in enumerate(EXTRA_PRICES, start=1):
            Product.objects.create(name=f'SP vòng lặp {i}', price=Decimal(price))
        cls.products = list(Product.objects.order_by('id'))

    def setUp(self):
        super().setUp()
        # Điều kiện tiên quyết: n = số SP trong hệ thống = 10, đúng thứ tự giá đã chọn
        self.assertEqual(len(self.products), N_LOOP)
        self.assertEqual([int(p.price) for p in self.products], PRICES)
        self.login()

    def fill(self, k, quantity=None):
        for i, product in enumerate(self.products[:k], start=1):
            self.set_qty(product, quantity if quantity is not None else i)

    def check_cart(self, tc_id, k):
        total, count = LOOP_EXPECTED[k]
        r = self.get('/cart/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context['cart_items']), k)              # số lần lặp
        self.assertEqual(r.context['total_price'], Decimal(total))     # L1
        self.assertEqual(r.context['cart_item_count'], count)          # L2
        if k:
            self.assertContains(r, f'{k} sản phẩm trong giỏ')         # vòng {% for %} của template
            self.assertContains(r, '<div class="cart-item">', count=k)
        else:
            self.assertContains(r, 'Giỏ hàng của bạn đang trống')
        self.record(tc_id, f"200; lặp {k} lần; total_price = {vnd(r.context['total_price'])}; "
                           f"cart_item_count = {r.context['cart_item_count']}")

    def test_loop_01_skip_zero_iterations(self):
        """WB-LOOP-01: 0 lần lặp (bỏ qua vòng lặp)."""
        Cart.objects.create(user=self.user)
        self.check_cart('WB-LOOP-01', 0)

    def test_loop_02_one_iteration(self):
        """WB-LOOP-02: 1 lần lặp."""
        self.fill(1)
        self.check_cart('WB-LOOP-02', 1)

    def test_loop_03_two_iterations(self):
        """WB-LOOP-03: 2 lần lặp."""
        self.fill(2)
        self.check_cart('WB-LOOP-03', 2)

    def test_loop_04_typical_m_iterations(self):
        """WB-LOOP-04: m = 5 lần lặp (giá trị điển hình, 2 < m < n − 1)."""
        self.fill(5)
        self.check_cart('WB-LOOP-04', 5)

    def test_loop_05_n_minus_1_iterations(self):
        """WB-LOOP-05: n − 1 = 9 lần lặp."""
        self.fill(9)
        self.check_cart('WB-LOOP-05', 9)

    def test_loop_06_n_iterations(self):
        """WB-LOOP-06: n = 10 lần lặp (giỏ chứa mọi SP trong hệ thống)."""
        self.fill(10)
        self.check_cart('WB-LOOP-06', 10)

    def test_loop_07_n_plus_1_attempt(self):
        """WB-LOOP-07: thử n + 1 lần: thêm lại SP đã có khi giỏ đủ n dòng → vẫn n lần lặp, q của SP đó + 1."""
        self.fill(10)
        r = self.get(f'/cart/add/{self.products[0].id}/')
        self.assert_back_to_cart(r)
        r = self.get('/cart/')
        self.assertEqual(len(r.context['cart_items']), N_LOOP)
        self.assertEqual(CartItem.objects.filter(cart__user=self.user).count(), N_LOOP)
        self.assertEqual(r.context['total_price'], Decimal(2235000 + 50000))
        self.assertEqual(r.context['cart_item_count'], 56)
        self.record('WB-LOOP-07', f"200; vẫn lặp {len(r.context['cart_items'])} lần; "
                                  f"total_price = {vnd(r.context['total_price'])}; "
                                  f"cart_item_count = {r.context['cart_item_count']}")

    def test_loop_08_n_iterations_extreme_values(self):
        """WB-LOOP-08: n = 10 lần lặp, mỗi lần q = MAX (giá trị cực đại trong thân vòng lặp)."""
        self.fill(10, quantity=QTY_MAX)
        r = self.get('/cart/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['total_price'], Decimal(QTY_MAX) * sum(PRICES))
        self.assertEqual(r.context['cart_item_count'], QTY_MAX * N_LOOP)
        self.record('WB-LOOP-08', f"200; total_price = {vnd(r.context['total_price'])}; "
                                  f"cart_item_count = {vnd(r.context['cart_item_count'])}")
