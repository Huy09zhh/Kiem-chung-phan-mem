"""Kiểm thử hộp đen FR4 - Đặt hàng & Thanh toán đa kênh (UC04): EP & BVA.

Mỗi test ứng với 1 test case trong docs/TestCase_FR4_Orders_EP_BVA.md
(mã TC-ORD-xx nằm ở docstring dòng đầu của mỗi test).

Chạy toàn bộ : python manage.py test orders -v 2
Chạy 1 test  : python manage.py test orders.tests.CheckoutFormTests.test_ord_12_name_empty -v 2
"""
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.test import Client, TestCase

from cart.models import Cart, CartItem
from products.models import Product
from .models import ORDER_TOTAL_MAX, Order, OrderItem

# Giới hạn tổng tiền checkout chấp nhận: ORDER_TOTAL_MAX = 2.147.483.647 VND (max int 32-bit)
TOTAL_MAX = ORDER_TOTAL_MAX
TOTAL_MAX_PLUS = ORDER_TOTAL_MAX + 1


class OrderTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('orduser', 'ord@test.com', 'User@12345')
        cls.other = User.objects.create_user('ordother', 'other@test.com', 'User@12345')
        cls.p_a = Product.objects.create(name='Bình nước tre', price=Decimal('50000'))
        cls.p_b = Product.objects.create(name='Túi vải canvas', price=Decimal('30000'))

    def setUp(self):
        # Không ném exception ra test để đo được mã HTTP 500 thật
        self.client = Client(raise_request_exception=False)

    # ---------- tiện ích ----------
    def login(self, user=None):
        self.client.force_login(user or self.user)

    def fill_cart(self, *pairs, user=None):
        """fill_cart((p_a, 2), (p_b, 1)) -> giỏ của user có A x2, B x1."""
        cart, _ = Cart.objects.get_or_create(user=user or self.user)
        cart.items.all().delete()
        for product, qty in pairs:
            CartItem.objects.create(cart=cart, product=product, quantity=qty)
        return cart

    def data(self, **over):
        d = {
            'full_name': 'Trần Đình Đức',
            'phone': '0901234567',
            'address': '12 Nguyễn Huệ, Quận 1, TP.HCM',
            'note': 'Giao giờ hành chính',
            'payment_method': 'cod',
        }
        d.update(over)
        return d

    def checkout(self, **over):
        return self.client.post('/orders/checkout/', self.data(**over))

    def mk_order(self, method='cod', status='pending', user=None, price='50000', qty=1):
        o = Order.objects.create(
            user=user or self.user, full_name='Nguyễn Văn A', phone='0900000000',
            address='1 Lê Lợi', payment_method=method, status=status,
            total_price=Decimal(price) * qty,
        )
        OrderItem.objects.create(order=o, product_name='Bình nước tre', price=Decimal(price), quantity=qty)
        return o

    def status_of(self, order):
        return Order.objects.get(pk=order.pk).status

    def cart_count(self):
        return CartItem.objects.filter(cart__user=self.user).count()


# =====================================================================
# A. Truy cập & tiền điều kiện
# =====================================================================
class AccessPreconditionTests(OrderTestBase):

    def test_ord_01_guest_get_checkout_redirects_login(self):
        """TC-ORD-01: Khách chưa đăng nhập GET /orders/checkout/ -> chuyển login."""
        r = self.client.get('/orders/checkout/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/accounts/login/', r.url)

    def test_ord_02_guest_post_checkout_redirects_login_no_order(self):
        """TC-ORD-02: Khách chưa đăng nhập POST checkout -> chuyển login, không tạo đơn."""
        r = self.client.post('/orders/checkout/', self.data())
        self.assertEqual(r.status_code, 302)
        self.assertIn('/accounts/login/', r.url)
        self.assertEqual(Order.objects.count(), 0)

    def test_ord_03_no_cart_row_redirects_cart(self):
        """TC-ORD-03: User chưa từng có Cart -> GET checkout chuyển về /cart/."""
        self.login()
        r = self.client.get('/orders/checkout/')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, '/cart/')

    def test_ord_04_empty_cart_get_redirects_cart(self):
        """TC-ORD-04: Giỏ rỗng -> GET checkout chuyển về /cart/."""
        self.login()
        Cart.objects.create(user=self.user)
        r = self.client.get('/orders/checkout/')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, '/cart/')

    def test_ord_05_empty_cart_post_creates_no_order(self):
        """TC-ORD-05: Giỏ rỗng -> POST checkout chuyển /cart/, không tạo đơn."""
        self.login()
        Cart.objects.create(user=self.user)
        r = self.checkout()
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, '/cart/')
        self.assertEqual(Order.objects.count(), 0)

    def test_ord_06_get_checkout_shows_items_total_and_3_methods(self):
        """TC-ORD-06: GET checkout có hàng -> 200, hiện SP, tổng tiền, đủ 3 phương thức."""
        self.login()
        self.fill_cart((self.p_a, 2), (self.p_b, 1))  # 2*50000 + 30000 = 130000
        r = self.client.get('/orders/checkout/')
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn('Bình nước tre', html)
        self.assertIn('Túi vải canvas', html)
        self.assertTrue('130,000' in html or '130.000' in html or '130000' in html)
        for m in ('cod', 'qr', 'mock'):
            self.assertIn(f'value="{m}"', html)


