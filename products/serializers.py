from rest_framework import serializers
from .models import Product

MAX_PRICE = 100000000


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

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError(
                'Tên sản phẩm phải có độ dài tối thiểu 2 ký tự trở lên.'
            )
        return value

    def validate_price(self, value):
        if value > MAX_PRICE:
            raise serializers.ValidationError(
                'Giá bán không được vượt quá 100.000.000 VNĐ.'
            )
        return value