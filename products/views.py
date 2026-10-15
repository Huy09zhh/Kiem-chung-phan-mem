from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse
from .models import Product, Category

from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import ProductSerializer


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
        products = Product.objects.filter(
            name__icontains=q
        ).order_by('name')[:8]

        results = [
            {
                'name': product.name,
                'url': reverse('product_detail', args=[product.pk]),
                'price': f"{int(product.price):,}".replace(',', '.'),
                'image': product.image.url
                if product.image
                else '/static/images/default.jpg',
            }
            for product in products
        ]

    return JsonResponse({'results': results})


@api_view(['GET', 'POST'])
def product_api_list(request):
    if request.method == 'GET':
        products = Product.objects.all()
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)

    serializer = ProductSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)

    return Response(serializer.errors, status=400)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def product_api_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'GET':
        serializer = ProductSerializer(product)
        return Response(serializer.data)

    if request.method == 'DELETE':
        product.delete()
        return Response(status=204)

    if request.method == 'PUT':
        serializer = ProductSerializer(product, data=request.data)
    else:
        serializer = ProductSerializer(
            product,
            data=request.data,
            partial=True
        )

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)

    return Response(serializer.errors, status=400)