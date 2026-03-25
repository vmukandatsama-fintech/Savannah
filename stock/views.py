import json

from django.contrib import messages
from django.shortcuts import redirect, render

from core.decorators import sql_login_required

from services.inventory_service import (
    create_inventory_item,
    get_categories,
    get_inventory_item_by_code,
    get_inventory_items,
    get_item_types,
    get_uoms,
    toggle_inventory_item_status,
    update_inventory_item,
)
from services.item_type_service import (
    create_item_type,
    get_item_type_by_code,
    get_item_types as get_all_item_types,
    toggle_item_type_status,
    update_item_type,
)
from services.uom_service import (
    create_uom,
    get_uom_by_code,
    get_uoms_master,
    update_uom,
)
from services.category_service import (
    create_category,
    get_categories_master,
    get_category_by_id,
    toggle_category_status,
    update_category,
)
from services.supplier_service import (
    create_supplier,
    get_supplier_by_id,
    get_suppliers,
    toggle_supplier_status,
    update_supplier,
)
from services.delivery_service import (
    create_delivery,
    get_active_suppliers,
    get_deliveries,
    get_delivery_by_number,
    get_inventory_for_delivery,
)


def _safe_decimal(value: str | None) -> float:
    try:
        return float(value) if value not in (None, "") else 0
    except (TypeError, ValueError):
        return 0


# =========================================================
# UOM VIEWS
# =========================================================

@sql_login_required
def uom_list_view(request):
    uoms = get_uoms_master()
    return render(
        request,
        "stock/uom_list.html",
        {
            "uoms": uoms,
            "page_title": "UOMs",
        },
    )


@sql_login_required
def uom_create_view(request):
    if request.method == "POST":
        uom_code = (request.POST.get("uom_code") or "").strip().upper()
        name = (request.POST.get("name") or "").strip()
        uom_type = (request.POST.get("uom_type") or "").strip() or None
        description = (request.POST.get("description") or "").strip() or None

        if not uom_code or not name:
            messages.error(request, "UOM Code and Name are required.")
        else:
            try:
                result = create_uom(uom_code, name, uom_type, description)
                if result:
                    messages.success(request, f"UOM created: {result['UOMCode']}")
                    return redirect("uom_list")
                messages.error(request, "Failed to create UOM.")
            except Exception as exc:
                messages.error(request, f"Create failed: {exc}")

    return render(
        request,
        "stock/uom_form.html",
        {
            "mode": "create",
            "uom": {},
            "page_title": "Create UOM",
        },
    )


@sql_login_required
def uom_edit_view(request, uom_code: str):
    uom = get_uom_by_code(uom_code)
    if not uom:
        messages.error(request, "UOM not found.")
        return redirect("uom_list")

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        uom_type = (request.POST.get("uom_type") or "").strip() or None
        description = (request.POST.get("description") or "").strip() or None

        if not name:
            messages.error(request, "UOM Name is required.")
        else:
            try:
                result = update_uom(uom_code, name, uom_type, description)
                if result:
                    messages.success(request, f"UOM updated: {uom_code}")
                    return redirect("uom_list")
                messages.error(request, "Failed to update UOM.")
            except Exception as exc:
                messages.error(request, f"Update failed: {exc}")

    return render(
        request,
        "stock/uom_form.html",
        {
            "mode": "edit",
            "uom": uom,
            "page_title": f"Edit UOM - {uom_code}",
        },
    )


@sql_login_required
def uom_toggle_view(request, uom_code: str):
    messages.info(request, "Toggle UOM status not implemented.")
    return redirect("uom_list")


# =========================================================
# INVENTORY VIEWS
# =========================================================

@sql_login_required
def inventory_list_view(request):
    items = get_inventory_items()
    return render(
        request,
        "stock/inventory_list.html",
        {
            "items": items,
            "page_title": "Inventory Items",
        },
    )


