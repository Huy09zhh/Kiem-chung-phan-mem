"""Unit test theo bảng quyết định FR3 - Giỏ hàng (Decision Table Testing).

Mỗi test ứng với 1 luật (rule) trong docs/TestCase_FR3_Cart_StateTransition_DecisionTable.md.
Chạy: python manage.py test cart.tests_decision_table -v 2

Điều kiện: C1 đã đăng nhập, C2 sản phẩm tồn tại, C3 sản phẩm có trong giỏ, C4 số lượng hiện tại.
"""
from django.contrib.auth.models import User

from orders.models import Order
from .tests import CartTestBase, QTY_MAX

MISSING_ID = 999999
CHECKOUT_DATA = {'full_name': 'Khach Test', 'phone': '0912345678', 'address': '1 Duong Test'}


class CartDecisionTableBase(CartTestBase):
    def assert_login_redirect(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f'/accounts/login/?next={url}')

    def assert_status(self, url, status):
        self.assertEqual(self.client.get(url).status_code, status)

    def assert_back_to_cart(self, url):
        self.assertRedirects(self.client.get(url), '/cart/')


class CartAddDecisionTests(CartDecisionTableBase):
    """Bảng 1: Thêm sản phẩm - GET /cart/add/<id>/."""

    def test_dt_r01_guest_is_redirected_even_if_product_missing(self):
        """R1: C1=N, các điều kiện khác bất kỳ -> chuyển login, không báo 404."""
        self.assert_login_redirect(f'/cart/add/{self.p_a.id}/')
        self.assert_login_redirect(f'/cart/add/{MISSING_ID}/')

    def test_dt_r02_missing_product_404(self):
        """R2: C1=Y, C2=N -> 404."""
        self.login()
        self.assert_status(f'/cart/add/{MISSING_ID}/', 404)

    def test_dt_r03_product_not_in_cart_creates_item(self):
        """R3: C1=Y, C2=Y, C3=N -> tạo CartItem quantity = 1."""
        self.login()
        self.assert_back_to_cart(f'/cart/add/{self.p_a.id}/')
        self.assertEqual(self.qty(self.p_a), 1)

    def test_dt_r04_below_max_increments(self):
        """R4: C1=Y, C2=Y, C3=Y, C4<MAX -> quantity + 1."""
        self.login()
        self.set_qty(self.p_a, 4)
        self.assert_back_to_cart(f'/cart/add/{self.p_a.id}/')
        self.assertEqual(self.qty(self.p_a), 5)

    def test_dt_r05_at_max_unchanged(self):
        """R5: C1=Y, C2=Y, C3=Y, C4=MAX -> giữ nguyên."""
        self.login()
        self.set_qty(self.p_a, QTY_MAX)
        self.assert_back_to_cart(f'/cart/add/{self.p_a.id}/')
        self.assertEqual(self.qty(self.p_a), QTY_MAX)


class CartIncreaseDecisionTests(CartDecisionTableBase):
    """Bảng 2: Tăng số lượng - GET /cart/increase/<id>/."""

    def test_dt_r06_guest_is_redirected_even_if_product_missing(self):
        """R6: C1=N -> chuyển login."""
        self.assert_login_redirect(f'/cart/increase/{self.p_a.id}/')
        self.assert_login_redirect(f'/cart/increase/{MISSING_ID}/')

    def test_dt_r07_missing_product_404(self):
        """R7: C1=Y, C2=N -> 404."""
        self.login()
        self.assert_status(f'/cart/increase/{MISSING_ID}/', 404)

    def test_dt_r08_product_not_in_cart_404(self):
        """R8: C1=Y, C2=Y, C3=N -> 404, không tự tạo CartItem."""
        self.login()
        self.assert_status(f'/cart/increase/{self.p_a.id}/', 404)
        self.assertIsNone(self.qty(self.p_a))

    def test_dt_r09_below_max_increments(self):
        """R9: C1=Y, C2=Y, C3=Y, C4<MAX -> quantity + 1."""
        self.login()
        self.set_qty(self.p_a, 4)
        self.assert_back_to_cart(f'/cart/increase/{self.p_a.id}/')
        self.assertEqual(self.qty(self.p_a), 5)

    def test_dt_r10_at_max_unchanged(self):
        """R10: C1=Y, C2=Y, C3=Y, C4=MAX -> giữ nguyên."""
        self.login()
        self.set_qty(self.p_a, QTY_MAX)
        self.assert_back_to_cart(f'/cart/increase/{self.p_a.id}/')
        self.assertEqual(self.qty(self.p_a), QTY_MAX)


