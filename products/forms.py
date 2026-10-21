from django import forms
from django.core.exceptions import ValidationError
from .models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'
        labels = {
            'name': 'Tên sản phẩm',
            'category': 'Danh mục',
            'price': 'Giá bán',
            'old_price': 'Giá cũ',
            'description': 'Mô tả',
            'image': 'Ảnh sản phẩm',
            'is_featured': 'Sản phẩm nổi bật',
            'is_flash_sale': 'Flash sale',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'
        self.fields['description'].widget.attrs['rows'] = 4
        self.fields['price'].widget.attrs['min'] = 0
        self.fields['old_price'].widget.attrs['min'] = 0

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price < 0:
            raise ValidationError('Giá phải lớn hơn hoặc bằng 0.')
        return price

    def clean_old_price(self):
        old_price = self.cleaned_data.get('old_price')
        if old_price is not None and old_price < 0:
            raise ValidationError('Giá cũ phải lớn hơn hoặc bằng 0.')
        return old_price