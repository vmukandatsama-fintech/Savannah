from django.urls import path
from . import views

urlpatterns = [
    path("inventory/", views.inventory_list_view, name="inventory_list"),
    path("inventory/create/", views.inventory_create_view, name="inventory_create"),
    path("inventory/<str:item_code>/edit/", views.inventory_edit_view, name="inventory_edit"),
    path("inventory/<str:item_code>/toggle/", views.inventory_toggle_view, name="inventory_toggle"),

    path("item-types/", views.item_type_list_view, name="item_type_list"),
    path("item-types/create/", views.item_type_create_view, name="item_type_create"),
    path("item-types/<str:item_type_code>/edit/", views.item_type_edit_view, name="item_type_edit"),
    path("item-types/<str:item_type_code>/toggle/", views.item_type_toggle_view, name="item_type_toggle"),
    path("uoms/", views.uom_list_view, name="uom_list"),
    path("uoms/create/", views.uom_create_view, name="uom_create"),
    path("uoms/<str:uom_code>/edit/", views.uom_edit_view, name="uom_edit"),
    path("uoms/<str:uom_code>/toggle/", views.uom_toggle_view, name="uom_toggle"),
]
