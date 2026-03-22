from django.urls import path
from . import views

urlpatterns = [
    path("create/", views.request_cart, name="request_cart"),
    path("my-requests/", views.my_requests, name="my_requests"),
    path("<str:request_number>/", views.request_details, name="request_details"),
]