# =====================================================================
# B + C. FR4.1 Thông tin giao nhận (EP/BVA) & FR4.2 chọn phương thức
# =====================================================================
class CheckoutFormTests(OrderTestBase):

    def setUp(self):
        super().setUp()
        self.login()
        self.fill_cart((self.p_a, 1))

    def assert_rejected(self, r):
        """Form không hợp lệ: không tạo đơn, không chuyển sang trang thanh toán."""
        self.assertEqual(Order.objects.count(), 0, 'Không được tạo đơn khi dữ liệu không hợp lệ')
        self.assertEqual(OrderItem.objects.count(), 0)
        self.assertEqual(r.status_code, 200, 'Phải hiển thị lại form kèm cảnh báo')
        self.assertEqual(self.cart_count(), 1, 'Giỏ hàng phải được giữ nguyên')

    # ----- Hợp lệ -----
    def test_ord_07_all_at_min(self):
        """TC-ORD-07: BVA min - Họ tên 1, SĐT 1, Địa chỉ 1 ký tự, note rỗng -> tạo đơn."""
        r = self.checkout(full_name='A', phone='0', address='B', note='')
        self.assertEqual(r.status_code, 302)
        o = Order.objects.get()
        self.assertEqual((o.full_name, o.phone, o.address), ('A', '0', 'B'))

    def test_ord_08_all_at_min_plus(self):
        """TC-ORD-08: BVA min+ - Họ tên 2, SĐT 2, Địa chỉ 2 ký tự -> tạo đơn."""
        r = self.checkout(full_name='An', phone='09', address='Bx')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Order.objects.count(), 1)

    def test_ord_09_nominal_saved_exactly_including_note(self):
        """TC-ORD-09: Nominal - lưu chính xác Họ tên, SĐT, Địa chỉ, Ghi chú."""
        r = self.checkout()
        self.assertEqual(r.status_code, 302)
        o = Order.objects.get()
        self.assertEqual(o.full_name, 'Trần Đình Đức')
        self.assertEqual(o.phone, '0901234567')
        self.assertEqual(o.address, '12 Nguyễn Huệ, Quận 1, TP.HCM')
        self.assertEqual(o.note, 'Giao giờ hành chính')

    def test_ord_10_max_minus(self):
        """TC-ORD-10: BVA max- - Họ tên 254, SĐT 19 ký tự -> tạo đơn."""
        r = self.checkout(full_name='a' * 254, phone='9' * 19)
        self.assertEqual(r.status_code, 302)
        o = Order.objects.get()
        self.assertEqual((len(o.full_name), len(o.phone)), (254, 19))

    def test_ord_11_max(self):
        """TC-ORD-11: BVA max - Họ tên 255, SĐT 20 ký tự -> tạo đơn."""
        r = self.checkout(full_name='a' * 255, phone='9' * 20)
        self.assertEqual(r.status_code, 302)
        o = Order.objects.get()
        self.assertEqual((len(o.full_name), len(o.phone)), (255, 20))

    # ----- Không hợp lệ (min-, max+) -----
    def test_ord_12_name_empty(self):
        """TC-ORD-12: BVA min- - Họ tên rỗng -> chặn (A1)."""
        self.assert_rejected(self.checkout(full_name=''))

    def test_ord_13_name_whitespace_only(self):
        """TC-ORD-13: Họ tên chỉ toàn khoảng trắng -> chặn."""
        self.assert_rejected(self.checkout(full_name='     '))

    def test_ord_14_phone_empty(self):
        """TC-ORD-14: BVA min- - SĐT rỗng -> chặn (A1)."""
        self.assert_rejected(self.checkout(phone=''))

    def test_ord_15_address_empty(self):
        """TC-ORD-15: BVA min- - Địa chỉ rỗng -> chặn (A1)."""
        self.assert_rejected(self.checkout(address=''))

    def test_ord_16_all_required_empty(self):
        """TC-ORD-16: Bỏ trống cả 3 trường bắt buộc -> chặn."""
        self.assert_rejected(self.checkout(full_name='', phone='', address=''))

    def test_ord_17_name_256_chars(self):
        """TC-ORD-17: BVA max+ - Họ tên 256 ký tự (vượt max_length=255) -> chặn."""
        self.assert_rejected(self.checkout(full_name='a' * 256))

    def test_ord_18_phone_21_chars(self):
        """TC-ORD-18: BVA max+ - SĐT 21 ký tự (vượt max_length=20) -> chặn."""
        self.assert_rejected(self.checkout(phone='9' * 21))

    # ----- Ghi chú (tùy chọn) & chuẩn hóa -----
    def test_ord_19_note_field_omitted(self):
        """TC-ORD-19: Không gửi trường note (tùy chọn) -> vẫn tạo đơn, note rỗng."""
        d = self.data()
        del d['note']
        r = self.client.post('/orders/checkout/', d)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Order.objects.get().note or '', '')

    def test_ord_20_input_is_trimmed(self):
        """TC-ORD-20: Khoảng trắng đầu/cuối được cắt khi lưu."""
        self.checkout(full_name='  Đức  ', phone=' 0901234567 ', address='  HCM  ')
        o = Order.objects.get()
        self.assertEqual((o.full_name, o.phone, o.address), ('Đức', '0901234567', 'HCM'))

    # ----- FR4.2 phương thức thanh toán -----
    def test_ord_21_payment_method_omitted_defaults_to_cod(self):
        """TC-ORD-21: Không gửi payment_method -> mặc định COD (pending)."""
        d = self.data()
        del d['payment_method']
        r = self.client.post('/orders/checkout/', d)
        self.assertEqual(r.status_code, 302)
        o = Order.objects.get()
        self.assertEqual((o.payment_method, o.status), ('cod', 'pending'))

    def test_ord_22_invalid_payment_method_rejected(self):
        """TC-ORD-22: payment_method không thuộc {cod, qr, mock} -> chặn, không âm thầm đổi sang COD."""
        for bad in ('bitcoin', 'COD', ''):
            with self.subTest(payment_method=bad):
                Order.objects.all().delete()
                self.fill_cart((self.p_a, 1))  # nạp lại giỏ: lần thử trước có thể đã làm rỗng giỏ
                r = self.checkout(payment_method=bad)
                self.assertEqual(Order.objects.count(), 0, f'Không được tạo đơn với payment_method={bad!r}')
                self.assertNotEqual(r.status_code, 500)


# =====================================================================
# D. FR4.3 COD
# =====================================================================
class CodFlowTests(OrderTestBase):

    def setUp(self):
        super().setUp()
        self.login()

    def test_ord_23_cod_creates_pending_order_and_redirects_success(self):
        """TC-ORD-23: COD -> Order pending, đúng user/phương thức/tổng tiền, chuyển /orders/success/<id>/."""
        self.fill_cart((self.p_a, 2))  # 100000
        r = self.checkout(payment_method='cod')
        o = Order.objects.get()
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, f'/orders/success/{o.id}/')
        self.assertEqual((o.status, o.payment_method, o.user), ('pending', 'cod', self.user))
        self.assertEqual(o.total_price, Decimal('100000'))

    def test_ord_24_cod_copies_cart_to_order_items(self):
        """TC-ORD-24: COD -> sao chép từng CartItem sang OrderItem (tên, giá, số lượng)."""
        self.fill_cart((self.p_a, 2), (self.p_b, 3))
        self.checkout()
        o = Order.objects.get()
        items = {i.product_name: (i.price, i.quantity) for i in o.items.all()}
        self.assertEqual(items, {
            'Bình nước tre': (Decimal('50000'), 2),
            'Túi vải canvas': (Decimal('30000'), 3),
        })

    def test_ord_25_cod_empties_cart(self):
        """TC-ORD-25 (BR04.2): COD -> giỏ hàng rỗng sau khi đặt."""
        self.fill_cart((self.p_a, 1), (self.p_b, 1))
        self.checkout()
        self.assertEqual(self.cart_count(), 0)

    def test_ord_26_order_item_is_snapshot(self):
        """TC-ORD-26 (BR04.1): Đổi giá/tên SP sau khi đặt -> OrderItem không đổi."""
        self.fill_cart((self.p_a, 1))
        self.checkout()
        Product.objects.filter(pk=self.p_a.pk).update(price=Decimal('99000'), name='Tên mới')
        i = OrderItem.objects.get()
        self.assertEqual((i.product_name, i.price), ('Bình nước tre', Decimal('50000')))

    def test_ord_27_total_is_sum_price_times_quantity(self):
        """TC-ORD-27: Tổng tiền = Σ(giá × số lượng) = 2A + B."""
        self.fill_cart((self.p_a, 2), (self.p_b, 1))
        self.checkout()
        self.assertEqual(Order.objects.get().total_price, Decimal('130000'))

    def test_ord_28_second_submit_does_not_duplicate_order(self):
        """TC-ORD-28: Gửi lại form lần 2 sau khi đặt xong -> không tạo thêm đơn (giỏ đã rỗng)."""
        self.fill_cart((self.p_a, 1))
        self.checkout()
        r = self.checkout()
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, '/cart/')


