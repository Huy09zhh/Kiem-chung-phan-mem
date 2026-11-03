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
from .models import Order, OrderItem

# Giới hạn Order.total_price = DecimalField(max_digits=10, decimal_places=2)
# -> tối đa 8 chữ số phần nguyên = 99.999.999 VND
TOTAL_MAX = Decimal('99999999')
TOTAL_MAX_PLUS = Decimal('100000000')


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
        """TC-ORD-29: QR -> Order awaiting_transfer, giỏ rỗng, chuyển /orders/qr/<id>/."""
        self.fill_cart((self.p_a, 1))
        r = self.checkout(payment_method='qr')
        o = Order.objects.get()
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, f'/orders/qr/{o.id}/')
        self.assertEqual((o.status, o.payment_method), ('awaiting_transfer', 'qr'))
        self.assertEqual(self.cart_count(), 0)

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

    def test_ord_50_total_at_max_99_999_999(self):
        """TC-ORD-50: BVA max - tổng tiền 99.999.999 VND (8 chữ số) -> tạo đơn."""
        self.one_product_cart(TOTAL_MAX)
        r = self.checkout()
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Order.objects.get().total_price, TOTAL_MAX)

    def test_ord_51_total_above_max_is_handled_gracefully(self):
        """TC-ORD-51: BVA max+ - tổng tiền 100.000.000 VND vượt giới hạn cột total_price -> không lỗi 500 và KHÔNG lưu đơn."""
        self.one_product_cart(TOTAL_MAX_PLUS)
        r = self.checkout()
        self.assertNotEqual(r.status_code, 500, 'Server không được trả lỗi 500')
        self.assertEqual(Order.objects.count(), 0, 'Đơn có tổng vượt max_digits của cột vẫn bị lưu')
        self.assertEqual(OrderItem.objects.count(), 0)

    def test_ord_52_atomic_order_creation(self):
        """TC-ORD-52 (NFR3 - ACID): Lỗi khi tạo OrderItem -> rollback, không còn Order mồ côi, giỏ giữ nguyên."""
        self.fill_cart((self.p_a, 1))
        with mock.patch.object(OrderItem, 'save', side_effect=RuntimeError('boom')):
            self.checkout()
        self.assertEqual(Order.objects.count(), 0, 'Order mồ côi (không có OrderItem) vẫn bị lưu')
        self.assertEqual(self.cart_count(), 1)
