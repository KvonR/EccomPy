from .models import CartItem

def cart_count(request):
    """ Ensure cart count is available on all pages """
    total_cart_quantity = 0
    if request.user.is_authenticated:
        total_cart_quantity = sum(item.quantity for item in CartItem.objects.filter(user=request.user))
    return {"total_cart_quantity": total_cart_quantity}
