"""Tạo dữ liệu mẫu cho test BVA tìm kiếm đơn hàng bằng CodeceptJS.

Chạy:  python manage.py seed_bva_orders
Tạo (nếu chưa có):
  - tài khoản quản trị  bva_admin / Bva@12345
  - một đơn "BVA Seed" có SĐT 0912345678 (10 ký tự)
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from orders.models import Order

ADMIN_USERNAME = 'bva_admin'
ADMIN_PASSWORD = 'Bva@12345'
SEED_NAME = 'BVA Seed'
SEED_PHONE = '0912345678'


class Command(BaseCommand):
    help = 'Tạo tài khoản admin và đơn mẫu cho bộ test BVA tìm kiếm đơn hàng'

    def handle(self, *args, **options):
        User = get_user_model()
        admin, created = User.objects.get_or_create(username=ADMIN_USERNAME, defaults={'is_staff': True})
        if created or not admin.is_staff:
            admin.is_staff = True
        admin.set_password(ADMIN_PASSWORD)
        admin.save()

        order, order_created = Order.objects.get_or_create(
            full_name=SEED_NAME, phone=SEED_PHONE,
            defaults={'user': admin, 'address': '1 Duong BVA', 'total_price': 100000},
        )
        self.stdout.write(self.style.SUCCESS(
            f'Admin: {ADMIN_USERNAME} / {ADMIN_PASSWORD}; đơn mẫu #{order.pk} '
            f'({"mới tạo" if order_created else "đã có"}), SĐT {SEED_PHONE}'))