# =====================================================================
# E. FR4.4 VietQR
# =====================================================================
class QrFlowTests(OrderTestBase):

    def setUp(self):
        super().setUp()
        self.login()

    def test_ord_29_qr_creates_awaiting_transfer_and_redirects_qr_page(self):
        """TC-ORD-29: QR -> Order awaiting_transfer, giữ giỏ hàng, chuyển /orders/qr/<id>/."""
        self.fill_cart((self.p_a, 1))
        r = self.checkout(payment_method='qr')
        o = Order.objects.get()
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, f'/orders/qr/{o.id}/')
        self.assertEqual((o.status, o.payment_method), ('awaiting_transfer', 'qr'))
        self.assertEqual(self.cart_count(), 1)

    def test_ord_30_qr_page_has_correct_qr_url_amount_and_note(self):
        """TC-ORD-30: Trang QR -> ảnh VietQR đúng STK, số tiền, nội dung THANH TOAN DH{id}."""
        o = self.mk_order(method='qr', status='awaiting_transfer', price='150000')
        r = self.client.get(f'/orders/qr/{o.id}/')
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn('https://img.vietqr.io/image/', html)
        self.assertIn('0382771491', html)                        # STK cấu hình trong settings
        self.assertIn('amount=150000', html)
        self.assertIn(f'addInfo=THANH%20TOAN%20DH{o.id}', html)
        self.assertIn(f'THANH TOAN DH{o.id}', html)              # nội dung hiển thị cho khách copy
        self.assertIn(f'/orders/qr/{o.id}/confirm/', html)       # nút "Tôi đã chuyển khoản"

    def test_ord_31_confirm_post_sets_paid(self):
        """TC-ORD-31: POST confirm -> paid, chuyển trang success."""
        o = self.mk_order(method='qr', status='awaiting_transfer')
        r = self.client.post(f'/orders/qr/{o.id}/confirm/')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, f'/orders/success/{o.id}/')
        self.assertEqual(self.status_of(o), 'paid')

    def test_ord_32_confirm_get_does_not_change_status(self):
        """TC-ORD-32: GET confirm -> không đổi trạng thái."""
        o = self.mk_order(method='qr', status='awaiting_transfer')
        self.client.get(f'/orders/qr/{o.id}/confirm/')
        self.assertEqual(self.status_of(o), 'awaiting_transfer')

    def test_ord_33_confirm_without_csrf_token_is_forbidden(self):
        """TC-ORD-33 (NFR2): POST confirm không có CSRF token -> 403, trạng thái không đổi."""
        o = self.mk_order(method='qr', status='awaiting_transfer')
        c = Client(enforce_csrf_checks=True, raise_request_exception=False)
        c.force_login(self.user)
        r = c.post(f'/orders/qr/{o.id}/confirm/')
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.status_of(o), 'awaiting_transfer')

    def test_ord_34_confirm_on_non_qr_order_is_ignored(self):
        """TC-ORD-34: Confirm trên đơn COD/Mock (không phải QR) -> không được chuyển sang paid."""
        for method in ('cod', 'mock'):
            with self.subTest(method=method):
                o = self.mk_order(method=method, status='pending')
                self.client.post(f'/orders/qr/{o.id}/confirm/')
                self.assertEqual(self.status_of(o), 'pending')

    def test_ord_35_confirm_on_final_or_failed_order_is_ignored(self):
        """TC-ORD-35: Confirm trên đơn đã completed/cancelled/failed -> trạng thái giữ nguyên."""
        for st in ('completed', 'cancelled', 'failed'):
            with self.subTest(status=st):
                o = self.mk_order(method='qr', status=st)
                self.client.post(f'/orders/qr/{o.id}/confirm/')
                self.assertEqual(self.status_of(o), st)


# =====================================================================
# F. FR4.5 Mock online
# =====================================================================
class MockFlowTests(OrderTestBase):

    def setUp(self):
        super().setUp()
        self.login()

    def test_ord_36_mock_creates_pending_and_redirects_sandbox(self):
        """TC-ORD-36: Mock -> Order pending, chuyển /orders/mock/<id>/, giỏ chưa xóa."""
        self.fill_cart((self.p_a, 1))
        r = self.checkout(payment_method='mock')
        o = Order.objects.get()
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, f'/orders/mock/{o.id}/')
        self.assertEqual((o.status, o.payment_method), ('pending', 'mock'))
        self.assertEqual(self.cart_count(), 1)

    def test_ord_37_mock_sandbox_page_renders_with_two_buttons(self):
        """TC-ORD-37: Trang Sandbox -> 200, có nút Thành công & Thất bại trỏ đúng URL."""
        o = self.mk_order(method='mock', status='pending')
        r = self.client.get(f'/orders/mock/{o.id}/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, f'/orders/mock/{o.id}/success/')
        self.assertContains(r, f'/orders/mock/{o.id}/fail/')

    def test_ord_38_mock_success_sets_paid_and_empties_cart(self):
        """TC-ORD-38: Mock thành công -> paid, giỏ rỗng, chuyển success."""
        self.fill_cart((self.p_a, 1))
        self.checkout(payment_method='mock')
        o = Order.objects.get()
        r = self.client.post(f'/orders/mock/{o.id}/success/')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, f'/orders/success/{o.id}/')
        self.assertEqual(self.status_of(o), 'paid')
        self.assertEqual(self.cart_count(), 0)

    def test_ord_39_mock_fail_sets_failed_and_keeps_cart(self):
        """TC-ORD-39: Mock thất bại -> failed, giỏ giữ nguyên."""
        self.fill_cart((self.p_a, 1))
        self.checkout(payment_method='mock')
        o = Order.objects.get()
        self.client.post(f'/orders/mock/{o.id}/fail/')
        self.assertEqual(self.status_of(o), 'failed')
        self.assertEqual(self.cart_count(), 1)

    def test_ord_40_failed_payment_page_does_not_say_success(self):
        """TC-ORD-40 (A2): Sau khi thất bại, trang kết quả báo giao dịch chưa hoàn tất, KHÔNG báo 'Đặt hàng thành công'."""
        o = self.mk_order(method='mock', status='pending')
        r = self.client.post(f'/orders/mock/{o.id}/fail/', follow=True)
        html = r.content.decode()
        self.assertNotIn('Đặt hàng thành công', html)
        self.assertIn('thất bại', html.lower())

    def test_ord_41_mock_success_on_cod_order_is_ignored(self):
        """TC-ORD-41: Gọi mock success trên đơn COD -> không đổi trạng thái, không xóa giỏ hiện tại."""
        o = self.mk_order(method='cod', status='pending')
        self.fill_cart((self.p_b, 1))
        self.client.post(f'/orders/mock/{o.id}/success/')
        self.assertEqual(self.status_of(o), 'pending')
        self.assertEqual(self.cart_count(), 1)

    def test_ord_42_mock_fail_cannot_downgrade_paid_order(self):
        """TC-ORD-42: Gọi mock fail trên đơn đã paid -> vẫn paid."""
        o = self.mk_order(method='mock', status='paid')
        self.client.post(f'/orders/mock/{o.id}/fail/')
        self.assertEqual(self.status_of(o), 'paid')

    def test_ord_43_get_request_must_not_change_order_state(self):
        """TC-ORD-43 (NFR2): GET /mock/<id>/success|fail/ không được thay đổi trạng thái (chỉ nhận POST)."""
        for action in ('success', 'fail'):
            with self.subTest(action=action):
                o = self.mk_order(method='mock', status='pending')
                self.client.get(f'/orders/mock/{o.id}/{action}/')
                self.assertEqual(self.status_of(o), 'pending')


