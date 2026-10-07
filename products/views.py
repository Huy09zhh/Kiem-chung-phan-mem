from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse
from .models import Product, Category

def product_list(request):
    products = Product.objects.all()

    q = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', '').strip()
    category_id = request.GET.get('category', '').strip()

    if q:
        products = products.filter(name__icontains=q)
    if category_id:
        products = products.filter(category_id=category_id)

    if sort == 'name_asc':
        products = products.order_by('name')
    elif sort == 'name_desc':
        products = products.order_by('-name')
    elif sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    else:
        products = products.order_by('-id')

    categories = Category.objects.all()
    return render(request, 'products/list.html', {
        'products': products,
        'q': q,
        'sort': sort,
        'categories': categories,
        'category_id': category_id,
    })


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'products/detail.html', {
        'product': product
    })

def product_search_suggestions(request):
    q = request.GET.get('q', '').strip()
    results = []

    if q:
        products = Product.objects.filter(name__icontains=q).order_by('name')[:8]
        results = [
            {
                'name': product.name,
                'url': reverse('product_detail', args=[product.pk]),
                'price': f"{int(product.price):,}".replace(',', '.'),
                'image': product.image.url if product.image else '/static/images/default.jpg',
            }
            for product in products
        ]

    return JsonResponse({'results': results})