@sql_login_required
def inventory_create_view(request):
    categories = get_categories()
    uoms = get_uoms()
    item_types = get_item_types(active_only=True)

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        description = (request.POST.get("description") or "").strip() or None
        item_type = (request.POST.get("item_type") or "").strip() or None
        category_code = (request.POST.get("category_code") or "").strip() or None
        uom_code = (request.POST.get("uom_code") or "").strip() or None
        reorder_level = _safe_decimal(request.POST.get("reorder_level"))
        min_stock_level = _safe_decimal(request.POST.get("min_stock_level"))
        max_stock_level = _safe_decimal(request.POST.get("max_stock_level"))
        enabled_stock_alert = request.POST.get("enabled_stock_alert") == "on"
        item_image_path = (request.POST.get("item_image_path") or "").strip() or None

        if not name:
            messages.error(request, "Item name is required.")
        else:
            try:
                result = create_inventory_item(
                    name=name,
                    description=description,
                    item_type=item_type,
                    category_code=category_code,
                    uom_code=uom_code,
                    reorder_level=reorder_level,
                    min_stock_level=min_stock_level,
                    max_stock_level=max_stock_level,
                    enabled_stock_alert=enabled_stock_alert,
                    item_image_path=item_image_path,
                )
                if result:
                    messages.success(request, f"Inventory item created: {result['ItemCode']}")
                    return redirect("inventory_list")
                messages.error(request, "Failed to create inventory item.")
            except Exception as exc:
                messages.error(request, f"Create failed: {exc}")

    return render(
        request,
        "stock/inventory_form.html",
        {
            "mode": "create",
            "item": {},
            "categories": categories,
            "uoms": uoms,
            "item_types": item_types,
            "page_title": "Create Inventory Item",
        },
    )


@sql_login_required
def inventory_edit_view(request, item_code: str):
    item = get_inventory_item_by_code(item_code)
    categories = get_categories()
    uoms = get_uoms()
    item_types = get_item_types(active_only=True)

    if not item:
        messages.error(request, "Inventory item not found.")
        return redirect("inventory_list")

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        description = (request.POST.get("description") or "").strip() or None
        item_type = (request.POST.get("item_type") or "").strip() or None
        category_code = (request.POST.get("category_code") or "").strip() or None
        uom_code = (request.POST.get("uom_code") or "").strip() or None
        reorder_level = _safe_decimal(request.POST.get("reorder_level"))
        min_stock_level = _safe_decimal(request.POST.get("min_stock_level"))
        max_stock_level = _safe_decimal(request.POST.get("max_stock_level"))
        enabled_stock_alert = request.POST.get("enabled_stock_alert") == "on"
        item_image_path = (request.POST.get("item_image_path") or "").strip() or None

        if not name:
            messages.error(request, "Item name is required.")
        else:
            try:
                result = update_inventory_item(
                    item_code=item_code,
                    name=name,
                    description=description,
                    item_type=item_type,
                    category_code=category_code,
                    uom_code=uom_code,
                    reorder_level=reorder_level,
                    min_stock_level=min_stock_level,
                    max_stock_level=max_stock_level,
                    enabled_stock_alert=enabled_stock_alert,
                    item_image_path=item_image_path,
                )
                if result:
                    messages.success(request, f"Inventory item updated: {item_code}")
                    return redirect("inventory_list")
                messages.error(request, "Failed to update inventory item.")
            except Exception as exc:
                messages.error(request, f"Update failed: {exc}")

    return render(
        request,
        "stock/inventory_form.html",
        {
            "mode": "edit",
            "item": item,
            "categories": categories,
            "uoms": uoms,
            "item_types": item_types,
            "page_title": f"Edit Inventory Item - {item_code}",
        },
    )


@sql_login_required
def inventory_toggle_view(request, item_code: str):
    if request.method == "POST":
        try:
            result = toggle_inventory_item_status(item_code)
            if result:
                status_text = "activated" if result["IsActive"] else "deactivated"
                messages.success(request, f"{item_code} was {status_text}.")
            else:
                messages.error(request, "Failed to change inventory item status.")
        except Exception as exc:
            messages.error(request, f"Status change failed: {exc}")

    return redirect("inventory_list")


# =========================================================
# ITEM TYPE VIEWS
# =========================================================

@sql_login_required
def item_type_list_view(request):
    item_types = get_all_item_types()
    return render(
        request,
        "stock/item_type_list.html",
        {
            "item_types": item_types,
            "page_title": "Item Types",
        },
    )


