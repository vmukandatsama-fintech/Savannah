from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from core.models import RoleFeature, Roles


def sql_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get("user_email"):
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def feature_required(feature_name: str):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.session.get("user_email"):
                return redirect("login")

            role_name = request.session.get("role_name")
            has_feature = False
            if role_name:
                try:
                    role = Roles.objects.get(name=role_name)
                    rf = RoleFeature.objects.get(role=role)
                    has_feature = getattr(rf, feature_name, False)
                except (Roles.DoesNotExist, RoleFeature.DoesNotExist):
                    has_feature = False

            if not has_feature:
                messages.error(request, "You do not have access to that page.")
                return redirect("dashboard")

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