class CartDecreaseDecisionTests(CartDecisionTableBase):
    """Bảng 3: Giảm số lượng - GET /cart/decrease/<id>/."""

    def test_dt_r11_guest_is_redirected_even_if_product_missing(self):
        """R11: C1=N -> chuyển login."""
        self.assert_login_redirect(f'/cart/decrease/{self.p_a.id}/')
        self.assert_login_redirect(f'/cart/decrease/{MISSING_ID}/')

    def test_dt_r12_missing_product_404(self):
        """R12: C1=Y, C2=N -> 404."""
        self.login()
        self.assert_status(f'/cart/decrease/{MISSING_ID}/', 404)

    def test_dt_r13_product_not_in_cart_404(self):
        """R13: C1=Y, C2=Y, C3=N -> 404."""
        self.login()
        self.assert_status(f'/cart/decrease/{self.p_a.id}/', 404)

    def test_dt_r14_quantity_one_deletes_item(self):
        """R14: C1=Y, C2=Y, C3=Y, C4=1 -> xóa CartItem."""
        self.login()
        self.set_qty(self.p_a, 1)
        self.assert_back_to_cart(f'/cart/decrease/{self.p_a.id}/')
        self.assertIsNone(self.qty(self.p_a))

    def test_dt_r15_quantity_above_one_decrements(self):
        """R15: C1=Y, C2=Y, C3=Y, C4>1 -> quantity - 1."""
        self.login()
        self.set_qty(self.p_a, 4)
        self.assert_back_to_cart(f'/cart/decrease/{self.p_a.id}/')
        self.assertEqual(self.qty(self.p_a), 3)


class CartRemoveDecisionTests(CartDecisionTableBase):
    """Bảng 4: Xóa khỏi giỏ - GET /cart/remove/<id>/."""

    def test_dt_r16_guest_is_redirected_even_if_product_missing(self):
        """R16: C1=N -> chuyển login."""
        self.assert_login_redirect(f'/cart/remove/{self.p_a.id}/')
        self.assert_login_redirect(f'/cart/remove/{MISSING_ID}/')

    def test_dt_r17_missing_product_404(self):
        """R17: C1=Y, C2=N -> 404."""
        self.login()
        self.assert_status(f'/cart/remove/{MISSING_ID}/', 404)

    def test_dt_r18_product_not_in_cart_redirects_without_error(self):
        """R18: C1=Y, C2=Y, C3=N -> 302 về /cart/, không lỗi."""
        self.login()
        response = self.client.get(f'/cart/remove/{self.p_a.id}/')
        self.assertRedirects(response, '/cart/')

    def test_dt_r19_product_in_cart_is_deleted(self):
        """R19: C1=Y, C2=Y, C3=Y -> xóa CartItem, không phụ thuộc số lượng."""
        self.login()
        self.set_qty(self.p_a, QTY_MAX)
        self.assert_back_to_cart(f'/cart/remove/{self.p_a.id}/')
        self.assertIsNone(self.qty(self.p_a))


class CartViewDecisionTests(CartDecisionTableBase):
    """Bảng 5: Xem giỏ hàng - GET /cart/."""

    def test_dt_r20_guest_is_redirected(self):
        """R20: C1=N -> chuyển login."""
        self.assert_login_redirect('/cart/')

    def test_dt_r21_empty_cart_hides_checkout(self):
        """R21: C1=Y, giỏ rỗng -> thông báo giỏ trống, không có link đặt hàng."""
        self.login()
        response = self.client.get('/cart/')
        self.assertContains(response, 'Giỏ hàng của bạn đang trống')
        self.assertNotContains(response, '/orders/checkout/')

    def test_dt_r22_cart_with_items_shows_total_and_checkout(self):
        """R22: C1=Y, giỏ có SP -> hiện tổng tiền và link đặt hàng."""
        self.login()
        self.set_qty(self.p_a, 2)
        self.set_qty(self.p_b, 1)
        response = self.client.get('/cart/')
        self.assertEqual(response.context['total_price'], 130000)
        self.assertContains(response, '/orders/checkout/')


