# Green Shop - Website Thương mại điện tử

## Giới thiệu
Website bán sản phẩm tiêu dùng xanh được xây dựng bằng Django.

## Công nghệ sử dụng
- Python Django
- Django REST Framework
- HTML, CSS, Bootstrap
- SQLite

## Chức năng chính
- Hiển thị danh sách sản phẩm
- Xem chi tiết sản phẩm
- Quản lý sản phẩm qua Admin

## Cách chạy project
```bash
git clone https://github.com/vanhieu251206/green_shop.git
cd green_shop
python -m venv .venv
.venv\Scripts\activate
pip install django djangorestframework pillow
python manage.py runserver
```

## Email và quên mật khẩu

Xem [hướng dẫn cấu hình SMTP](docs/SMTP_SETUP.md) để gửi email thật và sử dụng
chức năng quên mật khẩu. File [.env.example](.env.example) chỉ chứa mẫu cấu hình;
mỗi môi trường tạo `.env` riêng và điền thông tin của môi trường đó.

Khi chưa cấu hình SMTP, email được lưu vào `sent_emails/`. Hộp thư dev chỉ dành
cho superuser đang hoạt động khi chạy ở chế độ dev. Không commit `.env`, mật khẩu
ứng dụng hoặc thư đã gửi lên Git.
