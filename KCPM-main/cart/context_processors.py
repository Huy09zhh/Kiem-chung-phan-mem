from .models import Cart

def cart_item_count(request):
    if request.user.is_authenticated:
        try:
            return {
                'cart_item_count': sum(item.quantity for item in request.user.cart.items.all())
            }
        except Cart.DoesNotExist:
            return {'cart_item_count': 0}
    return {'cart_item_count': 0}