"""Unit test EP + BVA cho chức năng thêm sản phẩm.

Mỗi ca ứng với một dòng trong bảng test case của report:
- ProductApiEpBvaTests: sheet PH2_Huy_EP-BVA (TC-PS-021 → 032), thêm qua API POST /products/api/
- ProductAdminFormEpBvaTests: sheet PH5_Ân_EP-BVA_SanPham (TC-CAT-BVA-021 → 032), thêm qua form /admin-panel/products/create/
Chạy: python manage.py test products.tests_ep_bva -v 2
"""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Product

# (mã ca, độ dài tên, giá bán, giá cũ, hợp lệ?)
CASES = [
    ('021', 2, 1000, 50001, True),            # tất cả tại min
    ('022', 3, 1001, 50002, True),            # tất cả tại min+
    ('023', 20, 50000, 70000, True),          # nominal
    ('024', 254, 50000, 99999999, True),      # tên max-, giá cũ max-
    ('025', 20, 99999999, 100000000, True),   # giá bán max-, giá cũ max
    ('026', 255, 100000000, None, True),      # tên max, giá bán max, giá cũ trống
    ('027', 1, 50000, 70000, False),          # tên min-
    ('028', 256, 50000, 70000, False),        # tên max+
    ('029', 20, 999, 70000, False),           # giá bán min-
    ('030', 20, 100000001, 70000, False),     # giá bán max+
    ('031', 20, 50000, 50000, False),         # giá cũ min- (bằng giá bán)
    ('032', 20, 50000, 100000001, False),     # giá cũ max+
]


def ten(n, ma):
    goc = f'SP{ma}'
    return (goc + 'x' * n)[:n]


class ProductApiEpBvaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username='epbva_api_admin', password='Password@123', is_staff=True)

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.admin)

    def _kiem_tra(self, ma):
        _, n, gia, gia_cu, hop_le = next(c for c in CASES if c[0] == ma)
        data = {'name': ten(n, ma), 'price': gia}
        if gia_cu is not None:
            data['old_price'] = gia_cu
        res = self.api.post('/products/api/', data, format='json')
        if hop_le:
            self.assertEqual(res.status_code, 201, res.data)
        else:
            self.assertEqual(res.status_code, 400, res.data)
        self.assertEqual(Product.objects.filter(name=data['name']).exists(), hop_le)

    def test_tc_ps_021(self): self._kiem_tra('021')
    def test_tc_ps_022(self): self._kiem_tra('022')
    def test_tc_ps_023(self): self._kiem_tra('023')
    def test_tc_ps_024(self): self._kiem_tra('024')
    def test_tc_ps_025(self): self._kiem_tra('025')
    def test_tc_ps_026(self): self._kiem_tra('026')
    def test_tc_ps_027(self): self._kiem_tra('027')
    def test_tc_ps_028(self): self._kiem_tra('028')
    def test_tc_ps_029(self): self._kiem_tra('029')
    def test_tc_ps_030(self): self._kiem_tra('030')
    def test_tc_ps_031(self): self._kiem_tra('031')
    def test_tc_ps_032(self): self._kiem_tra('032')


class ProductAdminFormEpBvaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username='epbva_form_admin', password='Password@123', is_staff=True)

    def setUp(self):
        self.client.force_login(self.admin)

    def _kiem_tra(self, ma):
        _, n, gia, gia_cu, hop_le = next(c for c in CASES if c[0] == ma)
        data = {'name': ten(n, ma), 'price': str(gia), 'description': ''}
        if gia_cu is not None:
            data['old_price'] = str(gia_cu)
        res = self.client.post('/admin-panel/products/create/', data)
        if hop_le:
            self.assertEqual(res.status_code, 302)
        else:
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.context['form'].errors)
        self.assertEqual(Product.objects.filter(name=data['name']).exists(), hop_le)

    def test_tc_cat_bva_021(self): self._kiem_tra('021')
    def test_tc_cat_bva_022(self): self._kiem_tra('022')
    def test_tc_cat_bva_023(self): self._kiem_tra('023')
    def test_tc_cat_bva_024(self): self._kiem_tra('024')
    def test_tc_cat_bva_025(self): self._kiem_tra('025')
    def test_tc_cat_bva_026(self): self._kiem_tra('026')
    def test_tc_cat_bva_027(self): self._kiem_tra('027')
    def test_tc_cat_bva_028(self): self._kiem_tra('028')
    def test_tc_cat_bva_029(self): self._kiem_tra('029')
    def test_tc_cat_bva_030(self): self._kiem_tra('030')
    def test_tc_cat_bva_031(self): self._kiem_tra('031')
    def test_tc_cat_bva_032(self): self._kiem_tra('032')
