
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, Count
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .models import Product, Supplier, Purchase


@login_required
def add_purchase(request):
    products = Product.objects.all().order_by("name")
    suppliers = Supplier.objects.all().order_by("company_name")

    if request.method == "POST":
        product_id = request.POST.get("product", "").strip()
        supplier_id = request.POST.get("supplier", "").strip()
        quantity_text = request.POST.get("quantity_purchased", "").strip()
        unit_cost_text = request.POST.get("unit_cost", "").strip()
        notes = request.POST.get("notes", "").strip()

        try:
            quantity = int(quantity_text)
            unit_cost = Decimal(unit_cost_text)

            if quantity <= 0:
                raise ValueError

            if (
                not unit_cost.is_finite()
                or unit_cost < 0
                or unit_cost.as_tuple().exponent < -2
            ):
                raise ValueError

        except (ValueError, TypeError, InvalidOperation, ArithmeticError):
            messages.error(
                request,
                "Enter a valid quantity and a non-negative purchase price "
                "with no more than two decimal places."
            )
            return render(
                request,
                "inventory/add_purchase.html",
                {
                    "products": products,
                    "suppliers": suppliers,
                    "form_data": request.POST,
                },
            )

        if not products.exists():
            messages.error(request, "Add a product before recording a purchase.")
            return redirect("add_product")

        if not suppliers.exists():
            messages.error(request, "Add a supplier before recording a purchase.")
            return redirect("add_supplier")

        try:
            with transaction.atomic():
                product = get_object_or_404(
                    Product.objects.select_for_update(),
                    id=int(product_id),
                )
                supplier = get_object_or_404(
                    Supplier.objects.select_for_update(),
                    id=int(supplier_id),
                )

                total_cost = unit_cost * quantity

                product.quantity += quantity
                product.save(update_fields=["quantity"])

                Purchase.objects.create(
                    product=product,
                    supplier=supplier,
                    quantity_purchased=quantity,
                    unit_cost=unit_cost,
                    total_cost=total_cost,
                    notes=notes,
                )

        except (ValueError, TypeError):
            messages.error(request, "Please select a valid product and supplier.")
            return render(
                request,
                "inventory/add_purchase.html",
                {
                    "products": products,
                    "suppliers": suppliers,
                    "form_data": request.POST,
                },
            )

        messages.success(
            request,
            f"Purchase recorded. Added {quantity} units of {product.name}. "
            f"New stock: {product.quantity}. Total cost: ₹{total_cost:.2f}."
        )
        return redirect("purchase_history")

    return render(
        request,
        "inventory/add_purchase.html",
        {
            "products": products,
            "suppliers": suppliers,
            "form_data": {},
        },
    )


@login_required
def purchase_history(request):
    purchases = Purchase.objects.select_related(
        "product", "supplier"
    ).order_by("-purchased_at")

    summary = purchases.aggregate(
        total_cost=Sum("total_cost"),
        transactions=Count("id"),
        total_units=Sum("quantity_purchased"),
    )

    return render(
        request,
        "inventory/purchase_history.html",
        {
            "purchases": purchases,
            "total_cost": summary["total_cost"] or Decimal("0.00"),
            "total_transactions": summary["transactions"] or 0,
            "total_units": summary["total_units"] or 0,
        },
    )


@login_required
def purchase_report(request):
    start_date = request.GET.get("start_date", "").strip()
    end_date = request.GET.get("end_date", "").strip()

    purchases = Purchase.objects.select_related(
        "product", "supplier"
    ).order_by("-purchased_at")

    valid_dates = True

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None

        if start and end and start > end:
            valid_dates = False

        if start:
            purchases = purchases.filter(purchased_at__date__gte=start)

        if end:
            purchases = purchases.filter(purchased_at__date__lte=end)

    except ValueError:
        valid_dates = False

    if not valid_dates:
        messages.error(request, "Please enter valid dates in the correct order.")
        purchases = Purchase.objects.none()

    summary = purchases.aggregate(
        total_cost=Sum("total_cost"),
        total_transactions=Count("id"),
        total_units=Sum("quantity_purchased"),
    )

    supplier_totals = (
        purchases.values("supplier__company_name")
        .annotate(
            purchase_count=Count("id"),
            units=Sum("quantity_purchased"),
            cost=Sum("total_cost"),
        )
        .order_by("-cost")
    )

    product_totals = (
        purchases.values("product__name")
        .annotate(
            purchase_count=Count("id"),
            units=Sum("quantity_purchased"),
            cost=Sum("total_cost"),
        )
        .order_by("-cost")
    )

    return render(
        request,
        "inventory/purchase_report.html",
        {
            "purchases": purchases,
            "total_cost": summary["total_cost"] or Decimal("0.00"),
            "total_transactions": summary["total_transactions"] or 0,
            "total_units": summary["total_units"] or 0,
            "supplier_totals": supplier_totals,
            "product_totals": product_totals,
            "start_date": start_date,
            "end_date": end_date,
        },
    )


@login_required
def export_purchase_csv(request):
    start_date = request.GET.get("start_date", "").strip()
    end_date = request.GET.get("end_date", "").strip()

    purchases = Purchase.objects.select_related(
        "product", "supplier"
    ).order_by("-purchased_at")

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None

        if start and end and start > end:
            return HttpResponseBadRequest(
                "Start date must not be later than end date."
            )

    except ValueError:
        return HttpResponseBadRequest("Please provide valid dates in YYYY-MM-DD format.")

    if start:
        purchases = purchases.filter(purchased_at__date__gte=start)

    if end:
        purchases = purchases.filter(purchased_at__date__lte=end)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="purchase_report.csv"'
    response.write("\ufeff")

    writer = csv.writer(response)

    writer.writerow([
        "Purchase ID",
        "Purchase Date",
        "Product",
        "Supplier",
        "Quantity Purchased",
        "Unit Cost",
        "Total Cost",
        "Notes",
    ])

    for purchase in purchases:
        writer.writerow([
            purchase.id,
            timezone.localtime(purchase.purchased_at).strftime("%Y-%m-%d %H:%M"),
            purchase.product.name,
            purchase.supplier.company_name,
            purchase.quantity_purchased,
            f"{purchase.unit_cost:.2f}",
            f"{purchase.total_cost:.2f}",
            purchase.notes,
        ])

    return response
