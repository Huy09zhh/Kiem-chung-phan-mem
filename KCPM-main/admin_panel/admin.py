from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from products.models import Category
from django.db.models import Sum

from accounts.decorators import admin_required
from products.models import Product
from products.forms import ProductForm


@admin_required
def admin_dashboard_view(request):
    products = Product.objects.select_related('category').order_by('-id')[:5]

    total_products = Product.objects.count()
    total_featured = Product.objects.filter(is_featured=True).count()
    total_flash_sale = Product.objects.filter(is_flash_sale=True).count()
    total_users = User.objects.count()

    total_stock_value = Product.objects.aggregate(total=Sum('price'))['total'] or 0

    context = {
        'total_products': total_products,
        'total_featured': total_featured,
        'total_flash_sale': total_flash_sale,
        'total_users': total_users,
        'total_stock_value': total_stock_value,
        'products': products,
    }
    return render(request, 'admin_panel/dashboard.html', context)


@admin_required
def admin_product_list(request):
    products = Product.objects.all().order_by('-id')
    return render(request, 'admin_panel/products_list.html', {
        'products': products,
        'categories': Category.objects.all()
    })


@admin_required
def admin_product_create(request):
    form = ProductForm(request.POST or None, request.FILES or None)

    if form.is_valid():
        form.save()
        return redirect('admin_product_list')

    return render(request, 'admin_panel/product_form.html', {
        'form': form,
        'title': 'Thêm sản phẩm'
    })


@admin_required
def admin_product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)

    if form.is_valid():
        form.save()
        return redirect('admin_product_list')

    return render(request, 'admin_panel/product_form.html', {
        'form': form,
        'title': 'Sửa sản phẩm'
    })


@admin_required
def admin_product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        product.delete()
        return redirect('admin_product_list')

    return render(request, 'admin_panel/product_delete.html', {
        'product': product
    })