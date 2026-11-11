from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Category, Product

User = get_user_model()


class ProductListCategoryFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.food = Category.objects.create(name='Food')
        cls.clothing = Category.objects.create(name='Clothing')
        cls.apple = Product.objects.create(
            name='Red Apple', price=100, category=cls.food
        )
        cls.shirt = Product.objects.create(
            name='Blue Shirt', price=200, category=cls.clothing
        )

    def test_non_numeric_category_does_not_crash_or_filter_products(self):
        for value in ('abc', '1abc', '1.5'):
            with self.subTest(category=value):
                response = self.client.get(
                    reverse('product_list'), {'category': value}
                )
                self.assertEqual(response.status_code, 200)
                self.assertCountEqual(
                    response.context['products'].values_list('pk', flat=True),
                    (self.apple.pk, self.shirt.pk),
                )

    def test_out_of_range_category_does_not_crash(self):
        response = self.client.get(
            reverse('product_list'), {'category': '9' * 30}
        )
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            response.context['products'].values_list('pk', flat=True),
            (self.apple.pk, self.shirt.pk),
        )

    def test_valid_category_filters_products(self):
        response = self.client.get(
            reverse('product_list'), {'category': str(self.food.pk)}
        )
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['products'], [self.apple])

    def test_unknown_numeric_category_returns_empty_list(self):
        response = self.client.get(
            reverse('product_list'), {'category': '999999'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['products'], [])

    def test_invalid_category_keeps_other_filters(self):
        response = self.client.get(
            reverse('product_list'), {'category': 'abc', 'q': 'Apple'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['products'], [self.apple])


class ProductLifecycleStateTransitionTests(TestCase):
    """State Transition Testing cho vòng đời & trạng thái giảm giá của Sản phẩm (TC-PS-033 -> TC-PS-037)."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username='ps_stt_admin', password='Password@123', is_staff=True
        )
        cls.customer = User.objects.create_user(
            username='ps_stt_user', password='Password@123', is_staff=False
        )
        cls.category = Category.objects.create(name='Cây để bàn')

    def setUp(self):
        self.api = APIClient()

    def _create_product(self, name='Sen đá nâu', price='50000', old_price=None):
        return Product.objects.create(
            name=name,
            price=Decimal(price),
            old_price=Decimal(old_price) if old_price is not None else None,
            category=self.category,
        )

    def test_ps_033_state_nonexistent_to_normal_price(self):
        """TC-PS-033: [Chưa tồn tại] --(POST Admin)--> [Tồn tại - Giá thường]."""
        self.api.force_authenticate(user=self.admin)
        res = self.api.post('/products/api/', {
            'name': 'Sen đá nâu',
            'price': '50000',
            'category': self.category.pk,
        }, format='json')
        self.assertEqual(res.status_code, 201)
        product = Product.objects.get(pk=res.data['id'])
        self.assertFalse(bool(product.has_discount))
        self.assertEqual(product.discount_percent, 0)

    def test_ps_034_state_normal_to_discounted(self):
        """TC-PS-034: [Giá thường] --(PATCH thêm old_price > price)--> [Đang giảm giá]."""
        product = self._create_product(price='50000', old_price=None)
        self.api.force_authenticate(user=self.admin)
        res = self.api.patch(f'/products/api/{product.pk}/', {'old_price': '100000'}, format='json')
        self.assertEqual(res.status_code, 200)
        product.refresh_from_db()
        self.assertTrue(product.has_discount)
        self.assertEqual(product.discount_percent, 50)

    def test_ps_035_state_discounted_to_normal(self):
        """TC-PS-035: [Đang giảm giá] --(PATCH old_price=None)--> [Giá thường]."""
        product = self._create_product(name='Cây kim tiền', price='80000', old_price='100000')
        self.assertTrue(product.has_discount)
        self.api.force_authenticate(user=self.admin)
        res = self.api.patch(f'/products/api/{product.pk}/', {'old_price': None}, format='json')
        self.assertEqual(res.status_code, 200)
        product.refresh_from_db()
        self.assertFalse(bool(product.has_discount))
        self.assertEqual(product.discount_percent, 0)

    def test_ps_036_state_existing_to_deleted_final(self):
        """TC-PS-036: [Đang tồn tại] --(DELETE Admin)--> [Đã xóa]; gọi lại trả về 404."""
        product = self._create_product(name='Xương rồng', price='40000')
        self.api.force_authenticate(user=self.admin)
        res_del = self.api.delete(f'/products/api/{product.pk}/')
        self.assertEqual(res_del.status_code, 204)
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())
        self.assertEqual(self.api.get(f'/products/api/{product.pk}/').status_code, 404)
        self.assertEqual(
            self.api.patch(f'/products/api/{product.pk}/', {'price': '45000'}, format='json').status_code,
            404,
        )
        self.assertEqual(self.api.delete(f'/products/api/{product.pk}/').status_code, 404)

    def test_ps_037_invalid_transitions_unauthorized_users(self):
        """TC-PS-037: Guest/Customer gọi POST/PATCH/DELETE -> chặn 401/403, giữ nguyên trạng thái DB."""
        product = self._create_product(name='Cây trầu bà', price='60000')
        for client_user, expected_code in ((None, 401), (self.customer, 403)):
            self.api.force_authenticate(user=client_user)
            with self.subTest(expected_code=expected_code):
                self.assertEqual(
                    self.api.post('/products/api/', {'name': 'SP lậu', 'price': '10000'}, format='json').status_code,
                    expected_code,
                )
                self.assertEqual(
                    self.api.patch(f'/products/api/{product.pk}/', {'price': '1000'}, format='json').status_code,
                    expected_code,
                )
                self.assertEqual(
                    self.api.delete(f'/products/api/{product.pk}/').status_code,
                    expected_code,
                )
        product.refresh_from_db()
        self.assertEqual(product.price, Decimal('60000'))


class ProductDecisionTableTests(TestCase):
    """Decision Table Testing cho API chi tiết SP & Tìm kiếm/Lọc/Sắp xếp (TC-PS-038 -> TC-PS-048)."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username='ps_dt_admin', password='Password@123', is_staff=True
        )
        cls.customer = User.objects.create_user(
            username='ps_dt_user', password='Password@123', is_staff=False
        )
        cls.cat_indoor = Category.objects.create(name='Cây trong nhà')
        cls.cat_outdoor = Category.objects.create(name='Cây ngoài trời')

        cls.p1 = Product.objects.create(name='Bàng Singapore', price=Decimal('200000'), category=cls.cat_indoor)
        cls.p2 = Product.objects.create(name='Anthurium Hồng', price=Decimal('100000'), category=cls.cat_indoor)
        cls.p3 = Product.objects.create(name='Cây Hoa Giấy', price=Decimal('150000'), category=cls.cat_outdoor)

    def setUp(self):
        self.api = APIClient()

    # ----- Bảng quyết định 1: Phân quyền & xử lý /products/api/<pk>/ -----
    def test_ps_038_dt_r1_get_existing_product_anonymous(self):
        """TC-PS-038 (R1): GET + SP tồn tại (không cần login) -> 200 OK."""
        res = self.api.get(f'/products/api/{self.p1.pk}/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['name'], 'Bàng Singapore')

    def test_ps_039_dt_r2_get_nonexistent_product(self):
        """TC-PS-039 (R2): GET + SP không tồn tại -> 404 Not Found."""
        res = self.api.get('/products/api/999999/')
        self.assertEqual(res.status_code, 404)

    def test_ps_040_dt_r3_write_unauthenticated_returns_401(self):
        """TC-PS-040 (R3): PUT/PATCH/DELETE + Chưa đăng nhập -> 401 Unauthorized."""
        res = self.api.put(f'/products/api/{self.p1.pk}/', {'name': 'X', 'price': '1000'}, format='json')
        self.assertEqual(res.status_code, 401)

    def test_ps_041_dt_r4_write_non_staff_returns_403(self):
        """TC-PS-041 (R4): PUT/PATCH/DELETE + User thường -> 403 Forbidden."""
        self.api.force_authenticate(user=self.customer)
        res = self.api.patch(f'/products/api/{self.p1.pk}/', {'price': '1000'}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_ps_042_dt_r5_write_admin_invalid_data_returns_400(self):
        """TC-PS-042 (R5): PUT + Admin + SP tồn tại + Dữ liệu thiếu field -> 400 Bad Request."""
        self.api.force_authenticate(user=self.admin)
        res = self.api.put(f'/products/api/{self.p1.pk}/', {'name': 'Chỉ có tên'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_ps_043_dt_r6_write_admin_valid_data_returns_200(self):
        """TC-PS-043 (R6): PATCH + Admin + SP tồn tại + Dữ liệu hợp lệ -> 200 OK & cập nhật DB."""
        self.api.force_authenticate(user=self.admin)
        res = self.api.patch(f'/products/api/{self.p1.pk}/', {'price': '250000'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.price, Decimal('250000'))

    # ----- Bảng quyết định 2: Tổ hợp Tìm kiếm - Lọc - Sắp xếp /products/ -----
    def test_ps_044_dt_s1_default_list(self):
        """TC-PS-044 (S1): Không q, không category, sort mặc định -> toàn bộ SP theo -id."""
        res = self.client.get(reverse('product_list'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['products']), [self.p3, self.p2, self.p1])

    def test_ps_045_dt_s2_search_keyword_only(self):
        """TC-PS-045 (S2): Có q='Hồng', không category, sort mặc định -> chỉ trả p2."""
        res = self.client.get(reverse('product_list'), {'q': 'Hồng'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['products']), [self.p2])

    def test_ps_046_dt_s3_valid_category_and_sort_price_asc(self):
        """TC-PS-046 (S3): Không q, category hợp lệ, sort='price_asc' -> p2 trước p1."""
        res = self.client.get(reverse('product_list'), {
            'category': str(self.cat_indoor.pk),
            'sort': 'price_asc',
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['products']), [self.p2, self.p1])

    def test_ps_047_dt_s4_keyword_with_invalid_category_and_sort_name_asc(self):
        """TC-PS-047 (S4): Có q='a', category='abc', sort='name_asc' -> bỏ qua lỗi category, lọc q & sort A-Z."""
        res = self.client.get(reverse('product_list'), {
            'q': 'a',
            'category': 'abc',
            'sort': 'name_asc',
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['products']), [self.p2, self.p1, self.p3])

    def test_ps_048_dt_s5_valid_category_no_matching_keyword(self):
        """TC-PS-048 (S5): category hợp lệ + q không khớp -> trả danh sách rỗng []."""
        res = self.client.get(reverse('product_list'), {
            'category': str(self.cat_indoor.pk),
            'q': 'KhôngTồnTại',
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['products']), [])
