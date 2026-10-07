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