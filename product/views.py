import stripe
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, CartItem
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
# Set Stripe's secret key
stripe.api_key = settings.STRIPE_SECRET_KEY

def home(request):
    featured_products = Product.objects.all()[:3]  # Get the first 3 products as featured
    return render(request, 'home.html', {'featured_products': featured_products})

def product_list(request):
    query = request.GET.get('search', '')
    category = request.GET.get('category', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')

    products = Product.objects.all()

    if query:
        products = products.filter(name__icontains=query) | products.filter(description__icontains=query)
    if category:
        products = products.filter(category__iexact=category)  # Exact match for category
    if min_price:
        products = products.filter(price__gte=min_price)  # Minimum price
    if max_price:
        products = products.filter(price__lte=max_price)  # Maximum price

    return render(request, 'product_list.html', {'products': products, 'query': query, 'category': category, 'min_price': min_price, 'max_price': max_price})

# View the shopping cart
@login_required
def view_cart(request):
    cart_items = CartItem.objects.filter(user=request.user)
    total_amount = sum(item.product.price * item.quantity for item in cart_items)
    return render(request, 'cart.html', {'cart_items': cart_items, 'total_amount': total_amount})



# Add an item to the cart
@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart_item, created = CartItem.objects.get_or_create(user=request.user, product=product)  # Link cart to user
    if not created:
        cart_item.quantity += 1  # Increment quantity if item already exists
    cart_item.save()
    return redirect('view_cart')

# Remove an item from the cart
def remove_from_cart(request, cart_item_id):
    cart_item = get_object_or_404(CartItem, id=cart_item_id)
    cart_item.delete()
    return redirect('view_cart')

@login_required
def checkout(request):
    cart_items = CartItem.objects.filter(user=request.user)
    total_amount = sum(item.product.price * item.quantity for item in cart_items)

    if request.method == "POST":
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': item.product.name,
                        },
                        'unit_amount': int(item.product.price * 100),
                    },
                    'quantity': item.quantity,
                } for item in cart_items
            ],
            mode='payment',
            success_url=request.build_absolute_uri('/products/success/'),
            cancel_url=request.build_absolute_uri('/products/cancel/'),
        )
        return redirect(session.url, code=303)

    return render(request, 'checkout.html', {'cart_items': cart_items, 'total_amount': total_amount})


from .models import Order, OrderItem, CartItem

@login_required
def payment_success(request):
    # Get the cart items for the logged-in user
    cart_items = CartItem.objects.filter(user=request.user)
    total_amount = sum(item.product.price * item.quantity for item in cart_items)

    # Create an order
    order = Order.objects.create(
        user=request.user,
        total_amount=total_amount
    )

    # Save each cart item as an order item
    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity
        )

    # Clear the user's cart
    cart_items.delete()

    return render(request, 'success.html', {'order': order})

def payment_cancel(request):
    return render(request, 'cancel.html')

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-date')  # Get all orders for the user
    return render(request, 'order_history.html', {'orders': orders})

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()  # Save the new user
            return redirect('login')  # Redirect to login page after registration
    else:
        form = UserCreationForm()  # Empty form for GET requests

    return render(request, 'register.html', {'form': form})