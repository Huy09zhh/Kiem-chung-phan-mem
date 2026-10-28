from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from products.models import Product


class AdminProductPriceValidationTests(TestCase):
    def setUp(self):
        admin = get_user_model().objects.create_user(
            username='product_admin', password='test-password', is_staff=True
        )
        self.client.force_login(admin)

    def test_create_rejects_old_price_below_or_equal_to_price(self):
        for old_price in ('99999', '100000'):
            with self.subTest(old_price=old_price):
                response = self.client.post(reverse('admin_product_create'), {
                    'name': 'Test BVA giá cũ',
                    'price': '100000',
                    'old_price': old_price,
                })
                self.assertEqual(response.status_code, 200)
                self.assertIn('old_price', response.context['form'].errors)
                self.assertFalse(Product.objects.filter(name='Test BVA giá cũ').exists())

    def test_create_accepts_higher_or_empty_old_price(self):
        for old_price in ('100001', ''):
            with self.subTest(old_price=old_price):
                response = self.client.post(reverse('admin_product_create'), {
                    'name': f'Sản phẩm {old_price or "không giảm giá"}',
                    'price': '100000',
                    'old_price': old_price,
                })
                self.assertRedirects(response, reverse('admin_product_list'))

    def test_update_rejects_invalid_old_price_without_changing_product(self):
        product = Product.objects.create(name='Sản phẩm cũ', price=100000, old_price=120000)
        for old_price in ('99999', '100000'):
            with self.subTest(old_price=old_price):
                response = self.client.post(reverse('admin_product_update', args=[product.pk]), {
                    'name': 'Sản phẩm đã sửa',
                    'price': '100000',
                    'old_price': old_price,
                })
                self.assertEqual(response.status_code, 200)
                self.assertIn('old_price', response.context['form'].errors)
                product.refresh_from_db()
                self.assertEqual(product.name, 'Sản phẩm cũ')
                self.assertEqual(product.old_price, 120000)