@sql_login_required
def item_type_create_view(request):
    if request.method == "POST":
        item_type_code = (request.POST.get("item_type_code") or "").strip().upper()
        item_type_name = (request.POST.get("item_type_name") or "").strip()

        if not item_type_code or not item_type_name:
            messages.error(request, "Item Type Code and Name are required.")
        else:
            try:
                result = create_item_type(item_type_code, item_type_name)
                if result:
                    messages.success(request, f"Item type created: {result['ItemTypeCode']}")
                    return redirect("item_type_list")
                messages.error(request, "Failed to create item type.")
            except Exception as exc:
                messages.error(request, f"Create failed: {exc}")

    return render(
        request,
        "stock/item_type_form.html",
        {
            "mode": "create",
            "item_type": {},
            "page_title": "Create Item Type",
        },
    )


@sql_login_required
def item_type_edit_view(request, item_type_code: str):
    item_type = get_item_type_by_code(item_type_code)

    if not item_type:
        messages.error(request, "Item type not found.")
        return redirect("item_type_list")

    if request.method == "POST":
        item_type_name = (request.POST.get("item_type_name") or "").strip()

        if not item_type_name:
            messages.error(request, "Item Type Name is required.")
        else:
            try:
                result = update_item_type(item_type_code, item_type_name)
                if result:
                    messages.success(request, f"Item type updated: {item_type_code}")
                    return redirect("item_type_list")
                messages.error(request, "Failed to update item type.")
            except Exception as exc:
                messages.error(request, f"Update failed: {exc}")

    return render(
        request,
        "stock/item_type_form.html",
        {
            "mode": "edit",
            "item_type": item_type,
            "page_title": f"Edit Item Type - {item_type_code}",
        },
    )


@sql_login_required
def item_type_toggle_view(request, item_type_code: str):
    if request.method == "POST":
        try:
            result = toggle_item_type_status(item_type_code)
            if result:
                status_text = "activated" if result["IsActive"] else "deactivated"
                messages.success(request, f"{item_type_code} was {status_text}.")
            else:
                messages.error(request, "Failed to change item type status.")
        except Exception as exc:
            messages.error(request, f"Status change failed: {exc}")

    return redirect("item_type_list")


# =========================================================
# CATEGORY VIEWS
# =========================================================

@sql_login_required
def category_list_view(request):
    search = (request.GET.get("search") or "").strip()
    status = (request.GET.get("status") or "").strip()

    is_active = None
    if status == "active":
        is_active = True
    elif status == "inactive":
        is_active = False

    categories = get_categories_master(search=search, is_active=is_active)

    return render(
        request,
        "stock/category_list.html",
        {
            "categories": categories,
            "search": search,
            "status": status,
            "page_title": "Categories",
        },
    )


@sql_login_required
def category_create_view(request):
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        is_active = request.POST.get("is_active") == "on"

        if not name:
            messages.error(request, "Category Name is required.")
        else:
            try:
                result = create_category(
                    name=name,
                    is_active=is_active,
                )
                if result:
                    messages.success(request, f"Category created: {result['CategoryCode']}")
                    return redirect("category_list")
                messages.error(request, "Failed to create category.")
            except Exception as exc:
                messages.error(request, f"Create failed: {exc}")

        return render(
            request,
            "stock/category_form.html",
            {
                "mode": "create",
                "category": {
                    "Name": name,
                    "IsActive": is_active,
                },
                "page_title": "Create Category",
            },
        )

    return render(
        request,
        "stock/category_form.html",
        {
            "mode": "create",
            "category": {
                "IsActive": True,
            },
            "page_title": "Create Category",
        },
    )


@sql_login_required
def category_edit_view(request, category_id: int):
    category = get_category_by_id(category_id)

    if not category:
        messages.error(request, "Category not found.")
        return redirect("category_list")

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        is_active = request.POST.get("is_active") == "on"

        if not name:
            messages.error(request, "Category Name is required.")
        else:
            try:
                result = update_category(
                    category_id=category_id,
                    name=name,
                    is_active=is_active,
                )
                if result:
                    messages.success(request, f"Category updated: {result['CategoryCode']}")
                    return redirect("category_list")
                messages.error(request, "Failed to update category.")
            except Exception as exc:
                messages.error(request, f"Update failed: {exc}")

        category = {
            "CategoryID": category_id,
            "CategoryCode": category.get("CategoryCode", ""),
            "Name": name,
            "IsActive": is_active,
        }

    return render(
        request,
        "stock/category_form.html",
        {
            "mode": "edit",
            "category": category,
            "page_title": f"Edit Category - {category['CategoryCode']}",
        },
    )


