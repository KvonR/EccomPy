from django.db import models
from django.contrib.auth.models import User  # Import the User model

class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    image = models.ImageField(upload_to='products/')
    category = models.CharField(max_length=50)

    def __str__(self):
        return self.name

from django.contrib.auth.models import User  # Import the User model

class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # Associate cart with a user
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.user.username}'s Cart: {self.quantity} x {self.product.name}" if self.user else f"{self.quantity} x {self.product.name}"


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # Link the order to the user
    customer_name = models.CharField(max_length=100)  # Optional for non-logged-in orders
    email = models.EmailField()  # Optional for non-logged-in orders
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)  # Total cost of the order
    date = models.DateTimeField(auto_now_add=True)  # Date and time the order was placed

    def __str__(self):
        return f"Order {self.id} - {self.customer_name or self.user.username}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")  # Link to the parent order
    product = models.ForeignKey('Product', on_delete=models.CASCADE)  # Link to the product
    quantity = models.PositiveIntegerField()  # Quantity of the product

    def __str__(self):
        return f"{self.quantity} x {self.product.name} (Order {self.order.id})"