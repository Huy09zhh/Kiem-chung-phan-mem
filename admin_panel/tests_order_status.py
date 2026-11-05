"""
Unit test chuyển đổi trạng thái đơn hàng (State Transition Testing, chương 4).

Phân hệ 6: Admin Orders & Analytics.
Hàm được kiểm thử: admin_panel.views.admin_order_update_status
                   (URL: /admin-panel/orders/<id>/status/)

Chạy:  python manage.py test admin_panel.tests_order_status -v 2

BẢNG CHUYỂN TRẠNG THÁI HỢP LỆ nằm trong biến ALLOWED bên dưới.
Nếu nhóm quyết định luồng khác, chỉ cần sửa ALLOWED; mọi test tự cập nhật.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from orders.models import Order

# Trạng thái hiện tại -> tập trạng thái được phép chuyển tới.
ALLOWED = {
    'pending': {'confirmed', 'cancelled'},
    'awaiting_transfer': {'paid', 'failed', 'cancelled'},
    'paid': {'confirmed', 'cancelled'},
    'failed': {'awaiting_transfer', 'cancelled'},
    'confirmed': {'shipping', 'cancelled'},
    'shipping': {'completed', 'cancelled'},
    'completed': set(),   # trạng thái cuối: bị khoá
    'cancelled': set(),   # trạng thái cuối: bị khoá
}
ALL_STATES = [value for value, _label in Order.STATUS_CHOICES]


class OrderStatusTransitionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user('st_admin', password='pw-12345', is_staff=True)
        cls.customer = User.objects.create_user('st_customer', password='pw-12345')

    def setUp(self):
        self.client.force_login(self.admin)

    def make_order(self, status):
        return Order.objects.create(
            user=self.customer, full_name='Khach Test', phone='0912345678',
            address='1 Duong Test', total_price=100000, status=status,
        )

    def post_status(self, order, value, **extra):
        data = {'status': value}
        data.update(extra)
        return self.client.post(reverse('admin_order_update_status', args=[order.pk]), data)

    # ---- 1. Toàn bộ 8 x 8 = 64 cặp (trạng thái hiện tại, trạng thái yêu cầu) ----
    def test_all_state_pairs_follow_transition_table(self):
        for start in ALL_STATES:
            for target in ALL_STATES:
                with self.subTest(start=start, target=target):
                    order = self.make_order(start)
                    self.post_status(order, target)
                    order.refresh_from_db()
                    expected = target if target in ALLOWED[start] else start
                    self.assertEqual(order.status, expected)

    # ---- 2. Chuỗi chuyển hợp lệ đầy đủ theo luồng xử lý đơn ----
    def test_full_valid_flow_pending_to_completed(self):
        order = self.make_order('pending')
        for step in ('confirmed', 'shipping', 'completed'):
            with self.subTest(step=step):
                self.post_status(order, step)
                order.refresh_from_db()
                self.assertEqual(order.status, step)

    def test_online_payment_flow(self):
        order = self.make_order('awaiting_transfer')
        for step in ('paid', 'confirmed', 'shipping', 'completed'):
            with self.subTest(step=step):
                self.post_status(order, step)
                order.refresh_from_db()
                self.assertEqual(order.status, step)

    # ---- 3. Trạng thái cuối bị khoá (SCRUM-19) ----
    def test_final_states_are_locked(self):
        for start in ('completed', 'cancelled'):
            for target in ALL_STATES:
                with self.subTest(start=start, target=target):
                    order = self.make_order(start)
                    self.post_status(order, target)
                    order.refresh_from_db()
                    self.assertEqual(order.status, start)

    # ---- 4. Chuyển ngược (SCRUM-44) ----
    def test_backward_transition_is_rejected(self):
        order = self.make_order('shipping')
        self.post_status(order, 'pending')
        order.refresh_from_db()
        self.assertEqual(order.status, 'shipping')

    # ---- 5. Đầu vào bất thường ----
    def test_unknown_status_value_is_rejected(self):
        order = self.make_order('confirmed')
        self.post_status(order, 'hacked_status')
        order.refresh_from_db()
        self.assertEqual(order.status, 'confirmed')

    def test_empty_status_is_rejected(self):
        order = self.make_order('confirmed')
        self.post_status(order, '')
        order.refresh_from_db()
        self.assertEqual(order.status, 'confirmed')

    def test_missing_status_field_is_rejected(self):
        order = self.make_order('confirmed')
        self.client.post(reverse('admin_order_update_status', args=[order.pk]), {})
        order.refresh_from_db()
        self.assertEqual(order.status, 'confirmed')

    def test_get_request_does_not_change_status(self):
        order = self.make_order('confirmed')
        self.client.get(reverse('admin_order_update_status', args=[order.pk]), {'status': 'shipping'})
        order.refresh_from_db()
        self.assertEqual(order.status, 'confirmed')

    def test_nonexistent_order_returns_404(self):
        response = self.client.post(reverse('admin_order_update_status', args=[999999]), {'status': 'confirmed'})
        self.assertEqual(response.status_code, 404)

    # ---- 6. Điều hướng sau khi lưu ----
    def test_redirect_to_detail_when_next_is_detail(self):
        order = self.make_order('pending')
        response = self.post_status(order, 'confirmed', next='detail')
        self.assertRedirects(response, reverse('admin_order_detail', args=[order.pk]),
                             fetch_redirect_response=False)

    def test_redirect_to_list_by_default(self):
        order = self.make_order('pending')
        response = self.post_status(order, 'confirmed')
        self.assertRedirects(response, reverse('admin_order_list'), fetch_redirect_response=False)

    # ---- 7. Phân quyền ----
    def test_customer_cannot_change_status(self):
        order = self.make_order('pending')
        self.client.force_login(self.customer)
        self.post_status(order, 'confirmed')
        order.refresh_from_db()
        self.assertEqual(order.status, 'pending')

    def test_anonymous_cannot_change_status(self):
        order = self.make_order('pending')
        self.client.logout()
        response = self.post_status(order, 'confirmed')
        order.refresh_from_db()
        self.assertEqual(order.status, 'pending')
        self.assertEqual(response.status_code, 302)
