from django.urls import path
from .views import sql_login_view, sql_logout_view, sql_test, dashboard_view, root_redirect_view

urlpatterns = [
    path("", root_redirect_view),
    path("login/", sql_login_view, name="sql_login"),
    path("logout/", sql_logout_view, name="sql_logout"),
    path("sql-test/", sql_test, name="sql_test"),
    path("dashboard/", dashboard_view, name="dashboard"),
]
