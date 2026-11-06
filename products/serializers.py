from rest_framework import serializers
from .models import Product

MAX_PRICE = 100000000  # giá bán tối đa 100.000.000 VNĐ


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

    def validate_old_price(self, value):
        if value is not None and value > MAX_PRICE:
            raise serializers.ValidationError(
                'Giá cũ không được vượt quá 100.000.000 VNĐ.'
            )
        return value

    def validate(self, attrs):
        # PATCH có thể chỉ gửi một trong hai giá, nên lấy giá còn lại từ bản ghi hiện có
        price = attrs.get('price', getattr(self.instance, 'price', None))
        old_price = attrs.get('old_price', getattr(self.instance, 'old_price', None))
        if price is not None and old_price is not None and old_price <= price:
            raise serializers.ValidationError(
                {'old_price': 'Giá cũ phải lớn hơn giá bán.'}
            )
        return attrs