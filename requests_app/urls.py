from django.urls import path
from .views import (
    approval_action,
    approval_detail,
    approval_inbox,
    my_requests,
    request_cart,
    request_details,
    collection_inbox,
    collection_detail,
    disburse_request_view,
    collection_history,
    collection_history_detail,
    regenerate_collection_voucher_view,
    open_collection_voucher_view,
    download_collection_voucher_view,
)

urlpatterns = [
    path("create/", request_cart, name="request_cart"),
    path("my-requests/", my_requests, name="my_requests"),
    path("my-requests/<str:request_number>/", request_details, name="request_details"),

    path("approvals/", approval_inbox, name="approval_inbox"),
    path("approvals/<str:request_number>/", approval_detail, name="approval_detail"),
    path("approvals/<str:request_number>/action/", approval_action, name="approval_action"),

    # Collection History routes (must be above collections/)


    path("collections/history/", collection_history, name="collection_history"),
    path("collections/history/<str:collection_number>/", collection_history_detail, name="collection_history_detail"),
    path(
        "collections/history/<str:collection_number>/regenerate-voucher/",
        regenerate_collection_voucher_view,
        name="regenerate_collection_voucher",
    ),
    path(
        "collections/history/<str:collection_number>/open-voucher/",
        open_collection_voucher_view,
        name="open_collection_voucher",
    ),
    path(
        "collections/history/<str:collection_number>/download-voucher/",
        download_collection_voucher_view,
        name="download_collection_voucher",
    ),

    path("collections/", collection_inbox, name="collection_inbox"),
    path("collections/<str:request_number>/", collection_detail, name="collection_detail"),
    path("collections/<str:request_number>/disburse/", disburse_request_view, name="disburse_request"),
]
