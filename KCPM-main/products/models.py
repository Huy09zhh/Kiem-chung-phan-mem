from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=0)
    old_price = models.DecimalField(max_digits=10, decimal_places=0, blank=True, null=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )
    is_featured = models.BooleanField(default=False)
    is_flash_sale = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    @property
    def has_discount(self):
        return self.old_price and self.old_price > self.price

    @property
    def discount_percent(self):
        if self.has_discount:
            return int(round((self.old_price - self.price) * 100 / self.old_price))
        return 0