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
)

urlpatterns = [
    path("create/", request_cart, name="request_cart"),
    path("my-requests/", my_requests, name="my_requests"),
    path("my-requests/<str:request_number>/", request_details, name="request_details"),

    path("approvals/", approval_inbox, name="approval_inbox"),
    path("approvals/<str:request_number>/", approval_detail, name="approval_detail"),
    path("approvals/<str:request_number>/action/", approval_action, name="approval_action"),

    path("collections/", collection_inbox, name="collection_inbox"),
    path("collections/<str:request_number>/", collection_detail, name="collection_detail"),
    path("collections/<str:request_number>/disburse/", disburse_request_view, name="disburse_request"),
]
