"""Tạo dữ liệu mẫu cho test BVA tìm kiếm đơn hàng bằng CodeceptJS.

Chạy:  python manage.py seed_bva_orders
Tạo (nếu chưa có):
  - cấu hình Google OAuth giả (để trang đăng nhập render được trên DB trống)
  - tài khoản quản trị  bva_admin / Bva@12345
  - một đơn "BVA Seed" có SĐT 0912345678 (10 ký tự)
  - một đơn "Nguyen Van BVA" thanh toán QR, trạng thái Đã thanh toán (cho test bảng quyết định)
"""
from allauth.socialaccount.models import SocialApp
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand

from orders.models import Order

ADMIN_USERNAME = 'bva_admin'
ADMIN_PASSWORD = 'Bva@12345'
SEED_NAME = 'BVA Seed'
SEED_PHONE = '0912345678'


class Command(BaseCommand):
    help = 'Tạo tài khoản admin và đơn mẫu cho bộ test BVA tìm kiếm đơn hàng'

    def handle(self, *args, **options):
        # Database trống (vd. trên CI) thiếu cấu hình Google OAuth nên trang đăng nhập lỗi 500
        app, _ = SocialApp.objects.get_or_create(
            provider='google', defaults={'name': 'Google', 'client_id': 'test', 'secret': 'test'})
        # django-allauth bản mới tìm app theo provider_id, để trống thì get_app báo SocialApp.DoesNotExist
        if hasattr(app, 'provider_id') and not app.provider_id:
            app.provider_id = 'google'
            app.save()
        app.sites.add(Site.objects.get_current())

        User = get_user_model()
        admin, created = User.objects.get_or_create(username=ADMIN_USERNAME, defaults={'is_staff': True})
        if created or not admin.is_staff:
            admin.is_staff = True
        admin.set_password(ADMIN_PASSWORD)
        admin.save()

        # Dùng filter().first() thay vì get_or_create: các bộ Postman cũng tạo đơn trùng tên/SĐT,
        # get_or_create sẽ báo MultipleObjectsReturned khi có hơn 1 đơn khớp.
        order = Order.objects.filter(full_name=SEED_NAME, phone=SEED_PHONE).order_by('pk').first()
        order_created = order is None
        if order_created:
            order = Order.objects.create(
                full_name=SEED_NAME, phone=SEED_PHONE,
                user=admin, address='1 Duong BVA', total_price=100000,
            )
        # Test bảng quyết định cần ít nhất 1 đơn "Nguyen Van BVA" thanh toán QR, Đã thanh toán
        if not Order.objects.filter(full_name='Nguyen Van BVA', phone='0987654321',
                                    payment_method='qr', status='paid').exists():
            Order.objects.create(
                full_name='Nguyen Van BVA', phone='0987654321',
                user=admin, address='2 Duong BVA', total_price=50000,
                payment_method='qr', status='paid',
            )
        self.stdout.write(self.style.SUCCESS(
            f'Admin: {ADMIN_USERNAME} / {ADMIN_PASSWORD}; đơn mẫu #{order.pk} '
            f'({"mới tạo" if order_created else "đã có"}), SĐT {SEED_PHONE}'))