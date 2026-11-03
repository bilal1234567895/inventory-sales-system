
from django.urls import path
from . import views
from . import purchase_views

urlpatterns = [
    # Product management
    path("", views.product_list, name="product_list"),
    path("products/add/", views.add_product, name="add_product"),
    path("products/<int:product_id>/edit/", views.edit_product, name="edit_product"),
    path("products/<int:product_id>/delete/", views.delete_product, name="delete_product"),

    # Sales management
    path("sales/add/", views.add_sale, name="add_sale"),
    path("sales/history/", views.sales_history, name="sales_history"),
    path("sales/report/", views.sales_report, name="sales_report"),
    path("sales/export/", views.export_sales_csv, name="export_sales_csv"),

    # Dashboard
    path("dashboard/", views.dashboard, name="dashboard"),

    # Restocking
    path("restock/", views.restock_product, name="restock_product"),
    path("restock/history/", views.restock_history, name="restock_history"),

    # Supplier management
    path("suppliers/", views.supplier_list, name="supplier_list"),
    path("suppliers/add/", views.add_supplier, name="add_supplier"),
    path("suppliers/<int:supplier_id>/edit/", views.edit_supplier, name="edit_supplier"),
    path("suppliers/<int:supplier_id>/delete/", views.delete_supplier, name="delete_supplier"),

    # Purchase management
    path("purchases/add/", purchase_views.add_purchase, name="add_purchase"),
    path("purchases/history/", purchase_views.purchase_history, name="purchase_history"),
    path("purchases/report/", purchase_views.purchase_report, name="purchase_report"),
    path("purchases/export/", purchase_views.export_purchase_csv, name="export_purchase_csv"),

    # Low-stock alerts
    path("low-stock/", views.low_stock_products, name="low_stock_products"),
]