class CartBadgeDecisionTests(CartDecisionTableBase):
    """Bảng 6: Số trên biểu tượng giỏ hàng - context processor cart_item_count."""

    def badge(self):
        return self.client.get('/').context['cart_item_count']

    def test_dt_r23_guest_badge_is_zero(self):
        """R23: C1=N -> 0."""
        self.assertEqual(self.badge(), 0)

    def test_dt_r24_user_without_cart_row_badge_is_zero(self):
        """R24: C1=Y, chưa có bản ghi Cart -> 0, không lỗi."""
        self.client.force_login(User.objects.create_user('dt_no_cart', password='User@12345'))
        self.assertEqual(self.badge(), 0)

    def test_dt_r25_badge_is_sum_of_quantities(self):
        """R25: C1=Y, có Cart -> tổng quantity của mọi SP, không phải số dòng."""
        self.login()
        self.set_qty(self.p_a, 2)
        self.set_qty(self.p_b, 3)
        self.assertEqual(self.badge(), 5)


class CartClearDecisionTests(CartDecisionTableBase):
    """Bảng 7: Dọn giỏ khi đặt hàng và thanh toán (FR3.5, theo hành vi sau SCRUM-43)."""

    def setUp(self):
        super().setUp()
        self.login()

    def place_order(self, method):
        self.set_qty(self.p_a, 2)
        self.client.post('/orders/checkout/', {**CHECKOUT_DATA, 'payment_method': method})
        return Order.objects.filter(user=self.user).latest('id')

    def assert_result(self, order, status, quantity):
        order.refresh_from_db()
        self.assertEqual(order.status, status)
        self.assertEqual(self.qty(self.p_a), quantity)

    def test_dt_r26_empty_cart_creates_no_order(self):
        """R26: C1=N -> về /cart/, không tạo đơn."""
        response = self.client.post('/orders/checkout/', {**CHECKOUT_DATA, 'payment_method': 'cod'})
        self.assertEqual(response.url, '/cart/')
        self.assertFalse(Order.objects.filter(user=self.user).exists())

    def test_dt_r27_cod_order_clears_cart(self):
        """R27: C1=Y, COD, tạo đơn -> pending, xóa giỏ."""
        self.assert_result(self.place_order('cod'), 'pending', None)

    def test_dt_r28_qr_order_keeps_cart(self):
        """R28: C1=Y, QR, tạo đơn -> awaiting_transfer, giữ giỏ."""
        self.assert_result(self.place_order('qr'), 'awaiting_transfer', 2)

    def test_dt_r29_qr_confirm_clears_cart(self):
        """R29: C1=Y, QR, xác nhận đã chuyển khoản -> paid, xóa giỏ."""
        order = self.place_order('qr')
        self.client.post(f'/orders/qr/{order.id}/confirm/')
        self.assert_result(order, 'paid', None)

    def test_dt_r30_qr_cancel_keeps_cart(self):
        """R30: C1=Y, QR, hủy đơn -> cancelled, giữ giỏ."""
        order = self.place_order('qr')
        self.client.post(f'/orders/{order.id}/cancel/')
        self.assert_result(order, 'cancelled', 2)

    def test_dt_r31_mock_order_keeps_cart(self):
        """R31: C1=Y, Mock, tạo đơn -> pending, giữ giỏ."""
        self.assert_result(self.place_order('mock'), 'pending', 2)

    def test_dt_r32_mock_success_clears_cart(self):
        """R32: C1=Y, Mock, thanh toán thành công -> paid, xóa giỏ."""
        order = self.place_order('mock')
        self.client.post(f'/orders/mock/{order.id}/success/')
        self.assert_result(order, 'paid', None)

    def test_dt_r33_mock_failure_keeps_cart(self):
        """R33: C1=Y, Mock, thanh toán thất bại -> failed, giữ giỏ."""
        order = self.place_order('mock')
        self.client.post(f'/orders/mock/{order.id}/fail/')
        self.assert_result(order, 'failed', 2)
