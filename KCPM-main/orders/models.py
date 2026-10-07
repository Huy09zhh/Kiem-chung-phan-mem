from django.db import models
from django.contrib.auth.models import User


class Order(models.Model):
    PAYMENT_METHOD_CHOICES = (
        ('cod', 'Thanh toán khi nhận hàng'),
        ('qr', 'Chuyển khoản bằng QR'),
        ('mock', 'Thanh toán online mô phỏng'),
    )

    STATUS_CHOICES = (
        ('pending', 'Chờ xử lý'),
        ('awaiting_transfer', 'Chờ chuyển khoản'),
        ('paid', 'Đã thanh toán'),
        ('failed', 'Thanh toán thất bại'),
        ('confirmed', 'Đã xác nhận'),
        ('shipping', 'Đang giao'),
        ('completed', 'Hoàn thành'),
        ('cancelled', 'Đã hủy'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')

    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    note = models.TextField(blank=True, null=True)

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cod'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')

    product_name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return self.product_name