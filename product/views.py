import stripe
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, CartItem
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.mail import send_mail

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

    # Calculate total price for each item and store it in a list of dictionaries
    cart_data = []
    total_amount = 0

    for item in cart_items:
        item_total = item.product.price * item.quantity
        total_amount += item_total
        cart_data.append({
            "id": item.id,
            "product": item.product,
            "quantity": item.quantity,
            "item_total": item_total  # This stores the total price per item
        })

    return render(request, "cart.html", {"cart_items": cart_data, "total_amount": total_amount})


from django.http import JsonResponse

@login_required
def update_cart(request):
    if request.method == "POST":
        cart_item_id = request.POST.get("cart_item_id")
        new_quantity = int(request.POST.get("quantity", 1))

        try:
            cart_item = CartItem.objects.get(id=cart_item_id, user=request.user)

            if new_quantity > 0:
                cart_item.quantity = new_quantity
                cart_item.save()
            else:
                cart_item.delete()  # Remove item if quantity is set to 0

            # Ensure total_amount is always a valid number
            total_amount = sum(item.product.price * item.quantity for item in CartItem.objects.filter(user=request.user))
            total_amount = float(total_amount)  # Convert to float just in case

            # Ensure item_total_price is also a valid number
            item_total_price = float(cart_item.product.price * cart_item.quantity) if new_quantity > 0 else 0

            print(f"✅ Cart Updated: Item {cart_item_id} -> New Quantity: {new_quantity}, Total: {total_amount}")

            return JsonResponse({
                "success": True,
                "total_amount": total_amount,
                "item_total_price": item_total_price,
                "cart_item_id": cart_item.id
            })

        except CartItem.DoesNotExist:
            print(f"❌ Error: Cart item {cart_item_id} not found.")
            return JsonResponse({"success": False, "error": "Item not found"}, status=400)

    return JsonResponse({"success": False, "error": "Invalid request"}, status=400)

# Add an item to the cart
from django.http import JsonResponse

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart_item, created = CartItem.objects.get_or_create(user=request.user, product=product)

    if not created:
        cart_item.quantity += 1  # Increment quantity if item already exists
    cart_item.save()

    # Get total quantity of all items in the cart (not just unique items)
    total_cart_quantity = sum(item.quantity for item in CartItem.objects.filter(user=request.user))

    return JsonResponse({
        "success": True,
        "cart_count": total_cart_quantity  # Now reflects total quantity
    })

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
    session_id = request.GET.get('session_id')

    # Debugging: Print session ID
    print(f"Received session ID: {session_id}")

    if not session_id:
        return render(request, 'error.html', {'message': 'Session ID not found'})

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        print(f"Stripe session retrieved: {session}")  # Debugging log
    except stripe.error.InvalidRequestError as e:
        print(f"Stripe session retrieval failed: {e}")
        return render(request, 'error.html', {'message': 'Invalid Stripe session'})

    # ✅ Fix: Get email from customer_details instead of customer_email
    customer_email = session.customer_details.email if session.customer_details else None
    if not customer_email:
        return render(request, 'error.html', {'message': 'Customer email not found in Stripe session'})

    # Get cart items and calculate total amount
    cart_items = CartItem.objects.filter(user=request.user)
    total_amount = sum(item.product.price * item.quantity for item in cart_items)

    # Create an order
    order = Order.objects.create(
        user=request.user,
        total_amount=total_amount
    )

    # Add order items
    order_items_details = ""
    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity
        )
        order_items_details += f"{item.quantity} x {item.product.name} - ${item.product.price * item.quantity}\n"

    # Clear the user's cart
    cart_items.delete()

    # Debugging logs
    print(f"✅ Sending email to: {customer_email}")
    print(f"🛒 Order details:\n{order_items_details}")

    # Send Order Confirmation Email
    subject = "Your Order Confirmation - E-CommercePY"
    message = f"""
    Thank you for your purchase!

    Your Order Details:
    {order_items_details}

    Total Amount: ${total_amount}

    We will notify you once your order is shipped.
    """

    try:
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,  # Ensure this is configured correctly
            [customer_email],  # Use the email from Stripe customer_details
            fail_silently=False,
        )
        print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Email sending failed: {e}")

    return render(request, 'success.html', {'order': order})



def create_checkout_session(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY

    # Calculate the total amount based on cart items
    cart_items = CartItem.objects.filter(user=request.user)
    total_price = sum(item.product.price * item.quantity for item in cart_items) * 100  # Convert to cents

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        customer_creation='always',  # Ensures a customer is always created
        billing_address_collection='required',  # Forces Stripe to collect email
        line_items=[
            {
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': item.product.name,  # Use the actual product name
                    },
                    'unit_amount': int(item.product.price * 100),  # Convert price to cents
                },
                'quantity': item.quantity,  # Ensure quantity is correctly set
            } for item in cart_items  # Loop through all cart items
        ],
        mode='payment',
        success_url=request.build_absolute_uri('/products/success/') + '?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=request.build_absolute_uri('/products/cancel/'),
    )

    return redirect(session.url)

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


from django.core.mail import send_mail
from django.conf import settings


def send_order_confirmation(email, order_details):
    subject = "Your Order Confirmation - E-CommercePY"
    message = f"Thank you for your order!\n\nOrder Details:\n{order_details}\n\nWe will notify you once your order is shipped."

    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [email],
        fail_silently=False,
    )
