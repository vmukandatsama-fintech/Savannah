# === VOUCHER OPEN/DOWNLOAD ===
@sql_login_required
@feature_required("collections")
def open_collection_voucher_view(request, collection_number):  # Keeping the correct version
    detail = get_collection_history_detail(collection_number)

    if not detail or not detail["header"].get("VoucherPath"):
        messages.error(request, "Voucher not found.")
        return redirect("collection_history_detail", collection_number=collection_number)

    voucher_path = detail["header"]["VoucherPath"]

    if voucher_path.lower().startswith("http://") or voucher_path.lower().startswith("https://"):
        return HttpResponseRedirect(voucher_path)

    if not os.path.exists(voucher_path):
        raise Http404("Voucher file not found.")

    return FileResponse(open(voucher_path, "rb"), content_type="application/pdf")


@sql_login_required
@feature_required("collections")
def download_collection_voucher_view(request, collection_number):  # Keeping the correct version
    detail = get_collection_history_detail(collection_number)

    if not detail or not detail["header"].get("VoucherPath"):
        messages.error(request, "Voucher not found.")
        return redirect("collection_history_detail", collection_number=collection_number)

    voucher_path = detail["header"]["VoucherPath"]

    if voucher_path.lower().startswith("http://") or voucher_path.lower().startswith("https://"):
        response = requests.get(voucher_path, timeout=60)
        response.raise_for_status()
        download_name = f"{collection_number}.pdf"
        http_response = HttpResponse(response.content, content_type="application/pdf")
        http_response["Content-Disposition"] = f'attachment; filename="{download_name}"'
        return http_response

    if not os.path.exists(voucher_path):
        raise Http404("Voucher file not found.")

    return FileResponse(
        open(voucher_path, "rb"),
        as_attachment=True,
        filename=f"{collection_number}.pdf",
        content_type="application/pdf",
    )

import os
import json
import requests
from urllib.parse import urlparse
from django.http import FileResponse, Http404, HttpResponseRedirect, HttpResponse
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from core.decorators import feature_required
from core.session_auth import get_session_user_email, sql_login_required
from services.collection_service import get_pending_collections, get_collection_detail, get_collection_departments, get_collection_history, get_collection_history_detail, disburse_request as disburse_request_service
from services.approval_service import get_approval_history, get_approval_inbox, process_approval
from services.farmer_service import get_active_farmers
from services.item_service import get_requestable_items
from services.request_details_service import get_request_details
from services.request_history_service import get_my_requests
from services.request_service import create_request_from_cart
from services.user_service import get_user_context
from services.voucher_service import regenerate_collection_voucher

# === VOUCHER OPEN/DOWNLOAD ===
@sql_login_required
@feature_required("collections")
def open_collection_voucher_view(request, collection_number):
    detail = get_collection_history_detail(collection_number)

    if not detail or not detail["header"].get("VoucherPath"):
        messages.error(request, "Voucher not found.")
        return redirect("collection_history_detail", collection_number=collection_number)

    voucher_path = detail["header"]["VoucherPath"]

    if voucher_path.lower().startswith("http://") or voucher_path.lower().startswith("https://"):
        return HttpResponseRedirect(voucher_path)

    if not os.path.exists(voucher_path):
        raise Http404("Voucher file not found.")

    return FileResponse(open(voucher_path, "rb"), content_type="application/pdf")


@sql_login_required
@feature_required("collections")
def download_collection_voucher_view(request, collection_number):
    detail = get_collection_history_detail(collection_number)

    if not detail or not detail["header"].get("VoucherPath"):
        messages.error(request, "Voucher not found.")
        return redirect("collection_history_detail", collection_number=collection_number)

    voucher_path = detail["header"]["VoucherPath"]

    if voucher_path.lower().startswith("http://") or voucher_path.lower().startswith("https://"):
        response = requests.get(voucher_path, timeout=60)
        response.raise_for_status()
        download_name = f"{collection_number}.pdf"
        http_response = HttpResponse(response.content, content_type="application/pdf")
        http_response["Content-Disposition"] = f'attachment; filename="{download_name}"'
        return http_response

    if not os.path.exists(voucher_path):
        raise Http404("Voucher file not found.")

    return FileResponse(
        open(voucher_path, "rb"),
        as_attachment=True,
        filename=f"{collection_number}.pdf",
        content_type="application/pdf",
    )

# === COLLECTION HISTORY ===

