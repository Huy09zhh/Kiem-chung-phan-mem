"""
Unit test Dashboard quản trị (phân hệ 6: Admin Orders & Analytics).

Test case trong report (sheet Tuần 4, mục III):
  TC-BVA-012  Cơ cấu đơn hàng (%) khi hệ thống chưa có đơn nào (biên min, tránh chia cho 0)
  TC-BVA-013  Bảng "Đơn mới nhất" tối đa 6 đơn: thử 5 / 6 / 7 đơn (max-1 / max / max+1)

Chạy:  python manage.py test admin_panel.tests_dashboard -v 2
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from orders.models import Order


class DashboardBVATests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user('db_admin', password='pw-12345', is_staff=True)
        cls.customer = User.objects.create_user('db_customer', password='pw-12345')

    def setUp(self):
        self.client.force_login(self.admin)

    def make_orders(self, n, status='pending'):
        for i in range(n):
            Order.objects.create(
                user=self.customer, full_name=f'Khach {i}', phone='0912345678',
                address='1 Duong Test', total_price=100000, status=status,
                payment_method='cod',
            )

    def get_dashboard(self):
        return self.client.get(reverse('admin_dashboard'))

    def test_bva_012_khong_co_don_khong_loi_chia_0(self):
        """TC-BVA-012: 0 đơn -> trang mở bình thường, không tính phần trăm (không chia cho 0)."""
        response = self.get_dashboard()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_orders'], 0)
        self.assertContains(response, 'Chưa có đơn hàng nào để thống kê.')
        self.assertContains(response, 'Chưa có đơn hàng nào.')

    def test_bva_012_co_don_thi_hien_phan_tram(self):
        """Đối chứng cho TC-BVA-012: có 1 đơn chờ xử lý -> hiện 100%."""
        self.make_orders(1)
        response = self.get_dashboard()
        self.assertContains(response, '1 đơn (100%)')

    def test_bva_013_don_moi_nhat_toi_da_6(self):
        """TC-BVA-013: 5 / 6 / 7 đơn -> bảng đơn mới nhất hiện 5 / 6 / 6 đơn."""
        for total, expected in ((5, 5), (6, 6), (7, 6)):
            with self.subTest(total=total):
                Order.objects.all().delete()
                self.make_orders(total)
                response = self.get_dashboard()
                recent = list(response.context['recent_orders'])
                self.assertEqual(len(recent), expected)
                newest_ids = list(Order.objects.order_by('-id').values_list('id', flat=True)[:expected])
                self.assertEqual([o.id for o in recent], newest_ids)
