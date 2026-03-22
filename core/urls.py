from django.urls import path
from .views import sql_test

urlpatterns = [
    path('sql-test/', sql_test, name='sql_test'),
]