@sql_login_required
def category_toggle_view(request, category_id: int):
    if request.method == "POST":
        try:
            result = toggle_category_status(category_id)
            if result:
                status_text = "activated" if result["IsActive"] else "deactivated"
                messages.success(request, f"{result['CategoryCode']} was {status_text}.")
            else:
                messages.error(request, "Failed to change category status.")
        except Exception as exc:
            messages.error(request, f"Status change failed: {exc}")

    return redirect("category_list")


# =========================================================
# SUPPLIER VIEWS
# =========================================================

@sql_login_required
def supplier_list_view(request):
    search = (request.GET.get("search") or "").strip()
    status = (request.GET.get("status") or "").strip()

    is_active = None
    if status == "active":
        is_active = True
    elif status == "inactive":
        is_active = False

    suppliers = get_suppliers(search=search, is_active=is_active)

    return render(
        request,
        "stock/supplier_list.html",
        {
            "suppliers": suppliers,
            "search": search,
            "status": status,
            "page_title": "Suppliers",
        },
    )


@sql_login_required
def supplier_create_view(request):
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        vat_number = (request.POST.get("vat_number") or "").strip() or None
        contact_email = (request.POST.get("contact_email") or "").strip() or None
        contact_phone = (request.POST.get("contact_phone") or "").strip() or None
        is_active = request.POST.get("is_active") == "on"

        if not name:
            messages.error(request, "Supplier Name is required.")
        else:
            try:
                result = create_supplier(
                    name=name,
                    vat=vat_number,
                    email=contact_email,
                    phone=contact_phone,
                    is_active=is_active,
                )
                if result:
                    messages.success(request, f"Supplier created: {result['SupplierCode']}")
                    return redirect("supplier_list")
                messages.error(request, "Failed to create supplier.")
            except Exception as exc:
                messages.error(request, f"Create failed: {exc}")

        return render(
            request,
            "stock/supplier_form.html",
            {
                "mode": "create",
                "supplier": {
                    "Name": name,
                    "VatNumber": vat_number,
                    "ContactEmail": contact_email,
                    "ContactPhone": contact_phone,
                    "IsActive": is_active,
                },
                "page_title": "Create Supplier",
            },
        )

    return render(
        request,
        "stock/supplier_form.html",
        {
            "mode": "create",
            "supplier": {
                "IsActive": True,
            },
            "page_title": "Create Supplier",
        },
    )


@sql_login_required
def supplier_edit_view(request, supplier_id: int):
    supplier = get_supplier_by_id(supplier_id)

    if not supplier:
        messages.error(request, "Supplier not found.")
        return redirect("supplier_list")

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        vat_number = (request.POST.get("vat_number") or "").strip() or None
        contact_email = (request.POST.get("contact_email") or "").strip() or None
        contact_phone = (request.POST.get("contact_phone") or "").strip() or None
        is_active = request.POST.get("is_active") == "on"

        if not name:
            messages.error(request, "Supplier Name is required.")
        else:
            try:
                result = update_supplier(
                    supplier_id=supplier_id,
                    name=name,
                    vat=vat_number,
                    email=contact_email,
                    phone=contact_phone,
                    is_active=is_active,
                )
                if result:
                    messages.success(request, f"Supplier updated: {result['SupplierCode']}")
                    return redirect("supplier_list")
                messages.error(request, "Failed to update supplier.")
            except Exception as exc:
                messages.error(request, f"Update failed: {exc}")

        supplier = {
            "SupplierID": supplier_id,
            "SupplierCode": supplier.get("SupplierCode", ""),
            "Name": name,
            "VatNumber": vat_number,
            "ContactEmail": contact_email,
            "ContactPhone": contact_phone,
            "IsActive": is_active,
        }

    return render(
        request,
        "stock/supplier_form.html",
        {
            "mode": "edit",
            "supplier": supplier,
            "page_title": f"Edit Supplier - {supplier['SupplierCode']}",
        },
    )


