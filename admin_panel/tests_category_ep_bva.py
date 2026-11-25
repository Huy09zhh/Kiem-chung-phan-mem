"""Unit test EP + BVA cho chức năng quản lý danh mục (sheet PH5_Ân_EP-BVA_DanhMuc).

Biến: độ dài tên danh mục 1..100 ký tự (Category.name: max_length=100, unique=True).
TC-CAT-01 → 08 là các ca có sẵn trong report; TC-CAT-09 → 12 bổ sung cho X2, X3, B2, B4.
Chạy: python manage.py test admin_panel.tests_category_ep_bva -v 2
"""
from django.contrib.auth.models import User
from django.test import Client, TestCase

from products.models import Category

CREATE = '/admin-panel/categories/create/'


class CategoryEpBvaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username='cat_admin', password='Password@123', is_staff=True)

    def setUp(self):
        self.client.force_login(self.admin)

    def _tao(self, name):
        return self.client.post(CREATE, {'name': name})

    def test_tc_cat_01_ten_1_ky_tu_min(self):                # V1, V2, V4, B1
        self.assertEqual(self._tao('R').status_code, 302)
        self.assertTrue(Category.objects.filter(name='R').exists())

    def test_tc_cat_02_ten_nominal(self):                    # V1, V2, V4, B3
        self._tao('Rau Hữu Cơ Sạch')
        self.assertTrue(Category.objects.filter(name='Rau Hữu Cơ Sạch').exists())

    def test_tc_cat_03_ten_100_ky_tu_max(self):              # V1, V2, V4, B5
        self._tao('a' * 100)
        self.assertTrue(Category.objects.filter(name='a' * 100).exists())

    def test_tc_cat_04_ten_rong_min_tru(self):               # X1
        for name in ('', '   '):
            with self.subTest(name=repr(name)):
                self.assertEqual(self._tao(name).status_code, 302)
        self.assertEqual(Category.objects.count(), 0)

    def test_tc_cat_05_sua_ten_hop_le(self):                 # V1, V3, V4
        c = Category.objects.create(name='Rau Củ')
        self.client.post(f'/admin-panel/categories/{c.pk}/edit/', {'name': 'Rau Củ Quả Mới'})
        c.refresh_from_db()
        self.assertEqual(c.name, 'Rau Củ Quả Mới')

    def test_tc_cat_06_sua_id_khong_ton_tai(self):           # X4
        res = self.client.post('/admin-panel/categories/999999/edit/', {'name': 'Test'})
        self.assertEqual(res.status_code, 404)

    def test_tc_cat_07_xoa_hop_le(self):                     # V3, V4
        c = Category.objects.create(name='Tạm')
        self.client.post(f'/admin-panel/categories/{c.pk}/delete/')
        self.assertFalse(Category.objects.filter(pk=c.pk).exists())

    def test_tc_cat_08_khach_chua_dang_nhap(self):           # X5
        res = Client().post(CREATE, {'name': 'Hacker Category'})
        self.assertEqual(res.status_code, 302)
        self.assertIn('login', res['Location'])
        self.assertFalse(Category.objects.filter(name='Hacker Category').exists())

    def test_tc_cat_09_ten_101_ky_tu_max_cong(self):         # X2
        self._tao('b' * 101)
        self.assertFalse(Category.objects.filter(name='b' * 101).exists())

    def test_tc_cat_10_trung_ten(self):                      # X3
        Category.objects.create(name='Trái Cây')
        client = Client(raise_request_exception=False)
        client.force_login(self.admin)
        res = client.post(CREATE, {'name': 'Trái Cây'})
        self.assertNotEqual(res.status_code, 500)
        self.assertEqual(Category.objects.filter(name='Trái Cây').count(), 1)

    def test_tc_cat_11_ten_2_ky_tu_min_cong(self):           # V1, B2
        self._tao('Rb')
        self.assertTrue(Category.objects.filter(name='Rb').exists())

    def test_tc_cat_12_ten_99_ky_tu_max_tru(self):           # V1, B4
        self._tao('c' * 99)
        self.assertTrue(Category.objects.filter(name='c' * 99).exists())
