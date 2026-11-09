"""Unit test chuyển đổi trạng thái FR3 - Giỏ hàng (State Transition Testing).

Mỗi test ứng với 1 test case trong docs/TestCase_FR3_Cart_StateTransition_DecisionTable.md.
Chạy: python manage.py test cart.tests_state_transition -v 2

Có 2 máy trạng thái:
  - Một sản phẩm trong giỏ: ABSENT -> ONE -> MANY -> AT_MAX (theo CartItem.quantity).
  - Cả giỏ hàng: EMPTY <-> NOT_EMPTY (theo số CartItem, gồm cả lúc đặt hàng - FR3.5).
"""
from django.contrib.auth.models import User

from orders.models import Order
from products.models import Product
from .models import Cart, CartItem
from .tests import CartTestBase, QTY_MAX

ABSENT = 'ABSENT'    # sản phẩm không có trong giỏ
ONE = 'ONE'          # quantity = 1
MANY = 'MANY'        # 1 < quantity < QTY_MAX
AT_MAX = 'AT_MAX'    # quantity = QTY_MAX

START_QTY = {ABSENT: None, ONE: 1, MANY: 5, AT_MAX: QTY_MAX}

# (trạng thái, sự kiện) -> (số lượng sau sự kiện, mã HTTP). Số lượng None nghĩa là không có trong giỏ.
TRANSITIONS = {
    (ABSENT, 'add'): (1, 302),
    (ABSENT, 'increase'): (None, 404),
    (ABSENT, 'decrease'): (None, 404),
    (ABSENT, 'remove'): (None, 302),
    (ONE, 'add'): (2, 302),
    (ONE, 'increase'): (2, 302),
    (ONE, 'decrease'): (None, 302),
    (ONE, 'remove'): (None, 302),
    (MANY, 'add'): (6, 302),
    (MANY, 'increase'): (6, 302),
    (MANY, 'decrease'): (4, 302),
    (MANY, 'remove'): (None, 302),
    (AT_MAX, 'add'): (QTY_MAX, 302),
    (AT_MAX, 'increase'): (QTY_MAX, 302),
    (AT_MAX, 'decrease'): (QTY_MAX - 1, 302),
    (AT_MAX, 'remove'): (None, 302),
}

EVENTS = ('add', 'increase', 'decrease', 'remove')
CHECKOUT_DATA = {'full_name': 'Khach Test', 'phone': '0912345678', 'address': '1 Duong Test'}


class CartStateTestBase(CartTestBase):
    def setUp(self):
        super().setUp()
        self.login()

    def fire(self, event, product=None):
        return self.client.get(f'/cart/{event}/{(product or self.p_a).id}/')

    def set_state(self, quantity, product=None):
        product = product or self.p_a
        if quantity is None:
            CartItem.objects.filter(cart__user=self.user, product=product).delete()
        else:
            self.set_qty(product, quantity)


