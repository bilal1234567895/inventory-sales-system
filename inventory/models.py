
from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Sale(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="sales"
    )
    quantity_sold = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    sold_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} - Sale #{self.id}"


class Supplier(models.Model):
    company_name = models.CharField(max_length=150)
    contact_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name


class Restock(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="restocks"
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="restocks"
    )
    quantity_added = models.PositiveIntegerField()
    notes = models.CharField(max_length=255, blank=True)
    restocked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} - Restocked {self.quantity_added}"


class Purchase(models.Model):
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="purchases"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="purchases"
    )
    quantity_purchased = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.CharField(max_length=255, blank=True)
    purchased_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Purchase #{self.id} - {self.product.name}"
