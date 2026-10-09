
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, Q
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST

from products.models import Product, Category
from products.forms import ProductForm
from accounts.decorators import admin_required
from orders.models import Order


# =========================
# DASHBOARD / ANALYTICS
# =========================

@admin_required
def admin_dashboard_view(request):
    orders = Order.objects.all()

    total_orders = orders.count()
    pending_orders = orders.filter(status='pending').count()
    paid_orders = orders.filter(status='paid').count()
    cancelled_orders = orders.filter(status='cancelled').count()

    revenue = (
        orders.filter(
            status__in=['paid', 'confirmed', 'shipping', 'completed']
        ).aggregate(total=Sum('total_price'))['total'] or 0
    )

    context = {
        'total_products': Product.objects.count(),
        'total_users': User.objects.count(),
        'total_featured': Product.objects.filter(
            is_featured=True
        ).count(),
        'total_flash_sale': Product.objects.filter(
            is_flash_sale=True
        ).count(),
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'paid_orders': paid_orders,
        'cancelled_orders': cancelled_orders,
        'revenue': revenue,
        'recent_orders': (
            Order.objects.select_related('user')
            .order_by('-id')[:6]
        ),
    }

    return render(
        request,
        'admin_panel/dashboard.html',
        context
    )


# =========================
# PRODUCT MANAGEMENT
# =========================

@admin_required
def admin_product_list(request):
    products = (
        Product.objects.select_related('category')
        .all()
        .order_by('-id')
    )
    categories = Category.objects.all().order_by('name')

    return render(request, 'admin_panel/products_list.html', {
        'products': products,
        'categories': categories,
    })


@admin_required
def admin_product_create(request):
    form = ProductForm(
        request.POST or None,
        request.FILES or None
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('admin_product_list')

    return render(request, 'admin_panel/product_form.html', {
        'form': form,
        'title': 'Thêm sản phẩm',
    })


@admin_required
def admin_product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(
        request.POST or None,
        request.FILES or None,
        instance=product
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('admin_product_list')

    return render(request, 'admin_panel/product_form.html', {
        'form': form,
        'title': 'Sửa sản phẩm',
    })


@admin_required
def admin_product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        product.delete()
        return redirect('admin_product_list')

    return render(request, 'admin_panel/product_delete.html', {
        'product': product,
    })


# =========================
# CATEGORY MANAGEMENT
# =========================

@admin_required
def admin_category_list(request):
    categories = Category.objects.all().order_by('-id')

    return render(request, 'admin_panel/categories_list.html', {
        'categories': categories,
    })


@admin_required
def admin_category_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()

        if name:
            Category.objects.create(name=name)

    return redirect('admin_category_list')


@admin_required
def admin_category_update(request, pk):
    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()

        if name:
            category.name = name
            category.save(update_fields=['name'])

    return redirect('admin_category_list')


@admin_required
def admin_category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        category.delete()

    return redirect('admin_category_list')


# =========================
# ORDER MANAGEMENT
# =========================

@admin_required
def admin_order_list(request):
    orders = (
        Order.objects.select_related('user')
        .prefetch_related('items')
        .order_by('-id')
    )

    status_filter = request.GET.get('status', '').strip()
    payment_filter = request.GET.get('payment_method', '').strip()
    keyword = request.GET.get('keyword', '').strip()

    if status_filter:
        valid_statuses = {
            value for value, label in Order.STATUS_CHOICES
        }

        if status_filter in valid_statuses:
            orders = orders.filter(status=status_filter)
        else:
            orders = orders.none()

    if payment_filter:
        valid_payment_methods = {
            value for value, label in Order.PAYMENT_METHOD_CHOICES
        }

        if payment_filter in valid_payment_methods:
            orders = orders.filter(payment_method=payment_filter)
        else:
            orders = orders.none()

    if keyword:
        keyword_query = (
            Q(full_name__icontains=keyword)
            | Q(phone__icontains=keyword)
        )

        # Tìm chính xác mã đơn nếu nhập số.
        if keyword.isdigit():
            keyword_query |= Q(pk=int(keyword))

        orders = orders.filter(keyword_query)

    context = {
        'orders': orders,
        'status_filter': status_filter,
        'payment_filter': payment_filter,
        'keyword': keyword,
        'status_choices': Order.STATUS_CHOICES,
        'payment_choices': Order.PAYMENT_METHOD_CHOICES,
    }

    return render(
        request,
        'admin_panel/orders_list.html',
        context
    )


@admin_required
def admin_order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related('user').prefetch_related('items'),
        pk=pk
    )

    return render(
        request,
        'admin_panel/order_detail.html',
        {
            'order': order,
            'status_choices': Order.STATUS_CHOICES,
        }
    )


@admin_required
@require_POST
def admin_order_update_status(request, pk):
    order = get_object_or_404(Order, pk=pk)

    new_status = request.POST.get('status', '').strip()
    valid_statuses = {
        value for value, label in Order.STATUS_CHOICES
    }

    if new_status in valid_statuses:
        order.status = new_status
        order.save(update_fields=['status'])

    next_url = request.POST.get('next', '').strip()

    if next_url == 'detail':
        return redirect('admin_order_detail', pk=order.pk)

    return redirect('admin_order_list')