class CartItemStateTransitionTests(CartStateTestBase):
    """Máy trạng thái của một sản phẩm trong giỏ."""

    def test_st_01_all_state_event_pairs_follow_table(self):
        """TC-CART-ST-01: Toàn bộ 4 trạng thái x 4 sự kiện = 16 cặp đúng bảng chuyển trạng thái."""
        self.assertEqual(len(TRANSITIONS), 16)
        for (state, event), (expected_qty, expected_status) in TRANSITIONS.items():
            with self.subTest(state=state, event=event):
                self.set_state(START_QTY[state])
                response = self.fire(event)
                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(self.qty(self.p_a), expected_qty)

    def test_st_02_decrease_from_2_moves_many_to_one(self):
        """TC-CART-ST-02: MANY (biên 2) -decrease-> ONE."""
        self.set_state(2)
        self.fire('decrease')
        self.assertEqual(self.qty(self.p_a), 1)

    def test_st_03_add_or_increase_from_max_minus_1_moves_to_at_max(self):
        """TC-CART-ST-03: MANY (biên MAX-1) -add/increase-> AT_MAX."""
        for event in ('add', 'increase'):
            with self.subTest(event=event):
                self.set_state(QTY_MAX - 1)
                self.fire(event)
                self.assertEqual(self.qty(self.p_a), QTY_MAX)

    def test_st_04_full_path_up_then_down_to_absent(self):
        """TC-CART-ST-04: Chuỗi ABSENT -> ONE -> MANY -> ONE -> ABSENT."""
        path = [('add', 1), ('increase', 2), ('add', 3), ('decrease', 2), ('decrease', 1), ('decrease', None)]
        for event, expected_qty in path:
            with self.subTest(event=event, expected_qty=expected_qty):
                self.fire(event)
                self.assertEqual(self.qty(self.p_a), expected_qty)

    def test_st_05_path_through_at_max(self):
        """TC-CART-ST-05: Chuỗi MANY -> AT_MAX -> AT_MAX -> MANY -> AT_MAX -> ABSENT."""
        self.set_state(QTY_MAX - 1)
        path = [('increase', QTY_MAX), ('add', QTY_MAX), ('decrease', QTY_MAX - 1),
                ('add', QTY_MAX), ('remove', None)]
        for event, expected_qty in path:
            with self.subTest(event=event, expected_qty=expected_qty):
                self.fire(event)
                self.assertEqual(self.qty(self.p_a), expected_qty)

    def test_st_06_absent_is_reachable_again_after_remove(self):
        """TC-CART-ST-06: Sau khi xóa, thêm lại bắt đầu từ quantity = 1, không giữ số lượng cũ."""
        self.set_state(5)
        self.fire('remove')
        self.fire('add')
        self.assertEqual(self.qty(self.p_a), 1)

    def test_st_07_event_only_changes_target_product(self):
        """TC-CART-ST-07: Sự kiện trên SP A không làm đổi trạng thái SP B."""
        self.set_state(3, self.p_b)
        for event in EVENTS:
            with self.subTest(event=event):
                self.set_state(2)
                self.fire(event)
                self.assertEqual(self.qty(self.p_b), 3)

    def test_st_08_guest_events_do_not_change_state(self):
        """TC-CART-ST-08: Khách chưa đăng nhập: mọi sự kiện chuyển về login, giỏ của user giữ nguyên."""
        self.set_state(2)
        self.client.logout()
        for event in EVENTS:
            with self.subTest(event=event):
                response = self.fire(event)
                self.assertEqual(response.status_code, 302)
                self.assertIn('/accounts/login/', response.url)
                self.assertEqual(self.qty(self.p_a), 2)

    def test_st_16_other_user_events_do_not_change_state(self):
        """TC-CART-ST-16: User khác bấm thêm/tăng/giảm/xóa cùng SP: giỏ của user này giữ nguyên."""
        self.set_state(2)
        other = User.objects.create_user('st_other', password='User@12345')
        other_cart = Cart.objects.create(user=other)
        for event in EVENTS:
            with self.subTest(event=event):
                CartItem.objects.update_or_create(
                    cart=other_cart, product=self.p_a, defaults={'quantity': 3})
                self.client.force_login(other)
                self.fire(event)
                self.assertEqual(self.qty(self.p_a), 2)

    def test_st_09_guest_add_then_login_reaches_one(self):
        """TC-CART-ST-09: Khách bấm thêm -> đăng nhập -> quay lại URL next -> SP có quantity = 1."""
        self.client.logout()
        User.objects.create_user('st_guest', password='User@12345')
        add_url = f'/cart/add/{self.p_a.id}/'
        login_url = self.client.get(add_url).url

        response = self.client.post(login_url, {'username': 'st_guest', 'password': 'User@12345'})
        self.assertEqual(response.url, add_url)
        self.client.get(add_url)

        self.assertEqual(CartItem.objects.get(cart__user__username='st_guest', product=self.p_a).quantity, 1)

    def test_st_17_deleting_product_moves_item_to_absent(self):
        """TC-CART-ST-17: Admin xóa SP: ONE/MANY/AT_MAX -> ABSENT, trang giỏ vẫn hiển thị bình thường."""
        for state in (ONE, MANY, AT_MAX):
            with self.subTest(state=state):
                product = Product.objects.create(name=f'SP tạm {state}', price=1000)
                self.set_state(START_QTY[state], product)
                product_id = product.id
                product.delete()
                self.assertFalse(CartItem.objects.filter(cart__user=self.user, product_id=product_id).exists())
                self.assertEqual(self.client.get('/cart/').status_code, 200)


