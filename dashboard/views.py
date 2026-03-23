from django.shortcuts import render
from core.decorators import feature_required
from core.session_auth import sql_login_required
from services.dashboard_service import get_dashboard_cards, get_dashboard_metrics


@sql_login_required
@feature_required("dashboard")
def dashboard_view(request):
    user_email = request.session.get("user_email")
    role_name = request.session.get("role_name")

    metrics = get_dashboard_metrics(user_email, role_name)
    cards = get_dashboard_cards(role_name)

    return render(
        request,
        "core/dashboard.html",
        {
            "metrics": metrics,
            "cards": cards,
            "role_name": role_name,
        },
    )