# === COLLECTION HISTORY ===
@sql_login_required
@feature_required("collections")
def collection_history(request):
    search = request.GET.get("search", "").strip()
    collection_number = request.GET.get("collection_number", "").strip()
    request_number = request.GET.get("request_number", "").strip()
    department = request.GET.get("department", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    rows = get_collection_history(
        search=search,
        collection_number=collection_number,
        request_number=request_number,
        department_code_filter=department,
        date_from=date_from,
        date_to=date_to,
    )
    departments = get_collection_departments()

    return render(
        request,
        "requests_app/collection_history.html",
        {
            "rows": rows,
            "search": search,
            "collection_number": collection_number,
            "request_number": request_number,
            "department": department,
            "date_from": date_from,
            "date_to": date_to,
            "departments": departments,
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
            disbursed_by=get_session_user_email(request),
            issue_lines=issue_lines,
        )

        collection_number = None
        if result:
            collection_number = result.get("CollectionNumber")

        voucher_path = None

        if collection_number:
            try:
                voucher_result = regenerate_collection_voucher(collection_number)
                if voucher_result:
                    voucher_path = voucher_result.get("VoucherPath")
            except Exception as voucher_ex:
                messages.warning(
                    request,
                    f"Disbursement succeeded, but voucher generation failed: {voucher_ex}"
                )

        if collection_number and voucher_path:
            messages.success(
                request,
                f"Disbursement successful. Collection Number: {collection_number}. Voucher generated."
            )
        elif collection_number:
            messages.success(
                request,
                f"Disbursement successful. Collection Number: {collection_number}."
            )
        else:
            messages.success(request, "Disbursement successful.")

        return redirect("collection_history")

    except Exception as e:
        messages.error(request, f"Error: {e}")
        return redirect("collection_detail", request_number=request_number)


@sql_login_required
@feature_required("collections")
def regenerate_collection_voucher_view(request, collection_number):
    try:
        result = regenerate_collection_voucher(collection_number)
        voucher_path = result.get("VoucherPath") if result else None

        if voucher_path:
            messages.success(request, f"Voucher regenerated successfully for {collection_number}.")
        else:
            messages.warning(request, f"Voucher regeneration completed, but no voucher path was returned.")
    except Exception as ex:
        messages.error(request, f"Voucher regeneration failed: {ex}")

    return redirect("collection_history_detail", collection_number=collection_number)
@sql_login_required
@feature_required("collections")
def collection_history_detail(request, collection_number):
    detail = get_collection_history_detail(collection_number)

    if not detail:
        messages.error(request, "Collection not found.")
        return redirect("collection_history")

    return render(
        request,
        "requests_app/collection_history_detail.html",
        {
            "header": detail["header"],
            "lines": detail["lines"],
        },
    )

# Restored approval_inbox view
@sql_login_required
@feature_required("approvals")
def approval_inbox(request):
    user_email = (request.user.email or "").strip()
    if not user_email:
        user_email = (request.user.username or "").strip()

    mode = request.GET.get("mode", "Pending").strip() or "Pending"
    approvals = get_approval_inbox(user_email, mode)

    pending_count = len(
        [
            row for row in approvals
            if row.get("ApprovalStatusName") == "Pending"
            and row.get("IsCurrent") in (1, True)
        ]
    )

    return render(
        request,
        "requests_app/approval_inbox.html",
        {
            "approvals": approvals,
            "mode": mode,
            "pending_count": pending_count,
        },
    )
# Restored my_requests view
@sql_login_required
@feature_required("approvals")
def my_requests(request):
    user_email = get_session_user_email(request)
    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "").strip()
    page = int(request.GET.get("page", 1) or 1)
    page_size = int(request.GET.get("page_size", 10) or 10)

    result = get_my_requests(
        user_email=user_email,
        search=search,
        status=status,
        page=page,
        page_size=page_size,
    )

    return render(
        request,
        "requests_app/my_requests.html",
        {
            "request_history": result,
            "filters": {
                "search": search,
                "status": status,
                "page_size": page_size,
            },
        },
    )

# Restored request_details view
@sql_login_required
@feature_required("approvals")
def request_details(request, request_number):
    user_email = get_session_user_email(request)
    details = get_request_details(request_number, user_email)

    if not details:
        return render(
            request,
            "requests_app/request_details.html",
            {
                "not_found": True,
                "request_number": request_number,
            },
        )

    return render(
        request,
        "requests_app/request_details.html",
        {
            "details": details,
            "header": details["header"],
            "lines": details["lines"],
            "approvals": details["approvals"],
        },
    )

    departments = get_collection_departments()

    return render(
        request,
        "requests_app/collection_inbox.html",
        {
            "rows": rows,
            "search": search,
            "request_number": request_number,
            "department": department,
            "date_from": date_from,
            "date_to": date_to,
            "departments": departments,
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


@sql_login_required
@feature_required("approvals")
def approval_detail(request, request_number):
    user_email = (request.user.email or "").strip()
    if not user_email:
        user_email = (request.user.username or "").strip()

    details = get_request_details(request_number, user_email)

    if not details:
        return render(
            request,
            "requests_app/approval_detail.html",
            {
                "not_found": True,
                "request_number": request_number,
            },
        )

    approval_history = get_approval_history(request_number)

    can_act = any(
        (row.get("ApproverEmail") or "").strip().lower() == user_email.lower()
        and row.get("ApprovalStatusName") == "Pending"
        and row.get("IsCurrent") in (1, True)
        for row in approval_history
    )

    return render(
        request,
        "requests_app/approval_detail.html",
        {
            "details": details,
            "header": details["header"],
            "lines": details["lines"],
            "approvals": details["approvals"],
            "approval_history": approval_history,
            "can_act": can_act,
        },
    )