# =====================================================================
# G. FR4.6 Trang xác nhận đơn hàng
# =====================================================================
class ConfirmationPageTests(OrderTestBase):

    def test_ord_44_success_page_shows_full_order_info(self):
        """TC-ORD-44 (FR4.6): Trang xác nhận hiển thị mã đơn, người nhận, phương thức, trạng thái, danh sách món, tổng tiền."""
        self.login()
        self.fill_cart((self.p_a, 2), (self.p_b, 1))
        r = self.checkout(payment_method='cod')
        o = Order.objects.get()
        r = self.client.get(r.url)
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn(str(o.id), html)
        for text in ('Trần Đình Đức', '0901234567', '12 Nguyễn Huệ', 'Thanh toán khi nhận hàng',
                     'Chờ xử lý', 'Bình nước tre', 'Túi vải canvas'):
            self.assertIn(text, html, f'Thiếu "{text}" trên trang xác nhận')
        self.assertTrue('130,000' in html or '130.000' in html or '130000' in html, 'Thiếu tổng tiền')


# =====================================================================
# H. Phân quyền theo chủ đơn & định danh đơn hàng
# =====================================================================
class OwnershipAndIdTests(OrderTestBase):

    def test_ord_45_other_users_order_returns_404_and_is_untouched(self):
        """TC-ORD-45 (IDOR): User khác truy cập đơn của người khác -> 404, trạng thái không đổi."""
        o = self.mk_order(method='qr', status='awaiting_transfer', user=self.user)
        self.login(self.other)
        for url in (f'/orders/success/{o.id}/', f'/orders/qr/{o.id}/', f'/orders/mock/{o.id}/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)
        for url in (f'/orders/qr/{o.id}/confirm/', f'/orders/mock/{o.id}/success/', f'/orders/mock/{o.id}/fail/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url).status_code, 404)
        self.assertEqual(self.status_of(o), 'awaiting_transfer')

    def test_ord_46_nonexistent_order_returns_404(self):
        """TC-ORD-46: Mã đơn không tồn tại -> 404 ở mọi endpoint."""
        self.login()
        for url in ('/orders/success/999999/', '/orders/qr/999999/', '/orders/mock/999999/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)
        for url in ('/orders/qr/999999/confirm/', '/orders/mock/999999/success/', '/orders/mock/999999/fail/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url).status_code, 404)

    def test_ord_47_guest_on_order_endpoints_redirects_login(self):
        """TC-ORD-47: Khách chưa đăng nhập vào endpoint đơn hàng -> chuyển login, trạng thái không đổi."""
        o = self.mk_order(method='qr', status='awaiting_transfer')
        for url in (f'/orders/success/{o.id}/', f'/orders/qr/{o.id}/', f'/orders/mock/{o.id}/'):
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertEqual(r.status_code, 302)
                self.assertIn('/accounts/login/', r.url)
        for url in (f'/orders/qr/{o.id}/confirm/', f'/orders/mock/{o.id}/success/', f'/orders/mock/{o.id}/fail/'):
            with self.subTest(url=url):
                r = self.client.post(url)
                self.assertEqual(r.status_code, 302)
                self.assertIn('/accounts/login/', r.url)
        self.assertEqual(self.status_of(o), 'awaiting_transfer')

    def test_ord_48_non_integer_or_negative_id_returns_404(self):
        """TC-ORD-48: Mã đơn 'abc' hoặc '-1' -> 404."""
        self.login()
        for bad in ('abc', '-1', '0x1'):
            with self.subTest(order_id=bad):
                self.assertEqual(self.client.get(f'/orders/success/{bad}/').status_code, 404)


# =====================================================================
# I. Biên tổng tiền & độ tin cậy (NFR3)
# =====================================================================
class TotalBoundaryAndReliabilityTests(OrderTestBase):

    def setUp(self):
        super().setUp()
        self.login()

    def one_product_cart(self, price, qty=1):
        p = Product.objects.create(name='SP kiểm thử biên', price=price)
        self.fill_cart((p, qty))

    def test_ord_49_total_at_min_1(self):
        """TC-ORD-49: BVA min - tổng tiền 1 VND -> tạo đơn."""
        self.one_product_cart(Decimal('1'))
        r = self.checkout()
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Order.objects.get().total_price, Decimal('1'))

    def test_ord_50_total_at_max(self):
        """TC-ORD-50: BVA max - tổng tiền 2.147.483.647 VND -> tạo đơn."""
        self.one_product_cart(TOTAL_MAX)
        r = self.checkout()
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Order.objects.get().total_price, TOTAL_MAX)

    def test_ord_51_total_above_max_is_handled_gracefully(self):
        """TC-ORD-51: BVA max+ - tổng tiền 2.147.483.648 VND vượt ORDER_TOTAL_MAX -> không lỗi 500 và KHÔNG lưu đơn."""
        self.one_product_cart(TOTAL_MAX_PLUS)
        r = self.checkout()
        self.assertNotEqual(r.status_code, 500, 'Server không được trả lỗi 500')
        self.assertEqual(Order.objects.count(), 0, 'Đơn có tổng vượt max_digits của cột vẫn bị lưu')
        self.assertEqual(OrderItem.objects.count(), 0)

    def test_ord_53_total_above_max_shows_warning_and_keeps_cart(self):
        """TC-ORD-53: BVA max+ - tổng 2.147.483.648 VND -> hiển thị lại form kèm cảnh báo, giữ nguyên giỏ."""
        self.one_product_cart(TOTAL_MAX_PLUS)
        r = self.checkout()
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'vượt quá giới hạn')
        self.assertEqual(self.cart_count(), 1)

    def test_ord_54_order_pages_open_with_total_over_100_million(self):
        """TC-ORD-54: Đơn có tổng >= 100.000.000 VND (vượt cột cũ max_digits=10) -> trang đơn của khách và admin vẫn mở được (không lỗi 500)."""
        order = self.mk_order(price='60000000', qty=2)
        staff = User.objects.create_user('ordstaff', 'staff@test.com', 'User@12345', is_staff=True)
        self.assertEqual(Order.objects.get(pk=order.pk).total_price, Decimal('120000000'))
        self.assertEqual(self.client.get('/orders/my/').status_code, 200)
        self.client.force_login(staff)
        for url in ('/admin-panel/orders/', f'/admin-panel/orders/{order.pk}/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_ord_52_atomic_order_creation(self):
        """TC-ORD-52 (NFR3 - ACID): Lỗi khi tạo OrderItem -> rollback, không còn Order mồ côi, giỏ giữ nguyên."""
        self.fill_cart((self.p_a, 1))
        with mock.patch.object(OrderItem, 'save', side_effect=RuntimeError('boom')):
            self.checkout()
        self.assertEqual(Order.objects.count(), 0, 'Order mồ côi (không có OrderItem) vẫn bị lưu')
        self.assertEqual(self.cart_count(), 1)


# =====================================================================
# J. Kiểm thử Chuyển đổi trạng thái (State Transition Testing)
# =====================================================================
class StateTransitionTests(OrderTestBase):
    """Bộ kiểm thử Chuyển đổi trạng thái (State Transition Testing) cho Order & Payment.
    Bao phủ toàn bộ 16 chuyển đổi hợp lệ và 22 kịch bản chặn chuyển đổi bất hợp lệ
    theo thiết kế trong docs/TestCase_FR4_Orders_StateTransition_DecisionTable.md.
    """

    def setUp(self):
        super().setUp()
        self.login()

    # -------------------------------------------------------------
    # J.1 Các luồng chuyển trạng thái hợp lệ (Valid Transitions: TC-ST-01 -> TC-ST-16)
    # -------------------------------------------------------------
    def test_st_01_pending_to_paid(self):
        """TC-ST-01: pending -> paid (Admin xác nhận thanh toán trực tiếp)."""
        o = self.mk_order(status='pending')
        self.assertTrue(o.can_change_to('paid'))
        o.status = 'paid'
        o.save()
        self.assertEqual(self.status_of(o), 'paid')

    def test_st_02_pending_to_confirmed(self):
        """TC-ST-02: pending -> confirmed (Admin xác nhận đơn hàng COD)."""
        o = self.mk_order(status='pending')
        self.assertTrue(o.can_change_to('confirmed'))
        o.status = 'confirmed'
        o.save()
        self.assertEqual(self.status_of(o), 'confirmed')

    def test_st_03_pending_to_cancelled(self):
        """TC-ST-03: pending -> cancelled (Khách/Admin hủy đơn hàng)."""
        o = self.mk_order(status='pending')
        self.assertTrue(o.can_change_to('cancelled'))
        o.status = 'cancelled'
        o.save()
        self.assertEqual(self.status_of(o), 'cancelled')

    def test_st_04_pending_to_paid_via_mock(self):
        """TC-ST-04: pending -> paid (Mock Payment callback thành công qua endpoint)."""
        self.fill_cart((self.p_a, 1))
        self.checkout(payment_method='mock')
        o = Order.objects.get()
        self.assertEqual(o.status, 'pending')
        r = self.client.post(f'/orders/mock/{o.id}/success/')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.status_of(o), 'paid')
        self.assertEqual(self.cart_count(), 0)

    def test_st_05_pending_to_failed_via_mock(self):
        """TC-ST-05: pending -> failed (Mock Payment callback thất bại qua endpoint)."""
        self.fill_cart((self.p_a, 1))
        self.checkout(payment_method='mock')
        o = Order.objects.get()
        self.assertEqual(o.status, 'pending')
        r = self.client.post(f'/orders/mock/{o.id}/fail/')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.status_of(o), 'failed')
        self.assertEqual(self.cart_count(), 1)

    def test_st_06_awaiting_transfer_to_paid_via_qr(self):
        """TC-ST-06: awaiting_transfer -> paid (Khách bấm xác nhận đã chuyển khoản QR)."""
        o = self.mk_order(method='qr', status='awaiting_transfer')
        self.assertTrue(o.can_change_to('paid'))
        r = self.client.post(f'/orders/qr/{o.id}/confirm/')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.status_of(o), 'paid')

    def test_st_07_awaiting_transfer_to_failed(self):
        """TC-ST-07: awaiting_transfer -> failed (Chuyển khoản hết hạn / Báo lỗi QR)."""
        o = self.mk_order(method='qr', status='awaiting_transfer')
        self.assertTrue(o.can_change_to('failed'))
        o.status = 'failed'
        o.save()
        self.assertEqual(self.status_of(o), 'failed')

    def test_st_08_awaiting_transfer_to_cancelled_via_qr(self):
        """TC-ST-08: awaiting_transfer -> cancelled (Khách POST hủy đơn QR)."""
        o = self.mk_order(method='qr', status='awaiting_transfer')
        self.assertTrue(o.can_change_to('cancelled'))
        r = self.client.post(f'/orders/{o.id}/cancel/')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.status_of(o), 'cancelled')

    def test_st_09_paid_to_confirmed(self):
        """TC-ST-09: paid -> confirmed (Admin duyệt đơn sau khi đã thanh toán)."""
        o = self.mk_order(status='paid')
        self.assertTrue(o.can_change_to('confirmed'))
        o.status = 'confirmed'
        o.save()
        self.assertEqual(self.status_of(o), 'confirmed')

    def test_st_10_paid_to_cancelled(self):
        """TC-ST-10: paid -> cancelled (Admin hủy đơn đã thanh toán & hoàn tiền)."""
        o = self.mk_order(status='paid')
        self.assertTrue(o.can_change_to('cancelled'))
        o.status = 'cancelled'
        o.save()
        self.assertEqual(self.status_of(o), 'cancelled')

    def test_st_11_failed_to_awaiting_transfer(self):
        """TC-ST-11: failed -> awaiting_transfer (Khách chọn thanh toán lại qua QR)."""
        o = self.mk_order(status='failed')
        self.assertTrue(o.can_change_to('awaiting_transfer'))
        o.status = 'awaiting_transfer'
        o.save()
        self.assertEqual(self.status_of(o), 'awaiting_transfer')

    def test_st_12_failed_to_cancelled(self):
        """TC-ST-12: failed -> cancelled (Khách hoặc Admin hủy đơn hỏng thanh toán)."""
        o = self.mk_order(status='failed')
        self.assertTrue(o.can_change_to('cancelled'))
        o.status = 'cancelled'
        o.save()
        self.assertEqual(self.status_of(o), 'cancelled')

    def test_st_13_confirmed_to_shipping(self):
        """TC-ST-13: confirmed -> shipping (Bàn giao cho đơn vị vận chuyển)."""
        o = self.mk_order(status='confirmed')
        self.assertTrue(o.can_change_to('shipping'))
        o.status = 'shipping'
        o.save()
        self.assertEqual(self.status_of(o), 'shipping')

    def test_st_14_confirmed_to_cancelled(self):
        """TC-ST-14: confirmed -> cancelled (Khách hủy đơn trước khi giao hàng)."""
        o = self.mk_order(status='confirmed')
        self.assertTrue(o.can_change_to('cancelled'))
        o.status = 'cancelled'
        o.save()
        self.assertEqual(self.status_of(o), 'cancelled')

    def test_st_15_shipping_to_completed(self):
        """TC-ST-15: shipping -> completed (Giao hàng thành công - Terminal State)."""
        o = self.mk_order(status='shipping')
        self.assertTrue(o.can_change_to('completed'))
        o.status = 'completed'
        o.save()
        self.assertEqual(self.status_of(o), 'completed')
        self.assertTrue(o.is_final)

    def test_st_16_shipping_to_cancelled(self):
        """TC-ST-16: shipping -> cancelled (Giao hàng thất bại / Boom hàng - Terminal State)."""
        o = self.mk_order(status='shipping')
        self.assertTrue(o.can_change_to('cancelled'))
        o.status = 'cancelled'
        o.save()
        self.assertEqual(self.status_of(o), 'cancelled')
        self.assertTrue(o.is_final)

    # -------------------------------------------------------------
    # J.2 Các luồng chuyển bất hợp lệ (Invalid Transitions: TC-ST-INV-01 -> TC-ST-INV-22)
    # -------------------------------------------------------------
    def test_st_inv_01_to_03_pending_invalid(self):
        """TC-ST-INV-01..03: pending không được chuyển sang shipping, completed, awaiting_transfer."""
        o = self.mk_order(status='pending')
        for bad in ('shipping', 'completed', 'awaiting_transfer'):
            with self.subTest(target_status=bad):
                self.assertFalse(o.can_change_to(bad))

    def test_st_inv_04_to_06_awaiting_transfer_invalid(self):
        """TC-ST-INV-04..06: awaiting_transfer không được chuyển sang confirmed, shipping, completed."""
        o = self.mk_order(method='qr', status='awaiting_transfer')
        for bad in ('confirmed', 'shipping', 'completed'):
            with self.subTest(target_status=bad):
                self.assertFalse(o.can_change_to(bad))

    def test_st_inv_07_to_09_paid_invalid(self):
        """TC-ST-INV-07..09: paid không được lùi về pending, failed hoặc nhảy cóc sang completed."""
        o = self.mk_order(status='paid')
        for bad in ('pending', 'failed', 'completed'):
            with self.subTest(target_status=bad):
                self.assertFalse(o.can_change_to(bad))

    def test_st_inv_10_to_11_failed_invalid(self):
        """TC-ST-INV-10..11: failed không được chuyển thẳng sang paid hoặc shipping."""
        o = self.mk_order(status='failed')
        for bad in ('paid', 'shipping'):
            with self.subTest(target_status=bad):
                self.assertFalse(o.can_change_to(bad))

    def test_st_inv_12_to_13_confirmed_invalid(self):
        """TC-ST-INV-12..13: confirmed không được lùi về pending hoặc nhảy cóc sang completed."""
        o = self.mk_order(status='confirmed')
        for bad in ('pending', 'completed'):
            with self.subTest(target_status=bad):
                self.assertFalse(o.can_change_to(bad))

    def test_st_inv_14_to_15_shipping_invalid(self):
        """TC-ST-INV-14..15: shipping không được lùi về confirmed hoặc pending."""
        o = self.mk_order(status='shipping')
        for bad in ('confirmed', 'pending'):
            with self.subTest(target_status=bad):
                self.assertFalse(o.can_change_to(bad))

    def test_st_inv_16_to_18_completed_terminal(self):
        """TC-ST-INV-16..18: completed là trạng thái kết thúc, không được chuyển đi đâu."""
        o = self.mk_order(status='completed')
        self.assertTrue(o.is_final)
        self.assertEqual(len(o.ALLOWED_TRANSITIONS.get('completed', set())), 0)
        for target in ('pending', 'cancelled', 'shipping', 'paid', 'confirmed'):
            with self.subTest(target_status=target):
                self.assertFalse(o.can_change_to(target))

    def test_st_inv_19_to_22_cancelled_terminal(self):
        """TC-ST-INV-19..22: cancelled là trạng thái kết thúc, không được chuyển đi đâu."""
        o = self.mk_order(status='cancelled')
        self.assertTrue(o.is_final)
        self.assertEqual(len(o.ALLOWED_TRANSITIONS.get('cancelled', set())), 0)
        for target in ('pending', 'confirmed', 'paid', 'completed', 'shipping'):
            with self.subTest(target_status=target):
                self.assertFalse(o.can_change_to(target))

    # -------------------------------------------------------------
    # J.3 Kiểm tra toàn diện Ma trận chuyển đổi 8x8 & Bảo vệ Endpoint
    # -------------------------------------------------------------
    def test_st_exhaustive_matrix_8x8(self):
        """Kiểm tra toàn diện ma trận chuyển trạng thái 8x8 (64 cặp trạng thái)."""
        all_statuses = [s[0] for s in Order.STATUS_CHOICES]
        for src in all_statuses:
            o = self.mk_order(status=src)
            allowed = Order.ALLOWED_TRANSITIONS.get(src, set())
            for dst in all_statuses:
                with self.subTest(src=src, dst=dst):
                    if dst in allowed:
                        self.assertTrue(o.can_change_to(dst), f"Chuyển đổi {src} -> {dst} phải hợp lệ")
                    else:
                        self.assertFalse(o.can_change_to(dst), f"Chuyển đổi {src} -> {dst} phải bị chặn")

    def test_st_endpoint_guard_against_illegal_status(self):
        """Endpoint confirm/cancel QR và mock success/fail chặn đơn có trạng thái bất hợp lệ."""
        for terminal_st in ('completed', 'cancelled'):
            with self.subTest(status=terminal_st):
                o = self.mk_order(method='qr', status=terminal_st)
                self.client.post(f'/orders/qr/{o.id}/confirm/')
                self.assertEqual(self.status_of(o), terminal_st)

                self.client.post(f'/orders/{o.id}/cancel/')
                self.assertEqual(self.status_of(o), terminal_st)

        # Mock success không được tác động lên đơn đã confirmed hoặc shipping
        for st in ('confirmed', 'shipping', 'completed', 'cancelled'):
            with self.subTest(mock_invalid_status=st):
                o = self.mk_order(method='mock', status=st)
                self.client.post(f'/orders/mock/{o.id}/success/')
                self.assertEqual(self.status_of(o), st)


