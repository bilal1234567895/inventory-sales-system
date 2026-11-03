
import csv
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, Count, F
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .models import Product, Sale, Restock, Supplier


@login_required
def product_list(request):
    search_query = request.GET.get("search", "").strip()
    selected_category = request.GET.get("category", "").strip()

    products = Product.objects.all().order_by("id")

    if search_query:
        products = products.filter(name__icontains=search_query)

    if selected_category:
        products = products.filter(category=selected_category)

    categories = (
        Product.objects.order_by("category")
        .values_list("category", flat=True)
        .distinct()
    )

    return render(request, "inventory/product_list.html", {
        "products": products,
        "categories": categories,
        "search_query": search_query,
        "selected_category": selected_category,
    })


@login_required
def add_product(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        category = request.POST.get("category", "").strip()
        price = request.POST.get("price", "").strip()
        quantity = request.POST.get("quantity", "").strip()
        description = request.POST.get("description", "").strip()

        if not name or not category or not price or not quantity:
            messages.error(request, "Please fill in all required fields.")
            return render(request, "inventory/add_product.html")

        try:
            price_value = Decimal(price)
            quantity_value = int(quantity)

            if (
                not price_value.is_finite()
                or price_value < 0
                or quantity_value < 0
            ):
                raise ValueError
        except (ValueError, ArithmeticError):
            messages.error(
                request,
                "Enter a valid non-negative price and quantity."
            )
            return render(request, "inventory/add_product.html")

        Product.objects.create(
            name=name,
            category=category,
            price=price_value,
            quantity=quantity_value,
            description=description,
        )
        messages.success(request, "Product added successfully.")
        return redirect("product_list")

    return render(request, "inventory/add_product.html")


@login_required
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        category = request.POST.get("category", "").strip()
        price = request.POST.get("price", "").strip()
        quantity = request.POST.get("quantity", "").strip()
        description = request.POST.get("description", "").strip()

        if not name or not category or not price or not quantity:
            messages.error(request, "Please fill in all required fields.")
            return render(
                request, "inventory/edit_product.html",
                {"product": product}
            )

        try:
            price_value = Decimal(price)
            quantity_value = int(quantity)

            if (
                not price_value.is_finite()
                or price_value < 0
                or quantity_value < 0
            ):
                raise ValueError
        except (ValueError, ArithmeticError):
            messages.error(
                request,
                "Enter a valid non-negative price and quantity."
            )
            return render(
                request, "inventory/edit_product.html",
                {"product": product}
            )

        product.name = name
        product.category = category
        product.price = price_value
        product.quantity = quantity_value
        product.description = description
        product.save()

        messages.success(request, "Product updated successfully.")
        return redirect("product_list")

    return render(
        request, "inventory/edit_product.html", {"product": product}
    )


@login_required
def delete_product(request, product_id):
    if request.method != "POST":
        return redirect("product_list")

    product = get_object_or_404(Product, id=product_id)

    try:
        product.delete()
        messages.success(request, "Product deleted successfully.")
    except ProtectedError:
        messages.error(
            request,
            "This product has sales or restock records and cannot be deleted."
        )

    return redirect("product_list")


@login_required
def add_sale(request):
    products = Product.objects.filter(quantity__gt=0).order_by("name")

    if request.method == "POST":
        product_id = request.POST.get("product")
        quantity_text = request.POST.get("quantity_sold", "").strip()

        try:
            quantity_sold = int(quantity_text)
            if quantity_sold <= 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(
                request, "Enter a valid quantity greater than zero."
            )
            return render(
                request, "inventory/add_sale.html", {"products": products}
            )

        with transaction.atomic():
            product = get_object_or_404(
                Product.objects.select_for_update(), id=product_id
            )

            if product.quantity < quantity_sold:
                messages.error(
                    request,
                    f"Insufficient stock. Available quantity: {product.quantity}."
                )
                return render(
                    request, "inventory/add_sale.html",
                    {"products": products}
                )

            unit_price = product.price
            total_amount = unit_price * quantity_sold
            product.quantity -= quantity_sold
            product.save(update_fields=["quantity"])

            Sale.objects.create(
                product=product,
                quantity_sold=quantity_sold,
                unit_price=unit_price,
                total_amount=total_amount,
            )

        messages.success(request, "Sale recorded successfully.")
        return redirect("sales_history")

    return render(
        request, "inventory/add_sale.html", {"products": products}
    )


@login_required
def sales_history(request):
    sales = Sale.objects.select_related("product").order_by("-sold_at")
    summary = sales.aggregate(
        revenue=Sum("total_amount"),
        transactions=Count("id"),
        items_sold=Sum("quantity_sold"),
    )

    return render(request, "inventory/sales_history.html", {
        "sales": sales,
        "total_revenue": summary["revenue"] or Decimal("0.00"),
        "total_transactions": summary["transactions"] or 0,
        "total_items_sold": summary["items_sold"] or 0,
    })


@login_required

@login_required
def dashboard(request):
    total_products = Product.objects.count()

    total_stock = Product.objects.aggregate(
        total=Sum("quantity")
    )["total"] or 0

    stock_value = Product.objects.aggregate(
        total=Sum(F("price") * F("quantity"))
    )["total"] or Decimal("0.00")

    sales_summary = Sale.objects.aggregate(
        revenue=Sum("total_amount"),
        transactions=Count("id"),
        items_sold=Sum("quantity_sold"),
    )

    # Products with 5 or fewer units
    low_stock_products = Product.objects.filter(
        quantity__lte=5
    ).order_by("quantity", "name")

    # Products with zero units
    out_of_stock_count = Product.objects.filter(
        quantity=0
    ).count()

    # Products with 1 to 5 units
    low_stock_count = Product.objects.filter(
        quantity__gt=0,
        quantity__lte=5
    ).count()

    return render(request, "inventory/dashboard.html", {
        "total_products": total_products,
        "total_stock": total_stock,
        "stock_value": stock_value,
        "total_revenue": sales_summary["revenue"] or Decimal("0.00"),
        "total_sales": sales_summary["transactions"] or 0,
        "total_transactions": sales_summary["transactions"] or 0,
        "total_items_sold": sales_summary["items_sold"] or 0,
        "low_stock_products": low_stock_products,
        "out_of_stock_count": out_of_stock_count,
        "low_stock_count": low_stock_count,
    })


@login_required
def sales_report(request):
    start_date_text = request.GET.get("start_date", "").strip()
    end_date_text = request.GET.get("end_date", "").strip()
    sales = Sale.objects.select_related("product").all()
    errors = []
    start_date = None
    end_date = None

    if start_date_text:
        try:
            start_date = datetime.strptime(
                start_date_text, "%Y-%m-%d"
            ).date()
        except ValueError:
            errors.append("Enter a valid start date.")

    if end_date_text:
        try:
            end_date = datetime.strptime(
                end_date_text, "%Y-%m-%d"
            ).date()
        except ValueError:
            errors.append("Enter a valid end date.")

    if start_date and end_date and start_date > end_date:
        errors.append("Start date cannot be later than end date.")

    if not errors:
        if start_date:
            start_datetime = timezone.make_aware(
                datetime.combine(start_date, time.min)
            )
            sales = sales.filter(sold_at__gte=start_datetime)

        if end_date:
            end_datetime = timezone.make_aware(
                datetime.combine(end_date + timedelta(days=1), time.min)
            )
            sales = sales.filter(sold_at__lt=end_datetime)

    sales = sales.order_by("-sold_at")
    summary = sales.aggregate(
        revenue=Sum("total_amount"),
        transactions=Count("id"),
        items_sold=Sum("quantity_sold"),
    )

    return render(request, "inventory/sales_report.html", {
        "sales": sales,
        "start_date": start_date_text,
        "end_date": end_date_text,
        "today": timezone.localdate().isoformat(),
        "total_revenue": summary["revenue"] or Decimal("0.00"),
        "total_transactions": summary["transactions"] or 0,
        "total_items_sold": summary["items_sold"] or 0,
        "errors": errors,
    })


@login_required
def export_sales_csv(request):
    start_date_text = request.GET.get("start_date", "").strip()
    end_date_text = request.GET.get("end_date", "").strip()
    start_date = None
    end_date = None

    if start_date_text:
        try:
            start_date = datetime.strptime(
                start_date_text, "%Y-%m-%d"
            ).date()
        except ValueError:
            return HttpResponseBadRequest("Invalid start date.")

    if end_date_text:
        try:
            end_date = datetime.strptime(
                end_date_text, "%Y-%m-%d"
            ).date()
        except ValueError:
            return HttpResponseBadRequest("Invalid end date.")

    if start_date and end_date and start_date > end_date:
        return HttpResponseBadRequest(
            "Start date cannot be later than end date."
        )

    sales = Sale.objects.select_related("product").all()

    if start_date:
        sales = sales.filter(
            sold_at__gte=timezone.make_aware(
                datetime.combine(start_date, time.min)
            )
        )

    if end_date:
        sales = sales.filter(
            sold_at__lt=timezone.make_aware(
                datetime.combine(end_date + timedelta(days=1), time.min)
            )
        )

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        'attachment; filename="sales_report.csv"'
    )
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow([
        "Sale ID", "Product Name", "Quantity Sold",
        "Unit Price", "Total Amount", "Date and Time",
    ])

    for sale in sales.order_by("-sold_at"):
        writer.writerow([
            sale.id,
            sale.product.name,
            sale.quantity_sold,
            sale.unit_price,
            sale.total_amount,
            timezone.localtime(sale.sold_at).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        ])

    return response


