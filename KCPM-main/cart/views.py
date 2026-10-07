from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required

from products.models import Product
from .models import Cart, CartItem


def get_user_cart(user):
    cart, created = Cart.objects.get_or_create(user=user)
    return cart


def cart_add(request, product_id):
    if not request.user.is_authenticated:
        return redirect(f"/accounts/login/?next=/cart/add/{product_id}/")

    product = get_object_or_404(Product, id=product_id)
    cart = get_user_cart(request.user)

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
    )

    if not created:
        cart_item.quantity += 1
        cart_item.save()

    return redirect('cart_detail')


@login_required(login_url='login')
def cart_remove(request, product_id):
    cart = get_user_cart(request.user)
    product = get_object_or_404(Product, id=product_id)

    CartItem.objects.filter(cart=cart, product=product).delete()
    return redirect('cart_detail')


@login_required(login_url='login')
def cart_increase(request, product_id):
    cart = get_user_cart(request.user)
    product = get_object_or_404(Product, id=product_id)

    cart_item = get_object_or_404(CartItem, cart=cart, product=product)
    cart_item.quantity += 1
    cart_item.save()

    return redirect('cart_detail')


@login_required(login_url='login')
def cart_decrease(request, product_id):
    cart = get_user_cart(request.user)
    product = get_object_or_404(Product, id=product_id)

    cart_item = get_object_or_404(CartItem, cart=cart, product=product)
    cart_item.quantity -= 1

    if cart_item.quantity <= 0:
        cart_item.delete()
    else:
        cart_item.save()

    return redirect('cart_detail')


@login_required(login_url='login')
def cart_detail(request):
    cart = get_user_cart(request.user)
    cart_items = cart.items.select_related('product')
    total_price = sum(item.product.price * item.quantity for item in cart_items)

    return render(request, 'cart/detail.html', {
        'cart_items': cart_items,
        'total_price': total_price,
    })