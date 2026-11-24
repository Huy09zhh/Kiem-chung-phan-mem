from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from cart.models import Cart, CartItem
from products.models import Product

class Command(BaseCommand):
    help = 'Khởi tạo tài khoản test (khach_test) và dữ liệu mẫu cho Postman Collection FR4'

    def handle(self, *args, **options):
        User = get_user_model()
        for uname, pwd, email in [
            ('khach_test', 'DoiMatKhauCuaBan@123', 'khach_test@example.com'),
            ('test_user_orders', 'TestPass123!', 'test_orders@example.com'),
        ]:
            user, created = User.objects.get_or_create(
                username=uname,
                defaults={'email': email}
            )
            user.set_password(pwd)
            user.is_active = True
            user.save()

            cart, _ = Cart.objects.get_or_create(user=user)
            p, _ = Product.objects.get_or_create(
                id=1,
                defaults={'name': 'Sản phẩm kiểm thử Postman', 'price': Decimal('50000')}
            )
            CartItem.objects.get_or_create(cart=cart, product=p, defaults={'quantity': 1})

        self.stdout.write(self.style.SUCCESS(
            "Đã khởi tạo thành công tài khoản 'khach_test' (pass: 'DoiMatKhauCuaBan@123') và 'test_user_orders' (pass: 'TestPass123!') kèm giỏ hàng!"
        ))
