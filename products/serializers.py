from rest_framework import serializers
from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'price',
            'old_price',
            'image',
            'description',
            'category',
            'is_featured',
            'is_flash_sale',
            'has_discount',
            'discount_percent',
        ]