class CartLevelStateTransitionTests(CartStateTestBase):
    """Máy trạng thái của cả giỏ hàng: EMPTY <-> NOT_EMPTY."""

    def item_count(self):
        return CartItem.objects.filter(cart__user=self.user).count()

    def place_order(self, method):
        response = self.client.post('/orders/checkout/', {**CHECKOUT_DATA, 'payment_method': method})
        self.assertEqual(response.status_code, 302)
        return Order.objects.filter(user=self.user).latest('id')

    def test_st_10_removing_last_item_returns_to_empty(self):
        """TC-CART-ST-10: NOT_EMPTY (2 SP) -> vẫn NOT_EMPTY khi xóa 1 SP -> EMPTY khi xóa SP cuối."""
        self.set_state(1)
        self.set_state(1, self.p_b)
        self.fire('remove')
        self.assertContains(self.client.get('/cart/'), self.p_b.name)
        self.fire('decrease', self.p_b)
        self.assertContains(self.client.get('/cart/'), 'Giỏ hàng của bạn đang trống')

    def test_st_11_checkout_on_empty_cart_stays_empty(self):
        """TC-CART-ST-11: EMPTY -checkout-> quay về /cart/, không tạo đơn."""
        response = self.client.post('/orders/checkout/', {**CHECKOUT_DATA, 'payment_method': 'cod'})
        self.assertEqual(response.url, '/cart/')
        self.assertFalse(Order.objects.filter(user=self.user).exists())

    def test_st_12_cod_order_empties_cart(self):
        """TC-CART-ST-12: NOT_EMPTY -đặt COD-> EMPTY ngay (FR3.5, FR4.3)."""
        self.set_state(2)
        self.place_order('cod')
        self.assertEqual(self.item_count(), 0)

    def test_st_13_qr_keeps_cart_until_payment_confirmed(self):
        """TC-CART-ST-13: NOT_EMPTY -tạo đơn QR-> NOT_EMPTY -xác nhận đã thanh toán-> EMPTY."""
        self.set_state(2)
        order = self.place_order('qr')
        self.assertEqual(self.item_count(), 1)
        self.client.post(f'/orders/qr/{order.id}/confirm/')
        self.assertEqual(self.item_count(), 0)

    def test_st_14_mock_success_empties_cart(self):
        """TC-CART-ST-14: NOT_EMPTY -tạo đơn Mock-> NOT_EMPTY -thanh toán thành công-> EMPTY."""
        self.set_state(2)
        order = self.place_order('mock')
        self.assertEqual(self.item_count(), 1)
        self.client.post(f'/orders/mock/{order.id}/success/')
        self.assertEqual(self.item_count(), 0)

    def test_st_15_mock_failure_keeps_cart(self):
        """TC-CART-ST-15: NOT_EMPTY -thanh toán Mock thất bại-> vẫn NOT_EMPTY, giữ nguyên số lượng."""
        self.set_state(2)
        order = self.place_order('mock')
        self.client.post(f'/orders/mock/{order.id}/fail/')
        self.assertEqual(self.qty(self.p_a), 2)

    def test_st_18_cancel_qr_order_keeps_cart(self):
        """TC-CART-ST-18: NOT_EMPTY -hủy đơn QR-> NOT_EMPTY, đơn bị hủy, quay về /cart/."""
        self.set_state(2)
        order = self.place_order('qr')
        response = self.client.post(f'/orders/{order.id}/cancel/')
        order.refresh_from_db()
        self.assertEqual(response.url, '/cart/')
        self.assertEqual(order.status, 'cancelled')
        self.assertEqual(self.qty(self.p_a), 2)

    def test_st_19_confirm_paid_qr_again_keeps_new_cart(self):
        """TC-CART-ST-19: Xác nhận lại đơn QR đã paid: giỏ mới không bị xóa."""
        self.set_state(2)
        order = self.place_order('qr')
        self.client.post(f'/orders/qr/{order.id}/confirm/')
        self.set_state(1, self.p_b)
        self.client.post(f'/orders/qr/{order.id}/confirm/')
        self.assertEqual(self.qty(self.p_b), 1)

    def test_st_20_confirm_cancelled_qr_changes_nothing(self):
        """TC-CART-ST-20: Xác nhận đơn QR đã hủy: đơn vẫn cancelled, giỏ giữ nguyên."""
        self.set_state(2)
        order = self.place_order('qr')
        self.client.post(f'/orders/{order.id}/cancel/')
        self.client.post(f'/orders/qr/{order.id}/confirm/')
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')
        self.assertEqual(self.qty(self.p_a), 2)

    def test_st_21_qr_confirm_keeps_product_added_after_order(self):
        """TC-CART-ST-21 (BUG-CART-02): SP thêm khi đơn QR chờ thanh toán không có trong đơn, phải còn trong giỏ."""
        self.set_state(2)
        order = self.place_order('qr')
        self.fire('add', self.p_b)
        self.client.post(f'/orders/qr/{order.id}/confirm/')
        self.assertEqual(self.qty(self.p_b), 1)

    def test_st_22_mock_success_keeps_product_added_after_order(self):
        """TC-CART-ST-22 (BUG-CART-02): SP thêm khi đơn Mock chờ thanh toán không có trong đơn, phải còn trong giỏ."""
        self.set_state(2)
        order = self.place_order('mock')
        self.fire('add', self.p_b)
        self.client.post(f'/orders/mock/{order.id}/success/')
        self.assertEqual(self.qty(self.p_b), 1)
