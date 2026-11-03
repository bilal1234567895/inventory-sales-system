
from django.contrib import admin
from .models import Product, Sale


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'price', 'quantity')
    search_fields = ('name', 'category')
    list_filter = ('category',)


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'product',
        'quantity_sold',
        'unit_price',
        'total_amount',
        'sold_at'
    )
    list_filter = ('sold_at',)
    search_fields = ('product__name',)
    readonly_fields = (
        'product',
        'quantity_sold',
        'unit_price',
        'total_amount',
        'sold_at'
    )
