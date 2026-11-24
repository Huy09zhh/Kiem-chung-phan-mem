"""Dữ liệu test chung cho toàn bộ Postman collection của nhóm.

Chỉ chạy trên database MỚI (vừa migrate, chưa có sản phẩm/đơn hàng). postman/run_all.py tự làm việc này:
dựng DB mới -> chạy file này -> dùng bản DB đó làm mẫu, chép lại trước mỗi lượt chạy.

Chạy tay (trên DB trống):
    python manage.py shell -c "exec(open('postman/seed_full.py', encoding='utf-8').read())"

Mã đơn và sản phẩm khớp với biến trong các collection, sửa ở đây thì phải sửa biến tương ứng:
  Sản phẩm #1 "Cây Sen Đá Mini"  : PH2 (TC-PS-006, 009), PH4 product_id, PH5 product_id
  Danh mục #1                    : PH5 category_id
  Đơn #1  Hoàn thành, SĐT 0912345678 : PH6 order_id, final_order_id, phone_known
  Đơn #2  Hoàn thành, QR, Tran Thi B : PH6 search_order_id, detail_order_id
  Đơn #3  Đã hủy                     : PH6 cancelled_order_id
  Đơn #8  Chờ xử lý                  : PH6 status_order_id, flow_order_id
  Đơn #9  Đã thanh toán              : PH6 paid_order_id
  Đơn #10 Chờ xử lý                  : PH6 cancel_order_id
  Đơn #11 Chờ chuyển khoản (QR)      : PH6 qr_order_id
  Đơn #12 tên có dấu "Nguyễn ..."    : PH6 accent_name_proper
  Đơn #18 Chờ xử lý, #19 Đã thanh toán : PH6 perm_order_id, reject_order_id
"""
from decimal import Decimal

from allauth.socialaccount.models import SocialApp
from django.contrib.auth.models import User
from django.contrib.sites.models import Site

from orders.models import Order, OrderItem
from products.models import Category, Product

if Product.objects.exists() or Order.objects.exists():
    raise SystemExit('DB đã có dữ liệu. seed_full.py chỉ dành cho DB mới (run_all.py tự dựng DB riêng).')

# ---- tài khoản (giống postman/seed_test_data.py)
User.objects.create_superuser('admin', 'admin@example.com', 'Admin@12345')
user1 = User.objects.create_user('user1', 'user1@example.com', 'User@12345', first_name='Nguyen', last_name='Van A')
User.objects.create_user('user2', 'user2@example.com', 'User@12345')

# ---- đăng nhập Google: thiếu SocialApp thì trang đăng nhập lỗi 500 (SCRUM-10)
app = SocialApp.objects.create(provider='google', name='Google (test)', client_id='test', secret='test')
app.sites.add(Site.objects.get_current())

# ---- danh mục, sản phẩm. Sản phẩm #1 phải là "Cây Sen Đá Mini"
cay = Category.objects.create(name='Cây cảnh')
PRODUCTS = [
    # tên, giá, giá cũ, nổi bật, flash sale
    ('Cây Sen Đá Mini', 45000, 60000, True, True),
    ('Cây Lưỡi Hổ', 120000, None, True, False),
    ('Cây Kim Tiền', 150000, 180000, False, True),
    ('Cây Trầu Bà', 65000, None, False, False),
    ('Chậu Gốm Trắng', 35000, None, False, False),
    ('Bình Tưới Mini', 25000, 30000, False, True),
]
for name, price, old_price, featured, flash in PRODUCTS:
    Product.objects.create(name=name, price=price, old_price=old_price, category=cay,
                           description=f'{name} - sản phẩm mẫu để kiểm thử.',
                           is_featured=featured, is_flash_sale=flash)

# dữ liệu của seed_test_data.py (Phong): 2 danh mục, 3 sản phẩm, dùng get_or_create nên không trùng
exec(open('postman/seed_test_data.py', encoding='utf-8').read())

# ---- đơn hàng, tạo đúng thứ tự để có mã 1 -> 20
ORDERS = [
    # mã, trạng thái, thanh toán, họ tên, SĐT
    (1, 'completed', 'cod', 'Nguyen Van A', '0912345678'),
    (2, 'completed', 'qr', 'Tran Thi B', '0987654321'),
    (3, 'cancelled', 'cod', 'Le Van C', '0901234567'),
    (4, 'shipping', 'cod', 'Pham Thi D', '0934567890'),
    (5, 'confirmed', 'cod', 'Hoang Van E', '0945678901'),
    (6, 'paid', 'qr', 'Vo Thi F', '0956789012'),
    (7, 'awaiting_transfer', 'qr', 'Dang Van G', '0967890123'),
    (8, 'pending', 'cod', 'Nguyen Quan', '0978901234'),
    (9, 'paid', 'qr', 'Bui Thi H', '0989012345'),
    (10, 'pending', 'cod', 'Do Van I', '0990123456'),
    (11, 'awaiting_transfer', 'qr', 'Ngo Thi K', '0911223344'),
    (12, 'pending', 'cod', 'Nguyễn Văn An', '0922334455'),
    (13, 'failed', 'mock', 'Ly Van L', '0933445566'),
    (14, 'completed', 'mock', 'Mai Thi M', '0944556677'),
    (15, 'cancelled', 'qr', 'Trinh Van N', '0955667788'),
    (16, 'pending', 'cod', 'Cao Thi O', '0966778899'),
    (17, 'confirmed', 'qr', 'Duong Van P', '0977889900'),
    (18, 'pending', 'cod', 'Ha Thi Q', '0988990011'),
    (19, 'paid', 'cod', 'Lam Van R', '0999001122'),
    (20, 'completed', 'cod', 'Ta Thi S', '0910112233'),
]
products = list(Product.objects.order_by('id')[:4])
for pk, status, method, name, phone in ORDERS:
    p1, p2 = products[pk % 4], products[(pk + 1) % 4]
    items = [(p1, 1 + pk % 3), (p2, 1)]
    total = sum(Decimal(p.price) * q for p, q in items)
    order = Order.objects.create(pk=pk, user=user1, full_name=name, phone=phone,
                                 address=f'{pk} Đường Kiểm Thử, TP.HCM', payment_method=method,
                                 status=status, total_price=total)
    for p, q in items:
        OrderItem.objects.create(order=order, product_name=p.name, price=p.price, quantity=q)

print('seed_full: users', User.objects.count(), '| products', Product.objects.count(),
      '| orders', Order.objects.count())