@sql_login_required
def supplier_toggle_view(request, supplier_id: int):
    if request.method == "POST":
        try:
            result = toggle_supplier_status(supplier_id)
            if result:
                status_text = "activated" if result["IsActive"] else "deactivated"
                messages.success(request, f"{result['SupplierCode']} was {status_text}.")
            else:
                messages.error(request, "Failed to change supplier status.")
        except Exception as exc:
            messages.error(request, f"Status change failed: {exc}")

    return redirect("supplier_list")


# =========================================================
# DELIVERY VIEWS
# =========================================================

@sql_login_required
def delivery_list_view(request):
    search = (request.GET.get("search") or "").strip()
    supplier_code = (request.GET.get("supplier_code") or "").strip() or None
    date_from = (request.GET.get("date_from") or "").strip() or None
    date_to = (request.GET.get("date_to") or "").strip() or None

    deliveries = get_deliveries(
        search=search,
        supplier_code=supplier_code,
        date_from=date_from,
        date_to=date_to,
    )
    suppliers = get_active_suppliers()

    return render(
        request,
        "stock/delivery_list.html",
        {
            "deliveries": deliveries,
            "suppliers": suppliers,
            "search": search,
            "supplier_code": supplier_code,
            "date_from": date_from,
            "date_to": date_to,
            "page_title": "Deliveries",
        },
    )


@sql_login_required
def delivery_create_view(request):
    suppliers = get_active_suppliers()
    inventory_items = get_inventory_for_delivery()

    if request.method == "POST":
        delivery_date = (request.POST.get("delivery_date") or "").strip()
        supplier_code = (request.POST.get("supplier_code") or "").strip()
        vehicle_registration = (request.POST.get("vehicle_registration") or "").strip() or None
        driver_name = (request.POST.get("driver_name") or "").strip() or None
        waybill_number = (request.POST.get("waybill_number") or "").strip() or None
        remarks = (request.POST.get("remarks") or "").strip() or None
        line_items_json = request.POST.get("line_items_json") or "[]"

        try:
            line_items = json.loads(line_items_json)
            if not isinstance(line_items, list):
                line_items = []
        except json.JSONDecodeError:
            line_items = []

        if not delivery_date:
            messages.error(request, "Delivery Date is required.")
        elif not supplier_code:
            messages.error(request, "Supplier is required.")
        elif not line_items:
            messages.error(request, "At least one delivery line is required.")
        else:
            try:
                result = create_delivery(
                    delivery_date=delivery_date,
                    supplier_code=supplier_code,
                    vehicle_registration=vehicle_registration,
                    driver_name=driver_name,
                    waybill_number=waybill_number,
                    received_by_email=request.session.get("user_email", ""),
                    remarks=remarks,
                    line_items=line_items,
                )
                if result:
                    messages.success(request, f"Delivery created: {result['DeliveryNumber']}")
                    return redirect("delivery_detail", delivery_number=result["DeliveryNumber"])
                messages.error(request, "Failed to create delivery.")
            except Exception as exc:
                messages.error(request, f"Create failed: {exc}")

        return render(
            request,
            "stock/delivery_form.html",
            {
                "suppliers": suppliers,
                "inventory_items": inventory_items,
                "draft": {
                    "delivery_date": delivery_date,
                    "supplier_code": supplier_code,
                    "vehicle_registration": vehicle_registration,
                    "driver_name": driver_name,
                    "waybill_number": waybill_number,
                    "remarks": remarks,
                    "line_items_json": line_items_json,
                },
                "page_title": "Create Delivery",
            },
        )

    return render(
        request,
        "stock/delivery_form.html",
        {
            "suppliers": suppliers,
            "inventory_items": inventory_items,
            "draft": {
                "line_items_json": "[]",
            },
            "page_title": "Create Delivery",
        },
    )


@sql_login_required
def delivery_detail_view(request, delivery_number: str):
    delivery = get_delivery_by_number(delivery_number)

    if not delivery:
        messages.error(request, "Delivery not found.")
        return redirect("delivery_list")

    return render(
        request,
        "stock/delivery_detail.html",
        {
            "delivery": delivery["header"],
            "lines": delivery["lines"],
            "page_title": f"Delivery - {delivery_number}",
        },
    )