from django.urls import path
from .views import product_list, view_cart, add_to_cart, remove_from_cart, checkout, payment_success, payment_cancel, order_history, register, update_cart, create_checkout_session

urlpatterns = [
    path('', product_list, name='product_list'),
    path('cart/', view_cart, name='view_cart'),
    path('cart/add/<int:product_id>/', add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:cart_item_id>/', remove_from_cart, name='remove_from_cart'),
    path('checkout/', checkout, name='checkout'),
    path('success/', payment_success, name='payment_success'),  # Add success URL
    path('cancel/', payment_cancel, name='payment_cancel'),  # Add cancel URL
    path('orders/', order_history, name='order_history'),
    path('register/', register, name='register'),
    path('create-checkout-session/', create_checkout_session, name='create_checkout_session'),
    path('cart/', view_cart, name='view_cart'),
    path('cart/update/', update_cart, name='update_cart'),  # AJAX update route
]