from django.test import TestCase
from django.urls import reverse

from .models import Category, Product


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
