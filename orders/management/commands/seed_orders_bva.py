"""Tạo dữ liệu mẫu cho bộ test E2E BVA của phân hệ orders bằng CodeceptJS.

Chạy: python manage.py seed_orders_bva
"""
from decimal import Decimal
from allauth.socialaccount.models import SocialApp
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand

from cart.models import Cart, CartItem
from orders.models import ORDER_TOTAL_MAX, Order, OrderItem
from products.models import Product

PASSWORD = 'Order@12345'


class Command(BaseCommand):
    help = 'Tạo tài khoản và giỏ hàng mẫu cho test E2E BVA phân hệ Orders'

    def handle(self, *args, **options):
        # 1. Google OAuth dummy để tránh lỗi 500 trang login
        app, _ = SocialApp.objects.get_or_create(
            provider='google', defaults={'name': 'Google', 'client_id': 'test', 'secret': 'test'})
        if hasattr(app, 'provider_id') and not app.provider_id:
            app.provider_id = 'google'
            app.save()
        app.sites.add(Site.objects.get_current())

        User = get_user_model()

        # 2. Sản phẩm mẫu
        p1, _ = Product.objects.get_or_create(name='SP BVA 1 Dong', defaults={'price': Decimal('1')})
        p1.price = Decimal('1')
        p1.save()

        p2, _ = Product.objects.get_or_create(name='SP BVA 2 Dong', defaults={'price': Decimal('2')})
        p2.price = Decimal('2')
        p2.save()

        p_std, _ = Product.objects.get_or_create(name='SP BVA Tieu Chuan', defaults={'price': Decimal('50000')})
        p_std.price = Decimal('50000')
        p_std.save()

        # Danh sách người dùng cần tạo và gán giỏ hàng tương ứng
        user_configs = [
            # username, product, quantity
            ('order_bva_empty', None, 0),                                # min- = 0đ (giỏ rỗng)
            ('order_bva_min', p1, 1),                                    # min = 1đ
            ('order_bva_min_plus', p2, 1),                               # min+ = 2đ
            ('order_bva_nom', p_std, 2),                                 # nom = 100.000đ
            ('order_bva_max', p1, int(ORDER_TOTAL_MAX)),                 # max = 2.147.483.647đ
            ('order_bva_overflow', p1, int(ORDER_TOTAL_MAX) + 1),        # max+ = 2.147.483.648đ
            ('order_bva_fn_min', p_std, 1),                              # Họ tên min (1 ký tự)
            ('order_bva_fn_max', p_std, 1),                              # Họ tên max (255 ký tự)
            ('order_bva_phone_min', p_std, 1),                           # SĐT min (1 ký tự)
            ('order_bva_phone_max', p_std, 1),                           # SĐT max (20 ký tự)
            ('order_bva_qr', p_std, 1),                                  # Test kênh thanh toán VietQR
            ('order_bva_mock', p_std, 1),                                # Test kênh thanh toán Mock
        ]

        for username, product, qty in user_configs:
            user, _ = User.objects.get_or_create(username=username)
            user.set_password(PASSWORD)
            user.save()
            Cart.objects.filter(user=user).delete()
            cart = Cart.objects.create(user=user)
            if product and qty > 0:
                CartItem.objects.create(cart=cart, product=product, quantity=qty)

        self.stdout.write(self.style.SUCCESS(
            f'Seed thành công {len(user_configs)} tài khoản cho Orders BVA! Mật khẩu chung: {PASSWORD}'
        ))
