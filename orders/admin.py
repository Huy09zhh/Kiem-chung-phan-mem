from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_name', 'price', 'quantity')
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'full_name',
        'phone',
        'status',
        'payment_method',
        'total_price',
        'created_at'
    )

    list_filter = (
        'status',
        'payment_method',
        'created_at'
    )

    search_fields = (
        'full_name',
        'phone',
        'user__username'
    )

    readonly_fields = (
        'user',
        'total_price',
        'created_at'
    )

    inlines = [OrderItemInline]

    ordering = ['-created_at']


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'order',
        'product_name',
        'price',
        'quantity'
    )

    search_fields = (
        'product_name',
    )