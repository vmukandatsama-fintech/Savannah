
import json
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from core.decorators import feature_required
from core.session_auth import get_session_user_email, sql_login_required
from services.collection_service import (
    get_pending_collections,
    get_collection_detail,
    disburse_request as disburse_request_service,
)
from services.approval_service import (
    get_approval_history,
    get_approval_inbox,
    process_approval,
)
from services.farmer_service import get_active_farmers
from services.item_service import get_requestable_items
from services.request_details_service import get_request_details
from services.request_history_service import get_my_requests
from services.request_service import create_request_from_cart
from services.user_service import get_user_context

# ============================================================
# COLLECTIONS / DISBURSEMENT
# ============================================================

@sql_login_required
@feature_required("collections")
def collection_inbox(request):
    search = request.GET.get("search", "").strip()

    rows = get_pending_collections(
        search=search,
        department_code=request.session.get("department_code"),
    )

    return render(
        request,
        "requests_app/collection_inbox.html",
        {
            "rows": rows,
            "search": search,
        },
    )

@sql_login_required
@feature_required("collections")
def collection_detail(request, request_number):
    detail = get_collection_detail(request_number)

    if not detail:
        messages.error(request, "Collection request not found.")
        return redirect("collection_inbox")

    return render(
        request,
        "requests_app/collection_detail.html",
        {
            "header": detail["header"],
            "lines": detail["lines"],
        },
    )

@sql_login_required
@feature_required("collections")
@require_http_methods(["POST"])
def disburse_request_view(request, request_number):
    detail = get_collection_detail(request_number)

    if not detail:
        messages.error(request, "Collection request not found.")
        return redirect("collection_inbox")

    issue_lines = []

    for line in detail["lines"]:
        field_name = f"issue_qty_{line['LineNumber']}"
        raw_value = (request.POST.get(field_name) or "0").strip()

        try:
            quantity_issued = float(raw_value)
        except ValueError:
            quantity_issued = 0

        if quantity_issued > 0:
            issue_lines.append(
                {
                    "LineNumber": line["LineNumber"],
                    "IssueQty": quantity_issued,
                }
            )

    if not issue_lines:
        messages.error(request, "Please enter at least one quantity to issue.")
        return redirect("collection_detail", request_number=request_number)

    try:
        result = disburse_request_service(
            request_number=request_number,
            disbursed_by=request.session.get("user_email"),
            issue_lines=issue_lines,
        )

        collection_number = None
        if result:
            collection_number = result.get("CollectionNumber")

        if collection_number:
            messages.success(
                request,
                f"Request {request_number} disbursed successfully. Collection Number: {collection_number}"
            )
        else:
            messages.success(
                request,
                f"Request {request_number} disbursed successfully."
            )

        return redirect("collection_inbox")

    except Exception as e:
        messages.error(request, str(e))
        return redirect("collection_detail", request_number=request_number)

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from core.decorators import feature_required
from core.session_auth import get_session_user_email, sql_login_required

from services.approval_service import (
    get_approval_history,
    get_approval_inbox,
    process_approval,
)
from services.farmer_service import get_active_farmers
from services.item_service import get_requestable_items
from services.request_details_service import get_request_details
from services.request_history_service import get_my_requests
from services.request_service import create_request_from_cart
from services.user_service import get_user_context


# ============================================================
# CREATE REQUEST
# ============================================================

@sql_login_required
@feature_required("create_request")
def request_cart(request):
    items_data = get_requestable_items()
    items = items_data["items"]
    farmers = get_active_farmers()

    user_email = get_session_user_email(request)
    user_context = get_user_context(user_email) if user_email else None

    if not user_context:
        return render(
            request,
            "requests_app/request_cart.html",
            {
                "items": items,
                "farmers": farmers,
                "error_message": "No active user context was found.",
            },
        )

    if request.method == "POST":
        cart_json = request.POST.get("cart_json", "[]")

        try:
            cart = json.loads(cart_json)
        except json.JSONDecodeError:
            cart = []
    )


@sql_login_required
@feature_required("approvals")
@require_http_methods(["POST"])
def approval_action(request, request_number):
    user_email = get_session_user_email(request)
    decision = request.POST.get("decision")
    comments = request.POST.get("comments")

    try:
        process_approval(
            request_number=request_number,
            approver_email=user_email,
            decision=decision,
            comments=comments,
        )
        messages.success(request, "Approval processed successfully.")

    except Exception as e:
        messages.error(request, str(e))

    return redirect("approval_detail", request_number=request_number)