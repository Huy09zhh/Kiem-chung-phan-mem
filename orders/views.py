from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from urllib.parse import quote

from .models import Order, OrderItem
from cart.models import Cart


def get_qr_info(order):
    bank_name = getattr(settings, 'BANK_QR_NAME', 'MB Bank')
    bank_id = getattr(settings, 'BANK_QR_BANK_ID', 'mbbank')
    account_name = getattr(settings, 'BANK_QR_ACCOUNT_NAME', 'GREEN SHOP')
    account_number = getattr(settings, 'BANK_QR_ACCOUNT_NUMBER', '0123456789')

    amount = int(order.total_price)
    transfer_note = f"THANH TOAN DH{order.id}"

    qr_image_url = (
        f"https://img.vietqr.io/image/{bank_id}-{account_number}-compact2.png"
        f"?amount={amount}"
        f"&addInfo={quote(transfer_note)}"
        f"&accountName={quote(account_name)}"
    )

    return {
        'bank_name': bank_name,
        'bank_id': bank_id,
        'account_name': account_name,
        'account_number': account_number,
        'amount': order.total_price,
        'transfer_note': transfer_note,
        'qr_image_url': qr_image_url,
    }


@login_required(login_url='login')
def checkout(request):
    try:
        cart = request.user.cart
    except Cart.DoesNotExist:
        return redirect('cart_detail')

    cart_items = cart.items.select_related('product')

    if not cart_items.exists():
        return redirect('cart_detail')

    total_price = sum(item.product.price * item.quantity for item in cart_items)

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        note = request.POST.get('note', '').strip()
        payment_method = request.POST.get('payment_method', 'cod')

        if payment_method not in ['cod', 'qr', 'mock']:
            payment_method = 'cod'

        order_status = 'pending'
        if payment_method == 'qr':
            order_status = 'awaiting_transfer'
        elif payment_method == 'mock':
            order_status = 'pending'

        order = Order.objects.create(
            user=request.user,
            total_price=total_price,
            full_name=full_name,
            phone=phone,
            address=address,
            note=note,
            payment_method=payment_method,
            status=order_status,
        )

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product_name=item.product.name,
                price=item.product.price,
                quantity=item.quantity,
            )

        if payment_method == 'cod':
            cart.items.all().delete()
            return redirect('orders:order_success', order_id=order.id)

        if payment_method == 'qr':
            cart.items.all().delete()
            return redirect('orders:order_qr', order_id=order.id)

        return redirect('orders:mock_payment', order_id=order.id)

    return render(request, 'orders/checkout.html', {
        'cart_items': cart_items,
        'total_price': total_price,
    })


@login_required(login_url='login')
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'orders/success.html', {
        'order': order,
    })


@login_required(login_url='login')
def order_qr(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    qr_info = get_qr_info(order)

    return render(request, 'orders/qr_payment.html', {
        'order': order,
        'qr_info': qr_info,
    })


@login_required(login_url='login')
def confirm_qr_paid(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if request.method == 'POST':
        order.status = 'paid'
        order.save(update_fields=['status'])

    return redirect('orders:order_success', order_id=order.id)


@login_required(login_url='login')
def mock_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'orders/mock_payment.html', {
        'order': order,
    })


@login_required(login_url='login')
def mock_payment_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order.status = 'paid'
    order.save(update_fields=['status'])

    try:
        cart = request.user.cart
        cart.items.all().delete()
    except Cart.DoesNotExist:
        pass

    return redirect('orders:order_success', order_id=order.id)


@login_required(login_url='login')
def mock_payment_fail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order.status = 'failed'
    order.save(update_fields=['status'])

    return redirect('orders:order_success', order_id=order.id)