from django.urls import path
from . import views

urlpatterns = [
    # Inventory
    path("inventory/", views.inventory_list_view, name="inventory_list"),
    path("inventory/create/", views.inventory_create_view, name="inventory_create"),
    path("inventory/<str:item_code>/edit/", views.inventory_edit_view, name="inventory_edit"),
    path("inventory/<str:item_code>/toggle/", views.inventory_toggle_view, name="inventory_toggle"),

    # Item Types
    path("item-types/", views.item_type_list_view, name="item_type_list"),
    path("item-types/create/", views.item_type_create_view, name="item_type_create"),
    path("item-types/<str:item_type_code>/edit/", views.item_type_edit_view, name="item_type_edit"),
    path("item-types/<str:item_type_code>/toggle/", views.item_type_toggle_view, name="item_type_toggle"),

    # UOM
    path("uoms/", views.uom_list_view, name="uom_list"),
    path("uoms/create/", views.uom_create_view, name="uom_create"),
    path("uoms/<str:uom_code>/edit/", views.uom_edit_view, name="uom_edit"),
    path("uoms/<str:uom_code>/toggle/", views.uom_toggle_view, name="uom_toggle"),

    # Categories
    path("categories/", views.category_list_view, name="category_list"),
    path("categories/create/", views.category_create_view, name="category_create"),
    path("categories/<int:category_id>/edit/", views.category_edit_view, name="category_edit"),
    path("categories/<int:category_id>/toggle/", views.category_toggle_view, name="category_toggle"),

    # Suppliers
    path("suppliers/", views.supplier_list_view, name="supplier_list"),
    path("suppliers/create/", views.supplier_create_view, name="supplier_create"),
    path("suppliers/<int:supplier_id>/edit/", views.supplier_edit_view, name="supplier_edit"),
    path("suppliers/<int:supplier_id>/toggle/", views.supplier_toggle_view, name="supplier_toggle"),

    # Deliveries
    path("deliveries/", views.delivery_list_view, name="delivery_list"),
    path("deliveries/create/", views.delivery_create_view, name="delivery_create"),
    path("deliveries/<str:delivery_number>/", views.delivery_detail_view, name="delivery_detail"),
]