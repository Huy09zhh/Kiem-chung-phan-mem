"""Kiểm thử hộp đen FR3 - Giỏ hàng: Phân hoạch tương đương (EP) & Giá trị biên (BVA).

Mỗi test ứng với 1 test case trong docs/TestCase_FR3_Cart_EP_BVA.md.
Chạy: python manage.py test cart -v 2
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase

from products.models import Product
from .models import Cart, CartItem

INT64_MAX = 9223372036854775807
# Giới hạn trên của PositiveIntegerField (CartItem.quantity) theo Django
QTY_MAX = 2147483647


class CartTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('cartuser', 'cart@test.com', 'User@12345')
        cls.p_a = Product.objects.create(name='Bình nước tre', price=Decimal('50000'))
        cls.p_b = Product.objects.create(name='Túi vải canvas', price=Decimal('30000'))
        # Thêm 2 SP để min+1 và max-1 là các id khác nhau
        Product.objects.create(name='Ống hút cỏ', price=Decimal('20000'))
        Product.objects.create(name='Xà phòng hữu cơ', price=Decimal('45000'))
        cls.ids = list(Product.objects.order_by('id').values_list('id', flat=True))
        cls.min_id = Product.objects.order_by('id').first().id
        cls.max_id = Product.objects.order_by('-id').first().id

    def setUp(self):
        # Không ném exception ra test để đo được mã HTTP 500 thật
        self.client = Client(raise_request_exception=False)

    def login(self):
        self.client.force_login(self.user)

    def set_qty(self, product, quantity):
        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.update_or_create(cart=cart, product=product, defaults={'quantity': quantity})

    def qty(self, product):
        item = CartItem.objects.filter(cart__user=self.user, product=product).first()
        return item.quantity if item else None


class CartEquivalencePartitionTests(CartTestBase):
    """Phân hoạch tương đương."""

    def test_ep_01_guest_add_redirects_login(self):
        """TC-CART-EP-01: Khách chưa đăng nhập thêm SP -> chuyển login kèm next."""
        r = self.client.get(f'/cart/add/{self.p_a.id}/')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, f'/accounts/login/?next=/cart/add/{self.p_a.id}/')
        self.assertEqual(CartItem.objects.count(), 0)

    def test_ep_02_guest_view_cart_redirects_login(self):
        """TC-CART-EP-02: Khách chưa đăng nhập xem giỏ -> chuyển login."""
        r = self.client.get('/cart/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/accounts/login/', r.url)

    def test_ep_03_guest_increase_redirects_login(self):
        """TC-CART-EP-03: Khách chưa đăng nhập tăng số lượng -> chuyển login."""
        r = self.client.get(f'/cart/increase/{self.p_a.id}/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/accounts/login/', r.url)

    def test_ep_04_add_new_product_creates_item_qty_1(self):
        """TC-CART-EP-04: Thêm SP hợp lệ chưa có trong giỏ -> tạo CartItem quantity=1."""
        self.login()
        r = self.client.get(f'/cart/add/{self.p_a.id}/')
        self.assertRedirects(r, '/cart/', fetch_redirect_response=False)
        self.assertEqual(self.qty(self.p_a), 1)

    def test_ep_05_add_existing_product_increments(self):
        """TC-CART-EP-05: Thêm SP đã có trong giỏ -> không tạo dòng mới, quantity +1."""
        self.login()
        self.set_qty(self.p_a, 1)
        self.client.get(f'/cart/add/{self.p_a.id}/')
        self.assertEqual(self.qty(self.p_a), 2)
        self.assertEqual(CartItem.objects.filter(cart__user=self.user).count(), 1)

    def test_ep_06_add_nonexistent_product_404(self):
        """TC-CART-EP-06: product_id nguyên dương nhưng không tồn tại -> 404."""
        self.login()
        r = self.client.get(f'/cart/add/{self.max_id + 100}/')
        self.assertEqual(r.status_code, 404)
        self.assertEqual(CartItem.objects.count(), 0)

    def test_ep_07_add_negative_id_404(self):
        """TC-CART-EP-07: product_id âm (-1) -> 404."""
        self.login()
        self.assertEqual(self.client.get('/cart/add/-1/').status_code, 404)

    def test_ep_08_add_non_numeric_id_404(self):
        """TC-CART-EP-08: product_id không phải số ('abc') -> 404."""
        self.login()
        self.assertEqual(self.client.get('/cart/add/abc/').status_code, 404)

    def test_ep_09_increase_product_in_cart(self):
        """TC-CART-EP-09: Tăng SP có trong giỏ -> quantity +1."""
        self.login()
        self.set_qty(self.p_a, 2)
        self.client.get(f'/cart/increase/{self.p_a.id}/')
        self.assertEqual(self.qty(self.p_a), 3)

    def test_ep_10_increase_product_not_in_cart_404(self):
        """TC-CART-EP-10: Tăng SP tồn tại nhưng không có trong giỏ -> 404."""
        self.login()
        self.assertEqual(self.client.get(f'/cart/increase/{self.p_a.id}/').status_code, 404)

    def test_ep_11_decrease_product_not_in_cart_404(self):
        """TC-CART-EP-11: Giảm SP tồn tại nhưng không có trong giỏ -> 404."""
        self.login()
        self.assertEqual(self.client.get(f'/cart/decrease/{self.p_a.id}/').status_code, 404)

    def test_ep_12_remove_product_in_cart(self):
        """TC-CART-EP-12: Xóa SP có trong giỏ (quantity=5) -> xóa hẳn, không phụ thuộc số lượng."""
        self.login()
        self.set_qty(self.p_a, 5)
        r = self.client.get(f'/cart/remove/{self.p_a.id}/')
        self.assertEqual(r.status_code, 302)
        self.assertIsNone(self.qty(self.p_a))

    def test_ep_13_remove_product_not_in_cart_no_error(self):
        """TC-CART-EP-13: Xóa SP không có trong giỏ -> 302 về giỏ, không lỗi."""
        self.login()
        r = self.client.get(f'/cart/remove/{self.p_a.id}/')
        self.assertRedirects(r, '/cart/', fetch_redirect_response=False)

    def test_ep_14_empty_cart_message(self):
        """TC-CART-EP-14: Giỏ rỗng -> 200, hiển thị 'Giỏ hàng của bạn đang trống', ẩn nút đặt hàng."""
        self.login()
        r = self.client.get('/cart/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Giỏ hàng của bạn đang trống')
        self.assertNotContains(r, '/orders/checkout/')

    def test_ep_15_cart_isolated_per_user(self):
        """TC-CART-EP-15: User khác không thấy và không tăng được SP trong giỏ của user1."""
        self.set_qty(self.p_a, 1)
        other = User.objects.create_user('other', 'other@test.com', 'User@12345')
        self.client.force_login(other)
        r = self.client.get('/cart/')
        self.assertNotContains(r, self.p_a.name)
        self.assertEqual(self.client.get(f'/cart/increase/{self.p_a.id}/').status_code, 404)
        self.assertEqual(self.qty(self.p_a), 1)


class CartBoundaryValueTests(CartTestBase):
    """Phân tích giá trị biên."""

    def test_bva_01_product_id_zero(self):
        """TC-CART-BVA-01: product_id = 0 (dưới biên nhỏ nhất) -> 404."""
        self.login()
        self.assertEqual(self.client.get('/cart/add/0/').status_code, 404)

    def test_bva_02_product_id_min(self):
        """TC-CART-BVA-02: product_id = id nhỏ nhất đang tồn tại -> thêm thành công."""
        self.login()
        self.client.get(f'/cart/add/{self.min_id}/')
        self.assertEqual(self.qty(Product.objects.get(id=self.min_id)), 1)

    def test_bva_03_product_id_max(self):
        """TC-CART-BVA-03: product_id = id lớn nhất đang tồn tại -> thêm thành công."""
        self.login()
        self.client.get(f'/cart/add/{self.max_id}/')
        self.assertEqual(self.qty(Product.objects.get(id=self.max_id)), 1)

    def test_bva_04_product_id_max_plus_1(self):
        """TC-CART-BVA-04: product_id = max_id + 1 (ngay trên biên) -> 404."""
        self.login()
        self.assertEqual(self.client.get(f'/cart/add/{self.max_id + 1}/').status_code, 404)

    def test_bva_05_product_id_int64_max(self):
        """TC-CART-BVA-05: product_id = 2^63-1 (biên trên kiểu BIGINT) -> 404."""
        self.login()
        self.assertEqual(self.client.get(f'/cart/add/{INT64_MAX}/').status_code, 404)

    def test_bva_06_product_id_int64_max_plus_1(self):
        """TC-CART-BVA-06: product_id = 2^63 (vượt biên BIGINT) -> 404, không được 500."""
        self.login()
        for action in ('add', 'increase', 'decrease', 'remove'):
            with self.subTest(action=action):
                r = self.client.get(f'/cart/{action}/{INT64_MAX + 1}/')
                self.assertEqual(r.status_code, 404)

    def test_bva_07_decrease_from_1_removes_item(self):
        """TC-CART-BVA-07: Giảm khi quantity = 1 -> 0 -> xóa khỏi giỏ."""
        self.login()
        self.set_qty(self.p_a, 1)
        self.client.get(f'/cart/decrease/{self.p_a.id}/')
        self.assertIsNone(self.qty(self.p_a))

    def test_bva_08_decrease_from_2_keeps_item(self):
        """TC-CART-BVA-08: Giảm khi quantity = 2 -> còn 1, vẫn trong giỏ."""
        self.login()
        self.set_qty(self.p_a, 2)
        self.client.get(f'/cart/decrease/{self.p_a.id}/')
        self.assertEqual(self.qty(self.p_a), 1)

    def test_bva_09_decrease_from_3(self):
        """TC-CART-BVA-09: Giảm khi quantity = 3 -> còn 2."""
        self.login()
        self.set_qty(self.p_a, 3)
        self.client.get(f'/cart/decrease/{self.p_a.id}/')
        self.assertEqual(self.qty(self.p_a), 2)

    def test_bva_10_increase_from_1(self):
        """TC-CART-BVA-10: Tăng khi quantity = 1 (biên dưới hợp lệ) -> 2."""
        self.login()
        self.set_qty(self.p_a, 1)
        self.client.get(f'/cart/increase/{self.p_a.id}/')
        self.assertEqual(self.qty(self.p_a), 2)

    def test_bva_11_cart_one_item_total(self):
        """TC-CART-BVA-11: Giỏ có đúng 1 SP, quantity = 1 -> tổng = đơn giá (50.000)."""
        self.login()
        self.set_qty(self.p_a, 1)
        r = self.client.get('/cart/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['total_price'], Decimal('50000'))

    def test_bva_12_cart_two_items_total(self):
        """TC-CART-BVA-12: Giỏ có 2 SP (A x2, B x1) -> tổng = 50.000*2 + 30.000 = 130.000."""
        self.login()
        self.set_qty(self.p_a, 2)
        self.set_qty(self.p_b, 1)
        r = self.client.get('/cart/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['total_price'], Decimal('130000'))

    def test_bva_13_remove_last_item_becomes_empty(self):
        """TC-CART-BVA-13: Giỏ 1 SP -> xóa SP cuối cùng -> giỏ 0 SP, hiện thông báo trống."""
        self.login()
        self.set_qty(self.p_a, 1)
        self.client.get(f'/cart/remove/{self.p_a.id}/')
        self.assertContains(self.client.get('/cart/'), 'Giỏ hàng của bạn đang trống')

    def test_bva_14_product_id_min_plus_1(self):
        """TC-CART-BVA-14: product_id = min+1 (id hợp lệ kế trên min) -> thêm thành công."""
        self.login()
        pid = self.ids[1]
        r = self.client.get(f'/cart/add/{pid}/')
        self.assertRedirects(r, '/cart/', fetch_redirect_response=False)
        self.assertEqual(self.qty(Product.objects.get(id=pid)), 1)

    def test_bva_15_product_id_max_minus_1(self):
        """TC-CART-BVA-15: product_id = max-1 (id hợp lệ kế dưới max) -> thêm thành công."""
        self.login()
        pid = self.ids[-2]
        r = self.client.get(f'/cart/add/{pid}/')
        self.assertRedirects(r, '/cart/', fetch_redirect_response=False)
        self.assertEqual(self.qty(Product.objects.get(id=pid)), 1)

    def test_bva_16_increase_to_qty_max(self):
        """TC-CART-BVA-16: Tăng khi quantity = 2147483646 (max-1) -> 2147483647 (max)."""
        self.login()
        self.set_qty(self.p_a, QTY_MAX - 1)
        r = self.client.get(f'/cart/increase/{self.p_a.id}/')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.qty(self.p_a), QTY_MAX)

    def test_bva_17_increase_above_qty_max(self):
        """TC-CART-BVA-17: Tăng khi quantity = 2147483647 (max) -> không vượt max, không lỗi 500."""
        self.login()
        self.set_qty(self.p_a, QTY_MAX)
        r = self.client.get(f'/cart/increase/{self.p_a.id}/')
        self.assertNotEqual(r.status_code, 500)
        self.assertLessEqual(self.qty(self.p_a), QTY_MAX)

    def test_bva_18_add_above_qty_max(self):
        """TC-CART-BVA-18: Thêm SP đã có quantity = 2147483647 (max) -> không vượt max, không lỗi 500."""
        self.login()
        self.set_qty(self.p_a, QTY_MAX)
        r = self.client.get(f'/cart/add/{self.p_a.id}/')
        self.assertNotEqual(r.status_code, 500)
        self.assertLessEqual(self.qty(self.p_a), QTY_MAX)
