"""
Unit test chuyển đổi trạng thái đơn hàng (State Transition Testing, chương 4).

Phân hệ 6: Admin Orders & Analytics.
Hàm được kiểm thử: admin_panel.views.admin_order_update_status
                   (URL: /admin-panel/orders/<id>/status/)

Chạy:  python manage.py test admin_panel.tests_order_status -v 2

BẢNG CHUYỂN TRẠNG THÁI nằm trong biến ALLOWED bên dưới (khớp Order.ALLOWED_TRANSITIONS).
Nếu nhóm đổi luồng, chỉ cần sửa ALLOWED; mọi test tự cập nhật.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from orders.models import Order

# Bảng chuyển trạng thái của code (Order.ALLOWED_TRANSITIONS trong orders/models.py).
# Trạng thái hiện tại -> tập trạng thái được phép chuyển tới.
ALLOWED = {
    'pending': {'paid', 'confirmed', 'cancelled'},
    'awaiting_transfer': {'paid', 'failed', 'cancelled'},
    'paid': {'confirmed', 'cancelled'},
    'failed': {'awaiting_transfer', 'cancelled'},
    'confirmed': {'shipping', 'cancelled'},
    'shipping': {'completed', 'cancelled'},
    'completed': set(),           # trạng thái cuối: bị khoá
    'cancelled': set(),           # trạng thái cuối: bị khoá
}
# Chuyển trạng thái cho hai trạng thái thanh toán chưa hoàn tất (SCRUM-44: từng bị thiếu trong code).
EXPECTED_PAYMENT_FLOW = {
    'awaiting_transfer': {'paid', 'failed', 'cancelled'},
    'failed': {'awaiting_transfer', 'cancelled'},
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

    def post_status(self, order, value, follow=False, **extra):
        data = {'status': value}
        data.update(extra)
        return self.client.post(reverse('admin_order_update_status', args=[order.pk]), data, follow=follow)

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

    def test_payment_flow_pending_to_completed(self):
        order = self.make_order('pending')
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

    # ---- 8. Đơn "Chờ chuyển khoản" và "Thanh toán thất bại" phải xử lý được ----
    # Hồi quy cho lỗi bảng ALLOWED_TRANSITIONS từng thiếu hai trạng thái này,
    # khiến admin không xác nhận thanh toán hay hủy được đơn chuyển khoản.
    def test_awaiting_transfer_and_failed_orders_can_be_processed(self):
        for start, targets in EXPECTED_PAYMENT_FLOW.items():
            for target in targets:
                with self.subTest(start=start, target=target):
                    order = self.make_order(start)
                    self.post_status(order, target)
                    order.refresh_from_db()
                    self.assertEqual(order.status, target)

    # ---- 9. SCRUM-51: Kiểm tra giao diện và thông báo lỗi khi chuyển trạng thái ----
    def test_scrum51_pending_order_detail_only_shows_allowed_statuses(self):
        """
        Với đơn hàng 'Chờ xử lý' (pending), trang chi tiết chỉ hiển thị đúng 3 trạng thái hợp lệ:
        - Đã thanh toán (paid)
        - Đã xác nhận (confirmed)
        - Đã hủy (cancelled)
        Không hiển thị các trạng thái không được phép:
        - Chờ chuyển khoản (awaiting_transfer)
        - Thanh toán thất bại (failed)
        - Đang giao (shipping)
        - Hoàn thành (completed)
        Đồng thời KHÔNG được hiển thị 'Không có trạng thái chuyển tiếp'.
        """
        order = self.make_order('pending')
        response = self.client.get(reverse('admin_order_detail', args=[order.pk]))
        self.assertEqual(response.status_code, 200)

        # Kiểm tra biến context
        self.assertIn('allowed_status_choices', response.context)
        allowed_keys = [val for val, _ in response.context['allowed_status_choices']]
        self.assertEqual(set(allowed_keys), {'paid', 'confirmed', 'cancelled'})

        # Trạng thái được phép chuyển tiếp trong select HTML
        self.assertContains(response, 'value="paid"')
        self.assertContains(response, 'value="confirmed"')
        self.assertContains(response, 'value="cancelled"')

        # Trạng thái không được phép chuyển tiếp trực tiếp từ pending
        self.assertNotContains(response, 'value="shipping"')
        self.assertNotContains(response, 'value="completed"')
        self.assertNotContains(response, 'value="awaiting_transfer"')
        self.assertNotContains(response, 'value="failed"')

        # Không được báo lỗi rỗng trạng thái
        self.assertNotContains(response, 'Không có trạng thái chuyển tiếp')
        self.assertNotContains(response, 'Không có trạng thái chuyển đổi hợp lệ khả dụng')

    def test_scrum51_orders_list_dropdown_only_shows_allowed_statuses(self):
        """Bảng danh sách đơn hàng cũng chỉ hiển thị các trạng thái chuyển tiếp hợp lệ."""
        order = self.make_order('pending')
        response = self.client.get(reverse('admin_order_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="paid"')
        self.assertContains(response, 'value="confirmed"')
        self.assertContains(response, 'value="cancelled"')

    def test_scrum51_final_order_detail_disables_status_update(self):
        """Đơn hàng đã hoàn thành hoặc đã hủy bị khóa và hiển thị thông báo trạng thái cuối."""
        for final_status in ('completed', 'cancelled'):
            with self.subTest(status=final_status):
                order = self.make_order(final_status)
                response = self.client.get(reverse('admin_order_detail', args=[order.pk]))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'disabled')
                self.assertContains(response, 'Đơn đã ở trạng thái cuối, không thể thay đổi.')

    def test_scrum51_pending_order_valid_transitions_succeed_with_success_message(self):
        """Kiểm thử Chờ xử lý -> Đã thanh toán, Đã xác nhận, Đã hủy thành công và có thông báo."""
        valid_targets = ['paid', 'confirmed', 'cancelled']
        for target in valid_targets:
            with self.subTest(target=target):
                order = self.make_order('pending')
                response = self.post_status(order, target, next='detail', follow=True)
                order.refresh_from_db()
                self.assertEqual(order.status, target)
                # Kiểm tra thông báo thành công
                self.assertContains(response, 'Đã cập nhật trạng thái đơn hàng')

    def test_scrum51_pending_order_invalid_transitions_rejected_with_error_message(self):
        """
        Kiểm thử Chờ xử lý -> Đang giao, Hoàn thành:
        Backend phải từ chối, DB không đổi và có thông báo lỗi 'Trạng thái chuyển đổi không hợp lệ.'.
        """
        invalid_targets = ['shipping', 'completed', 'awaiting_transfer', 'failed', 'hacked_status']
        for target in invalid_targets:
            with self.subTest(target=target):
                order = self.make_order('pending')
                response = self.post_status(order, target, next='detail', follow=True)
                order.refresh_from_db()
                # Database không được thay đổi
                self.assertEqual(order.status, 'pending')
                # Admin nhận được thông báo lỗi rõ ràng
                self.assertContains(response, 'Trạng thái chuyển đổi không hợp lệ.')