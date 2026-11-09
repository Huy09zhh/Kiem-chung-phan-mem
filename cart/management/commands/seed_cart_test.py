"""Tạo dữ liệu mẫu cho bộ test giỏ hàng bằng CodeceptJS.

Chạy:  python manage.py seed_cart_test
Mỗi lần chạy đưa dữ liệu về trạng thái ban đầu:
  - cart_tester : giỏ trống, dùng cho đa số test case
  - cart_other  : giỏ trống, dùng để kiểm tra giỏ hàng tách biệt theo user
  - cart_fresh  : chưa từng có bản ghi Cart
  - cart_max    : có sẵn "Cart Test Max-1" x 2147483646 và "Cart Test Max" x 2147483647,
                  vì không thể bấm nút "+" 2 tỷ lần trên giao diện
Mật khẩu chung: Cart@12345
"""
from allauth.socialaccount.models import SocialApp
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand

from cart.models import Cart, CartItem
from cart.views import MAX_QUANTITY
from products.models import Product

PASSWORD = 'Cart@12345'
USERNAMES = ('cart_tester', 'cart_other', 'cart_fresh', 'cart_max')
PRODUCTS = {
    'Cart Test A': 50000,
    'Cart Test B': 30000,
    'Cart Test Max-1': 1000,
    'Cart Test Max': 1000,
}


class Command(BaseCommand):
    help = 'Tạo tài khoản và sản phẩm mẫu cho bộ test CodeceptJS của giỏ hàng'

    def handle(self, *args, **options):
        # Database trống (vd. trên CI) thiếu cấu hình Google OAuth nên trang đăng nhập lỗi 500
        app, _ = SocialApp.objects.get_or_create(
            provider='google', defaults={'name': 'Google', 'client_id': 'test', 'secret': 'test'})
        if hasattr(app, 'provider_id') and not app.provider_id:
            app.provider_id = 'google'
            app.save()
        app.sites.add(Site.objects.get_current())

        User = get_user_model()
        users = {}
        for username in USERNAMES:
            user, _ = User.objects.get_or_create(username=username)
            user.set_password(PASSWORD)
            user.save()
            Cart.objects.filter(user=user).delete()
            users[username] = user

        products = {
            name: Product.objects.get_or_create(name=name, defaults={'price': price})[0]
            for name, price in PRODUCTS.items()
        }

        cart = Cart.objects.create(user=users['cart_max'])
        CartItem.objects.create(cart=cart, product=products['Cart Test Max-1'], quantity=MAX_QUANTITY - 1)
        CartItem.objects.create(cart=cart, product=products['Cart Test Max'], quantity=MAX_QUANTITY)

        self.stdout.write(self.style.SUCCESS(
            f'Tài khoản: {", ".join(USERNAMES)} / {PASSWORD}; {len(products)} sản phẩm "Cart Test"'))