# =====================================================================
# K. BỘ KIỂM THỬ HỘP TRẮNG (WHITE-BOX TESTING) - ĐỘ PHỦ TỐI ĐA CFG
# =====================================================================
class WhiteBoxCoverageTests(OrderTestBase):
    """Kiểm thử Hộp trắng (White-box Testing):
    - Đồ thị luồng điều khiển (CFG) & Cyclomatic Complexity V(G).
    - Bao phủ câu lệnh (Statement Coverage 100%).
    - Bao phủ nhánh (Branch / Decision Coverage 100%).
    - Bao phủ điều kiện nhánh (Branch-Condition / MC/DC Coverage).
    - Bao phủ các nhánh ngoại lệ nội bộ (Cart.DoesNotExist, mô hình DB).
    """

    def setUp(self):
        super().setUp()
        self.login()

    # -------------------------------------------------------------
    # K.1 CFG Hàm checkout() - Đường đi & Nhánh quyết định
    # -------------------------------------------------------------
    def test_wb_01_cfg_checkout_get_statement_path(self):
        """TC-WB-01 [Statement]: GET checkout với giỏ hàng hợp lệ (Đường GET chính)."""
        self.fill_cart((self.p_a, 2))
        res = self.client.get('/orders/checkout/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Bình nước tre')
        self.assertIn('total_price', res.context)

    def test_wb_02_cfg_checkout_cart_empty_branch(self):
        """TC-WB-02 [Branch]: POST checkout khi giỏ hàng trống (Nhánh D1 True)."""
        cart, _ = Cart.objects.get_or_create(user=self.user)
        cart.items.all().delete()
        res = self.client.post('/orders/checkout/', self.data())
        self.assertRedirects(res, '/cart/')

    def test_wb_03_cfg_checkout_total_exceeded_branch(self):
        """TC-WB-03 [Branch]: POST checkout khi vượt ORDER_TOTAL_MAX (Nhánh D2 True)."""
        p_huge = Product.objects.create(name='Hàng siêu đắt', price=TOTAL_MAX_PLUS)
        self.fill_cart((p_huge, 1))
        res = self.client.post('/orders/checkout/', self.data())
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.context['total_exceeded'])

    def test_wb_04_cfg_checkout_name_empty_condition(self):
        """TC-WB-04 [Condition]: full_name rỗng (Nhánh D4a: not full_name = True)."""
        self.fill_cart((self.p_a, 1))
        res = self.client.post('/orders/checkout/', self.data(full_name='   '))
        self.assertEqual(res.status_code, 200)
        self.assertIn('Họ tên không được để trống', res.context['error'])

    def test_wb_05_cfg_checkout_name_length_exceeded_condition(self):
        """TC-WB-05 [Condition]: len(full_name) > 255 (Nhánh D4b: len > 255 = True)."""
        self.fill_cart((self.p_a, 1))
        res = self.client.post('/orders/checkout/', self.data(full_name='A' * 256))
        self.assertEqual(res.status_code, 200)
        self.assertIn('Họ tên không được để trống', res.context['error'])

    def test_wb_06_cfg_checkout_phone_empty_condition(self):
        """TC-WB-06 [Condition]: phone rỗng (Nhánh D5a: not phone = True)."""
        self.fill_cart((self.p_a, 1))
        res = self.client.post('/orders/checkout/', self.data(phone=''))
        self.assertEqual(res.status_code, 200)
        self.assertIn('Số điện thoại không được để trống', res.context['error'])

    def test_wb_07_cfg_checkout_phone_length_exceeded_condition(self):
        """TC-WB-07 [Condition]: len(phone) > 20 (Nhánh D5b: len > 20 = True)."""
        self.fill_cart((self.p_a, 1))
        res = self.client.post('/orders/checkout/', self.data(phone='0' * 21))
        self.assertEqual(res.status_code, 200)
        self.assertIn('Số điện thoại không được để trống', res.context['error'])

    def test_wb_08_cfg_checkout_address_empty_branch(self):
        """TC-WB-08 [Branch]: address rỗng (Nhánh D6: not address = True)."""
        self.fill_cart((self.p_a, 1))
        res = self.client.post('/orders/checkout/', self.data(address='  \t  '))
        self.assertEqual(res.status_code, 200)
        self.assertIn('Địa chỉ không được để trống', res.context['error'])

    def test_wb_09_cfg_checkout_payment_method_omitted_branch(self):
        """TC-WB-09 [Branch]: Bỏ qua payment_method trong POST -> mặc định 'cod'."""
        self.fill_cart((self.p_a, 1))
        data = self.data()
        del data['payment_method']
        res = self.client.post('/orders/checkout/', data)
        order = Order.objects.filter(user=self.user).latest('id')
        self.assertEqual(order.payment_method, 'cod')
        self.assertRedirects(res, f'/orders/success/{order.id}/')

    def test_wb_10_cfg_checkout_payment_method_invalid_branch(self):
        """TC-WB-10 [Branch]: payment_method không thuộc ['cod', 'qr', 'mock']."""
        self.fill_cart((self.p_a, 1))
        res = self.client.post('/orders/checkout/', self.data(payment_method='zalopay_unsupported'))
        self.assertEqual(res.status_code, 200)
        self.assertIn('Phương thức thanh toán không hợp lệ', res.context['error'])

    def test_wb_11_cfg_checkout_cod_full_path(self):
        """TC-WB-11 [Path]: Đặt hàng COD hợp lệ -> xóa giỏ hàng, redirect success."""
        self.fill_cart((self.p_a, 1))
        res = self.client.post('/orders/checkout/', self.data(payment_method='cod'))
        order = Order.objects.filter(user=self.user).latest('id')
        self.assertEqual(order.status, 'pending')
        self.assertEqual(self.cart_count(), 0)
        self.assertRedirects(res, f'/orders/success/{order.id}/')

    def test_wb_12_cfg_checkout_qr_full_path(self):
        """TC-WB-12 [Path]: Đặt hàng QR hợp lệ -> status awaiting_transfer, giữ giỏ hàng, redirect qr."""
        self.fill_cart((self.p_a, 1))
        res = self.client.post('/orders/checkout/', self.data(payment_method='qr'))
        order = Order.objects.filter(user=self.user).latest('id')
        self.assertEqual(order.status, 'awaiting_transfer')
        self.assertEqual(self.cart_count(), 1)
        self.assertRedirects(res, f'/orders/qr/{order.id}/')

    def test_wb_13_cfg_checkout_mock_full_path(self):
        """TC-WB-13 [Path]: Đặt hàng Mock hợp lệ -> status pending, giữ giỏ hàng, redirect mock."""
        self.fill_cart((self.p_a, 1))
        res = self.client.post('/orders/checkout/', self.data(payment_method='mock'))
        order = Order.objects.filter(user=self.user).latest('id')
        self.assertEqual(order.status, 'pending')
        self.assertEqual(self.cart_count(), 1)  # Giữ giỏ chờ thanh toán
        self.assertRedirects(res, f'/orders/mock/{order.id}/')

    # -------------------------------------------------------------
    # K.2 CFG Các nhánh ngoại lệ & Cạnh ẩn (Exception Branches)
    # -------------------------------------------------------------
    def test_wb_14_cfg_checkout_cart_does_not_exist_exception(self):
        """TC-WB-14 [Exception]: request.user.cart ném Cart.DoesNotExist -> redirect /cart/."""
        with mock.patch.object(User, 'cart', new_callable=mock.PropertyMock) as mock_cart:
            mock_cart.side_effect = Cart.DoesNotExist
            res = self.client.get('/orders/checkout/')
            self.assertRedirects(res, '/cart/')

    def test_wb_15_cfg_order_qr_redirect_if_not_awaiting(self):
        """TC-WB-15 [Branch views:146]: order_qr khi order.status != 'awaiting_transfer' -> redirect success."""
        o = self.mk_order(method='qr', status='paid')
        res = self.client.get(f'/orders/qr/{o.id}/')
        self.assertRedirects(res, f'/orders/success/{o.id}/')

    # -------------------------------------------------------------
    # K.3 CFG confirm_qr_paid() & MC/DC Biểu thức ghép 3 điều kiện
    # if request.method == 'POST' and order.payment_method == 'qr' and order.status == 'awaiting_transfer':
    # -------------------------------------------------------------
    def test_wb_16_cfg_confirm_qr_paid_all_true(self):
        """TC-WB-16 [MC/DC TTT]: POST + QR + awaiting_transfer -> Chuyển paid & xóa giỏ."""
        self.fill_cart((self.p_a, 1))
        o = self.mk_order(method='qr', status='awaiting_transfer')
        res = self.client.post(f'/orders/qr/{o.id}/confirm/')
        self.assertEqual(self.status_of(o), 'paid')
        self.assertEqual(self.cart_count(), 0)
        self.assertRedirects(res, f'/orders/success/{o.id}/')

    def test_wb_17_cfg_confirm_qr_paid_c1_false_get_method(self):
        """TC-WB-17 [MC/DC FTT]: Method=GET + QR + awaiting_transfer -> Không đổi trạng thái."""
        o = self.mk_order(method='qr', status='awaiting_transfer')
        res = self.client.get(f'/orders/qr/{o.id}/confirm/')
        self.assertEqual(self.status_of(o), 'awaiting_transfer')
        self.assertRedirects(res, f'/orders/success/{o.id}/')

    def test_wb_18_cfg_confirm_qr_paid_c2_false_payment_cod(self):
        """TC-WB-18 [MC/DC TFT]: POST + COD + awaiting_transfer -> Không đổi trạng thái."""
        o = self.mk_order(method='cod', status='awaiting_transfer')
        res = self.client.post(f'/orders/qr/{o.id}/confirm/')
        self.assertEqual(self.status_of(o), 'awaiting_transfer')
        self.assertRedirects(res, f'/orders/success/{o.id}/')

    def test_wb_19_cfg_confirm_qr_paid_c3_false_status_already_paid(self):
        """TC-WB-19 [MC/DC TTF]: POST + QR + status='paid' -> Không đổi trạng thái."""
        o = self.mk_order(method='qr', status='paid')
        res = self.client.post(f'/orders/qr/{o.id}/confirm/')
        self.assertEqual(self.status_of(o), 'paid')
        self.assertRedirects(res, f'/orders/success/{o.id}/')

    def test_wb_20_cfg_confirm_qr_paid_cart_does_not_exist(self):
        """TC-WB-20 [Exception views:164-165]: confirm_qr_paid bắt ngoại lệ Cart.DoesNotExist."""
        o = self.mk_order(method='qr', status='awaiting_transfer')
        with mock.patch.object(User, 'cart', new_callable=mock.PropertyMock) as mock_cart:
            mock_cart.side_effect = Cart.DoesNotExist
            res = self.client.post(f'/orders/qr/{o.id}/confirm/')
            self.assertEqual(self.status_of(o), 'paid')
            self.assertRedirects(res, f'/orders/success/{o.id}/')

    def test_wb_21_cfg_mock_payment_success_cart_does_not_exist(self):
        """TC-WB-21 [Exception views:188-189]: mock_payment_success bắt ngoại lệ Cart.DoesNotExist."""
        o = self.mk_order(method='mock', status='pending')
        with mock.patch.object(User, 'cart', new_callable=mock.PropertyMock) as mock_cart:
            mock_cart.side_effect = Cart.DoesNotExist
            res = self.client.post(f'/orders/mock/{o.id}/success/')
            self.assertEqual(self.status_of(o), 'paid')
            self.assertRedirects(res, f'/orders/success/{o.id}/')

    def test_wb_22_cfg_mock_payment_fail_path(self):
        """TC-WB-22 [Path]: mock_payment_fail đổi trạng thái từ pending -> failed."""
        o = self.mk_order(method='mock', status='pending')
        res = self.client.post(f'/orders/mock/{o.id}/fail/')
        self.assertEqual(self.status_of(o), 'failed')
        self.assertRedirects(res, f'/orders/success/{o.id}/')

    def test_wb_23_cfg_cancel_qr_order_path(self):
        """TC-WB-23 [Path]: cancel_qr_order hủy đơn awaiting_transfer -> cancelled."""
        o = self.mk_order(method='qr', status='awaiting_transfer')
        res = self.client.post(f'/orders/{o.id}/cancel/')
        self.assertEqual(self.status_of(o), 'cancelled')
        self.assertRedirects(res, '/cart/')

    def test_wb_24_cfg_cancel_qr_order_wrong_status(self):
        """TC-WB-24 [Branch]: cancel_qr_order trên đơn không phải awaiting_transfer -> giữ nguyên."""
        o = self.mk_order(method='qr', status='paid')
        res = self.client.post(f'/orders/{o.id}/cancel/')
        self.assertEqual(self.status_of(o), 'paid')
        self.assertRedirects(res, '/cart/')

    def test_wb_25_cfg_models_str_coverage(self):
        """TC-WB-25 [Statement models:78,93]: Phủ __str__ của Order và OrderItem."""
        o = self.mk_order()
        item = o.items.first()
        self.assertEqual(str(o), f"Order #{o.id} - {self.user.username}")
        self.assertEqual(str(item), 'Bình nước tre')

    def test_wb_26_cfg_my_orders_view(self):
        """TC-WB-26 [Statement views:204-209]: Phủ view my_orders liệt kê đơn QR."""
        self.mk_order(method='qr', status='awaiting_transfer')
        res = self.client.get('/orders/my/')
        self.assertEqual(res.status_code, 200)

    def test_wb_27_cfg_clear_cart_empty_order_items(self):
        """TC-WB-27 [Branch views:14-16]: _clear_order_items_from_cart khi đơn không có OrderItem -> cart.delete()."""
        self.fill_cart((self.p_a, 1))
        o = Order.objects.create(
            user=self.user, full_name='Nguyễn Văn A', phone='0900000000',
            address='1 Lê Lợi', payment_method='qr', status='awaiting_transfer',
            total_price=Decimal('50000'),
        )
        res = self.client.post(f'/orders/qr/{o.id}/confirm/')
        self.assertEqual(self.status_of(o), 'paid')
        self.assertEqual(self.cart_count(), 0)

    def test_wb_28_cfg_clear_cart_item_not_in_cart(self):
        """TC-WB-28 [Branch views:19->17]: _clear_order_items_from_cart khi SP trong đơn không có trong giỏ."""
        self.fill_cart((self.p_a, 1))
        o = Order.objects.create(
            user=self.user, full_name='Nguyễn Văn A', phone='0900000000',
            address='1 Lê Lợi', payment_method='qr', status='awaiting_transfer',
            total_price=Decimal('50000'),
        )
        OrderItem.objects.create(order=o, product_name='Sản phẩm khác', price=Decimal('50000'), quantity=1)
        res = self.client.post(f'/orders/qr/{o.id}/confirm/')
        self.assertEqual(self.status_of(o), 'paid')
        self.assertEqual(self.cart_count(), 1)

    def test_wb_29_cfg_clear_cart_partial_quantity(self):
        """TC-WB-29 [Branch views:22-24]: _clear_order_items_from_cart khi giỏ có SL nhiều hơn đơn -> trừ bớt SL."""
        self.fill_cart((self.p_a, 3))
        o = self.mk_order(method='qr', status='awaiting_transfer', qty=1)
        res = self.client.post(f'/orders/qr/{o.id}/confirm/')
        self.assertEqual(self.status_of(o), 'paid')
        self.assertEqual(self.cart_count(), 1)
        cart_item = CartItem.objects.get(cart__user=self.user, product=self.p_a)
        self.assertEqual(cart_item.quantity, 2)