@login_required
def restock_product(request):
    products = Product.objects.all().order_by("name")
    suppliers = Supplier.objects.all().order_by("company_name")

    if request.method == "POST":
        product_id = request.POST.get("product")
        supplier_id = request.POST.get("supplier", "").strip()
        quantity_text = request.POST.get("quantity_added", "").strip()
        notes = request.POST.get("notes", "").strip()

        try:
            quantity_added = int(quantity_text)
            if quantity_added <= 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(
                request, "Enter a whole-number quantity greater than zero."
            )
            return render(request, "inventory/restock_product.html", {
                "products": products, "suppliers": suppliers,
            })

        supplier = None
        if supplier_id:
            try:
                supplier = Supplier.objects.get(id=int(supplier_id))
            except (Supplier.DoesNotExist, ValueError):
                messages.error(request, "Please select a valid supplier.")
                return render(request, "inventory/restock_product.html", {
                    "products": products, "suppliers": suppliers,
                })

        with transaction.atomic():
            product = get_object_or_404(
                Product.objects.select_for_update(), id=product_id
            )
            product.quantity += quantity_added
            product.save(update_fields=["quantity"])

            Restock.objects.create(
                product=product,
                supplier=supplier,
                quantity_added=quantity_added,
                notes=notes,
            )

        messages.success(
            request,
            f"Added {quantity_added} units to {product.name}. "
            f"New stock: {product.quantity}."
        )
        return redirect("restock_history")

    return render(request, "inventory/restock_product.html", {
        "products": products, "suppliers": suppliers,
    })


