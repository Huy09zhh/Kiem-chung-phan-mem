from django.core.paginator import Paginator
from django.shortcuts import render
from products.models import Product


def home(request):
    products = Product.objects.all()

    flash_sale_qs = Product.objects.filter(is_flash_sale=True)
    flash_sale_paginator = Paginator(flash_sale_qs, 4)
    flash_sale_page = request.GET.get('flash_page')
    flash_sale_products = flash_sale_paginator.get_page(flash_sale_page)

    featured_qs = Product.objects.filter(is_featured=True)
    featured_paginator = Paginator(featured_qs, 4)
    featured_page = request.GET.get('featured_page')
    featured_products = featured_paginator.get_page(featured_page)

    shop_products_qs = Product.objects.all()
    shop_paginator = Paginator(shop_products_qs, 12)
    shop_page = request.GET.get('page')
    shop_products = shop_paginator.get_page(shop_page)

    context = {
        'products': products,
        'flash_sale_products': flash_sale_products,
        'featured_products': featured_products,
        'shop_products': shop_products,
    }

    return render(request, 'core/home.html', context)