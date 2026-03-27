from django.contrib import messages
from django.db import connection
from django.http import HttpResponse
from django.shortcuts import redirect, render

from services.auth_service import login_sql_user
from services.dashboard_service import (
    get_dashboard_cards,
    get_dashboard_metrics,
    get_recent_activity,   # ✅ ADD THIS
)
from core.decorators import feature_required
from core.session_auth import sql_login_required


@sql_login_required
@feature_required("dashboard")
def dashboard_view(request):
    user_email = request.session.get("user_email", "")
    role_name = request.session.get("role_name", "")

    metrics = get_dashboard_metrics(
        user_email=user_email,
        role_name=role_name,
    )
    cards = get_dashboard_cards(role_name)

    # ✅ ADD THIS
    recent_activity = get_recent_activity(user_email, role_name)

    # ✅ DEBUG (you WILL see this in terminal now)
    print("DASHBOARD DEBUG:", user_email, role_name, len(recent_activity))

    return render(
        request,
        "core/dashboard.html",
        {
            "metrics": metrics,
            "cards": cards,
            "role_name": role_name,
            "recent_activity": recent_activity,  # ✅ ADD THIS
        },
    )


def sql_login_view(request):
    if request.session.get("user_email"):
        return redirect("/requests/my-requests/")

    if request.method == "POST":
        email = (request.POST.get("email") or "").strip()
        password = (request.POST.get("password") or "").strip()

        if not email or not password:
            messages.error(request, "Email and password are required.")
            return render(request, "registration/sql_login.html")

        try:
            profile = login_sql_user(email, password)

            if not profile:
                messages.error(request, "Invalid email or password.")
                return render(request, "registration/sql_login.html")

            request.session["user_email"] = profile["Email"]
            request.session["user_name"] = profile["Name"]
            request.session["department_code"] = profile["DepartmentCode"]
            request.session["department_name"] = profile.get("DepartmentName", "")
            request.session["role_name"] = profile["RoleName"]
            request.session["is_requestor"] = profile["IsRequestor"]
            request.session["is_approver"] = profile["IsApprover"]
            request.session["is_authorizer"] = profile["IsAuthorizer"]
            request.session["app_target"] = profile["AppTarget"]
            request.session["app_target_code"] = profile["AppTargetCode"]

            return redirect("my_requests")

        except Exception as e:
            messages.error(request, str(e))
            return render(request, "registration/sql_login.html")

    return render(request, "registration/sql_login.html")


def sql_logout_view(request):
    request.session.flush()
    return redirect("/login/")


def sql_test(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT DB_NAME() AS db_name, @@SERVERNAME AS server_name")
        row = cursor.fetchone()

    return HttpResponse(
        f"Connected successfully. Database: {row[0]} | Server: {row[1]}"
    )


def root_redirect_view(request):
    return redirect('sql_login')