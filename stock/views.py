from django.contrib import messages
from django.shortcuts import redirect, render
from core.decorators import sql_login_required
from services.inventory_service import (
	create_inventory_item,
	get_categories,
	get_inventory_item_by_code,
	get_inventory_items,
	get_uoms,
	toggle_inventory_item_status,
	update_inventory_item,
	get_item_types,
)
from services.item_type_service import (
	create_item_type,
	get_item_type_by_code,
	get_item_types as get_all_item_types,
	toggle_item_type_status,
	update_item_type,
)
from services.uom_service import (
	get_uoms_master,
	get_uom_by_code,
	create_uom,
	update_uom,
)

# UOM Views
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
			result = create_uom(uom_code, name, uom_type, description)
			if result:
				messages.success(request, f"UOM created: {result['UOMCode']}")
				return redirect("uom_list")
			messages.error(request, "Failed to create UOM.")

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
			result = update_uom(uom_code, name, uom_type, description)
			if result:
				messages.success(request, f"UOM updated: {uom_code}")
				return redirect("uom_list")
			messages.error(request, "Failed to update UOM.")

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
	# Placeholder for toggle logic if needed
	messages.info(request, "Toggle UOM status not implemented.")
	return redirect("uom_list")


def _safe_decimal(value: str | None) -> float:
	try:
		return float(value) if value not in (None, "") else 0
	except (TypeError, ValueError):
		return 0


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
				messages.success(
					request,
					f"Inventory item created successfully: {result['ItemCode']}",
				)
				return redirect("inventory_list")

			messages.error(request, "Failed to create inventory item.")

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

# Item Type Views
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
			result = create_item_type(item_type_code, item_type_name)
			if result:
				messages.success(request, f"Item type created: {result['ItemTypeCode']}")
				return redirect("item_type_list")
			messages.error(request, "Failed to create item type.")

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
			result = update_item_type(item_type_code, item_type_name)
			if result:
				messages.success(request, f"Item type updated: {item_type_code}")
				return redirect("item_type_list")
			messages.error(request, "Failed to update item type.")

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
		result = toggle_item_type_status(item_type_code)
		if result:
			status_text = "activated" if result["IsActive"] else "deactivated"
			messages.success(request, f"{item_type_code} was {status_text}.")
		else:
			messages.error(request, "Failed to change item type status.")

	return redirect("item_type_list")


@sql_login_required
def inventory_toggle_view(request, item_code: str):
	if request.method == "POST":
		result = toggle_inventory_item_status(item_code)

		if result:
			status_text = "activated" if result["IsActive"] else "deactivated"
			messages.success(request, f"{item_code} was {status_text}.")
		else:
			messages.error(request, "Failed to change inventory item status.")

	return redirect("inventory_list")
