from django.urls import path
from . import views

urlpatterns = [
    path("", views.approval_inbox, name="approval_inbox"),
    path("<str:request_number>/", views.approval_detail, name="approval_detail"),
    path("<str:request_number>/action/", views.approval_action, name="approval_action"),
]