from functools import wraps
from django.shortcuts import redirect

def sql_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get("user_email"):
            return redirect("/login/")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def get_session_user_email(request):
    return request.session.get("user_email", "")
