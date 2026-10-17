"""Tạo dữ liệu tối thiểu để chạy collection GreenShop-BugRegression.

Chạy từ thư mục Kiem-chung-phan-mem:
    python manage.py shell -c "exec(open('postman/seed_test_data.py', encoding='utf-8').read())"
"""
from django.contrib.auth.models import User
from products.models import Product, Category

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'Admin@12345')
for username in ('user1', 'user2'):
    if not User.objects.filter(username=username).exists():
        User.objects.create_user(username, f'{username}@example.com', 'User@12345')

rau, _ = Category.objects.get_or_create(name='Rau cu')
qua, _ = Category.objects.get_or_create(name='Trai cay')
for name, price, old_price, category in [
    ('Ca rot', 25000, 30000, rau),
    ('Bap cai', 18000, None, rau),
    ('Tao My', 85000, 99000, qua),
]:
    Product.objects.get_or_create(
        name=name,
        defaults=dict(price=price, old_price=old_price, category=category, is_featured=True),
    )

print('Users:', list(User.objects.values_list('username', flat=True)))
print('Products:', Product.objects.count(), '| Categories:', Category.objects.count())