@login_required
def restock_history(request):
    restocks = Restock.objects.select_related(
        "product", "supplier"
    ).order_by("-restocked_at")

    total_units = restocks.aggregate(
        total=Sum("quantity_added")
    )["total"] or 0

    return render(request, "inventory/restock_history.html", {
        "restocks": restocks,
        "total_units": total_units,
        "total_transactions": restocks.count(),
    })


@login_required
def supplier_list(request):
    suppliers = Supplier.objects.all().order_by("company_name")
    return render(request, "inventory/supplier_list.html", {
        "suppliers": suppliers,
    })


@login_required
def add_supplier(request):
    if request.method == "POST":
        company_name = request.POST.get("company_name", "").strip()
        contact_name = request.POST.get("contact_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        email = request.POST.get("email", "").strip()
        address = request.POST.get("address", "").strip()

        if not company_name or not contact_name or not phone:
            messages.error(
                request,
                "Company name, contact name, and phone are required."
            )
            return render(
                request, "inventory/supplier_form.html",
                {"supplier": None}
            )

        Supplier.objects.create(
            company_name=company_name,
            contact_name=contact_name,
            phone=phone,
            email=email,
            address=address,
        )
        messages.success(request, "Supplier added successfully.")
        return redirect("supplier_list")

    return render(
        request, "inventory/supplier_form.html", {"supplier": None}
    )


@login_required
def edit_supplier(request, supplier_id):
    supplier = get_object_or_404(Supplier, id=supplier_id)

    if request.method == "POST":
        company_name = request.POST.get("company_name", "").strip()
        contact_name = request.POST.get("contact_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        email = request.POST.get("email", "").strip()
        address = request.POST.get("address", "").strip()

        if not company_name or not contact_name or not phone:
            messages.error(
                request,
                "Company name, contact name, and phone are required."
            )
            return render(
                request, "inventory/supplier_form.html",
                {"supplier": supplier}
            )

        supplier.company_name = company_name
        supplier.contact_name = contact_name
        supplier.phone = phone
        supplier.email = email
        supplier.address = address
        supplier.save()

        messages.success(request, "Supplier updated successfully.")
        return redirect("supplier_list")

    return render(
        request, "inventory/supplier_form.html",
        {"supplier": supplier}
    )


@login_required
def delete_supplier(request, supplier_id):
    if request.method != "POST":
        return redirect("supplier_list")

    supplier = get_object_or_404(Supplier, id=supplier_id)
    supplier.delete()

    messages.success(
        request,
        "Supplier deleted. Existing restock records are retained."
    )
    return redirect("supplier_list")
@login_required
def low_stock_products(request):
    products = Product.objects.filter(
        quantity__lte=5
    ).order_by("quantity", "name")

    out_of_stock_count = Product.objects.filter(
        quantity=0
    ).count()

    low_stock_count = Product.objects.filter(
        quantity__gt=0,
        quantity__lte=5
    ).count()

    return render(
        request,
        "inventory/low_stock.html",
        {
            "products": products,
            "out_of_stock_count": out_of_stock_count,
            "low_stock_count": low_stock_count,
        },
    )
