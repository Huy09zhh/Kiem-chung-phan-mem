from django.db import models


class ContactMessage(models.Model):
    SUBJECT_CHOICES = [
        ('tu_van', 'Tư vấn sản phẩm'),
        ('don_hang', 'Hỗ trợ đơn hàng'),
        ('hop_tac', 'Hợp tác / đối tác'),
        ('khieu_nai', 'Khiếu nại / góp ý'),
        ('khac', 'Khác'),
    ]

    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=20, choices=SUBJECT_CHOICES, default='tu_van')
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Liên hệ'
        verbose_name_plural = 'Liên hệ'

    def __str__(self):
        return f"{self.name} - {self.get_subject_display()}"


class Feedback(models.Model):
    CATEGORY_CHOICES = [
        ('website', 'Giao diện website'),
        ('san_pham', 'Chất lượng sản phẩm'),
        ('giao_hang', 'Tốc độ giao hàng'),
        ('ho_tro', 'Dịch vụ hỗ trợ'),
        ('tong_the', 'Trải nghiệm tổng thể'),
    ]

    SATISFACTION_CHOICES = [
        ('5', 'Rất hài lòng'),
        ('4', 'Hài lòng'),
        ('3', 'Bình thường'),
        ('2', 'Chưa hài lòng'),
        ('1', 'Rất không hài lòng'),
    ]

    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='tong_the')
    satisfaction = models.CharField(max_length=1, choices=SATISFACTION_CHOICES, default='5')
    message = models.TextField()
    is_reviewed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Phản hồi'
        verbose_name_plural = 'Phản hồi'

    def __str__(self):
        return f"{self.name} - {self.get_category_display()}"