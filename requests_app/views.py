import json
import os
import time
from io import BytesIO

import requests
from django.contrib import messages
from django.db import connection
from django.http import FileResponse, Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from openpyxl import Workbook

from core.decorators import feature_required, sql_login_required
from core.session_auth import get_session_user_email
from services.approval_service import get_approval_history, get_approval_inbox, process_approval
from services.collection_service import disburse_request as disburse_request_service, get_collection_departments, get_collection_detail, get_collection_history, get_collection_history_detail, get_pending_collections
from services.collection_voucher_service import build_collection_voucher_pdf
from services.department_report_service import get_department_consumption_detail, get_department_consumption_summary, get_department_list, get_department_summary_card, get_department_trends
from services.farmer_report_service import get_farmer_account_statement, get_farmer_collection_statement, get_farmer_departments, get_farmer_reports, get_farmer_summary
from services.farmer_service import get_active_farmers
from services.item_service import get_requestable_items
from services.request_details_service import get_request_details
from services.request_history_service import get_my_requests
from services.request_report_service import get_request_departments, get_request_exception_summary, get_request_exceptions, get_request_statuses, get_request_tracker
from services.request_service import create_request_from_cart
from services.return_service import cancel_remaining_balance, get_collection_return_detail, get_returnable_collections, post_return_stock
from services.reversal_report_service import get_reversal_reports
from services.stock_report_service import get_low_stock_report, get_stock_balance_report, get_stock_card, get_stock_categories, get_stock_item_summary
from services.user_service import get_user_context
from services.voucher_service import regenerate_collection_voucher

# =============================
# RETURNS AND REVERSALS MODULE
# =============================
def _apply_return_filters_from_request(request):
    return {
        "collection_number": (request.GET.get("collection_number") or "").strip(),
        "request_number": (request.GET.get("request_number") or "").strip(),
        "grower_number": (request.GET.get("grower_number") or "").strip(),
        "date_from": (request.GET.get("date_from") or "").strip(),
        "date_to": (request.GET.get("date_to") or "").strip(),
    }



def _build_reversal_workbook(rows):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Reversals"
    ws.append([
        "Transaction Date",
        "Item Code",
        "Reference",
        "Line Number",
        "Quantity",
        "Direction",
        "Transaction Type",
        "Responsible Department",
        "Performed By",
        "Notes",
    ])
    for row in rows:
        ws.append([
            row.get("TransactionDate"),
            row.get("ItemCode"),
            row.get("Reference"),
            row.get("LineNumber"),
            row.get("Quantity"),
            row.get("Direction"),
            row.get("TransactionType"),
            row.get("ResponsibleDepartment"),
            row.get("PerformedByEmail"),
            row.get("Notes"),
        ])
    return wb



@sql_login_required
@feature_required("collections")
def returns_list_view(request):
    filters = _apply_return_filters_from_request(request)
    rows = get_returnable_collections(
        collection_number=filters["collection_number"] or None,
        request_number=filters["request_number"] or None,
        grower_number=filters["grower_number"] or None,
        date_from=filters["date_from"] or None,
        date_to=filters["date_to"] or None,
    )
    return render(request, "requests_app/returns_list.html", {"rows": rows, "filters": filters})



@sql_login_required
@feature_required("collections")
def return_detail_view(request, collection_number):
    detail = get_collection_return_detail(collection_number)
    if not detail or not detail.get("header"):
        messages.error(request, f"Collection {collection_number} not found.")
        return redirect("returns_list")
    if request.method == "POST":
        reason = (request.POST.get("reason") or "").strip()
        line_items = []
        for line in detail["lines"]:
            field_name = f"return_qty_{line['LineNumber']}"
            raw_value = (request.POST.get(field_name) or "0").strip()
            try:
                return_qty = float(raw_value)
            except Exception:
                return_qty = 0
            if return_qty > 0:
                line_items.append({"LineNumber": line["LineNumber"], "ReturnQty": return_qty})
        if not line_items:
            messages.error(request, "Please enter at least one quantity to return.")
            return redirect("return_detail", collection_number=collection_number)
        if not reason:
            messages.error(request, "Return reason is required.")
            return redirect("return_detail", collection_number=collection_number)
        try:
            post_return_stock(
                collection_number=collection_number,
                returned_by=request.session.get("user_email"),
                reason=reason,
                line_items=line_items,
            )
            messages.success(request, f"Return posted successfully for {collection_number}.")
            return redirect("return_detail", collection_number=collection_number)
        except Exception as ex:
            messages.error(request, f"Return failed: {ex}")
            return redirect("return_detail", collection_number=collection_number)
    return render(request, "requests_app/return_detail.html", {"header": detail["header"], "lines": detail["lines"]})



@sql_login_required
@feature_required("collections")
@require_http_methods(["POST"])
def cancel_remaining_balance_view(request, request_number):
    reason = (request.POST.get("reason") or "").strip()
    if not reason:
        messages.error(request, "Cancellation reason is required.")
        return redirect("request_details", request_number=request_number)
    try:
        cancel_remaining_balance(
            request_number=request_number,
            cancelled_by=request.session.get("user_email"),
            reason=reason,
        )
        messages.success(request, f"Remaining balance cancelled for {request_number}.")
    except Exception as ex:
        messages.error(request, f"Cancel remaining balance failed: {ex}")
    return redirect("request_details", request_number=request_number)



@sql_login_required
@feature_required("reports")
def reversal_reports_view(request):
    filters = {
        "item_code": (request.GET.get("item_code") or "").strip(),
        "reference": (request.GET.get("reference") or "").strip(),
        "date_from": (request.GET.get("date_from") or "").strip(),
        "date_to": (request.GET.get("date_to") or "").strip(),
    }
    rows = get_reversal_reports(
        item_code=filters["item_code"] or None,
        reference=filters["reference"] or None,
        date_from=filters["date_from"] or None,
        date_to=filters["date_to"] or None,
    )
    return render(request, "requests_app/reversal_reports.html", {"rows": rows, "filters": filters})



@sql_login_required
@feature_required("reports")
def reversal_reports_export_excel_view(request):
    from io import BytesIO
    filters = {
        "item_code": (request.GET.get("item_code") or "").strip(),
        "reference": (request.GET.get("reference") or "").strip(),
        "date_from": (request.GET.get("date_from") or "").strip(),
        "date_to": (request.GET.get("date_to") or "").strip(),
    }
    rows = get_reversal_reports(
        item_code=filters["item_code"] or None,
        reference=filters["reference"] or None,
        date_from=filters["date_from"] or None,
        date_to=filters["date_to"] or None,
    )
    wb = _build_reversal_workbook(rows)
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="reversal_reports.xlsx"'
    return response



@sql_login_required
@feature_required("reports")
def reversal_reports_export_pdf_view(request):
    filters = {
        "item_code": (request.GET.get("item_code") or "").strip(),
        "reference": (request.GET.get("reference") or "").strip(),
        "date_from": (request.GET.get("date_from") or "").strip(),
        "date_to": (request.GET.get("date_to") or "").strip(),
    }
    rows = get_reversal_reports(
        item_code=filters["item_code"] or None,
        reference=filters["reference"] or None,
        date_from=filters["date_from"] or None,
        date_to=filters["date_to"] or None,
    )
    return render(request, "requests_app/reversal_reports_print.html", {"rows": rows, "filters": filters})



@sql_login_required
@feature_required("reports")
def department_trends_export_pdf_view(request):
    from django.shortcuts import render
    filters = _apply_department_filters_from_request(request)
    rows = get_department_trends(
        department_code=filters["department_code"] or None,
        date_from=filters["date_from"] or None,
        date_to=filters["date_to"] or None,
    )
    departments = get_department_list()
    return render(request, "requests_app/department_trends_print.html", {
        "rows": rows,
        "departments": departments,
        "filters": filters,
        "print_export": True,
    })



@sql_login_required
@feature_required("reports")
def department_report_detail_export_pdf_view(request, department_code):
    from django.shortcuts import render
    filters = _apply_department_filters_from_request(request)
    summary = get_department_summary_card(
        department_code=department_code,
        date_from=filters["date_from"] or None,
        date_to=filters["date_to"] or None,
    )
    rows = get_department_consumption_detail(
        department_code=department_code,
        date_from=filters["date_from"] or None,
        date_to=filters["date_to"] or None,
    )
    return render(request, "requests_app/department_report_detail_print.html", {
        "department": summary,
        "report_rows": rows,
        "date_from": filters["date_from"],
        "date_to": filters["date_to"],
        "print_export": True,
    })




def _apply_department_filters_from_request(request):
    return {
        "department_code": (request.GET.get("department_code") or "").strip(),
        "date_from": (request.GET.get("date_from") or "").strip(),
        "date_to": (request.GET.get("date_to") or "").strip(),
    }



def _build_department_summary_workbook(rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "Department Summary"
    headers = [
        "Department Code", "Department Name", "Request Count", "Collection Count", "Farmer Count", "Total Issued Qty", "Last Issue Date"
    ]
    ws.append(headers)
    for row in rows:
        ws.append([
            row.get("DepartmentCode"), row.get("DepartmentName"), row.get("RequestCount"), row.get("CollectionCount"), row.get("FarmerCount"), row.get("TotalIssuedQty"), row.get("LastIssueDate")
        ])
    return wb



def _build_department_detail_workbook(rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "Department Detail"
    headers = [
        "Department Code", "Department Name", "Item Code", "Item Name", "UOM", "Request Count", "Collection Count", "Farmer Count", "Total Issued Qty", "Last Issue Date"
    ]
    ws.append(headers)
    for row in rows:
        ws.append([
            row.get("DepartmentCode"), row.get("DepartmentName"), row.get("ItemCode"), row.get("ItemName"), row.get("UOM"), row.get("RequestCount"), row.get("CollectionCount"), row.get("FarmerCount"), row.get("TotalIssuedQty"), row.get("LastIssueDate")
        ])
    return wb



def _build_department_trends_workbook(rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "Department Trends"
    headers = [
        "Period Month", "Department Code", "Department Name", "Collection Count", "Request Count", "Total Issued Qty"
    ]
    ws.append(headers)
    for row in rows:
        ws.append([
            row.get("PeriodMonth"), row.get("DepartmentCode"), row.get("DepartmentName"), row.get("CollectionCount"), row.get("RequestCount"), row.get("TotalIssuedQty")
        ])
    return wb



@sql_login_required
@feature_required("reports")
def department_reports_view(request):
    filters = _apply_department_filters_from_request(request)
    rows = get_department_consumption_summary(
        department_code=filters["department_code"] or None,
        date_from=filters["date_from"] or None,
        date_to=filters["date_to"] or None,
    )
    departments = get_department_list()
    return render(
        request,
        "requests_app/department_reports.html",
        {
            "rows": rows,
            "departments": departments,
            "filters": filters,
        },
    )



@sql_login_required
@feature_required("reports")
def department_reports_export_excel_view(request):
    from io import BytesIO
    filters = _apply_department_filters_from_request(request)
    rows = get_department_consumption_summary(
        department_code=filters["department_code"] or None,
        date_from=filters["date_from"] or None,
        date_to=filters["date_to"] or None,
    )
    wb = _build_department_summary_workbook(rows)
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="department_reports_summary.xlsx"'
    return response



@sql_login_required
@feature_required("reports")
def department_report_detail_view(request, department_code):
    filters = _apply_department_filters_from_request(request)
    summary = get_department_summary_card(
        department_code=department_code,
        date_from=filters["date_from"] or None,
        date_to=filters["date_to"] or None,
    )
    rows = get_department_consumption_detail(
        department_code=department_code,
        date_from=filters["date_from"] or None,
        date_to=filters["date_to"] or None,
    )
    return render(
        request,
        "requests_app/department_report_detail.html",
        {
            "summary": summary,
            "rows": rows,
            "filters": filters,
        },
    )



@sql_login_required
@feature_required("reports")
def department_report_detail_export_excel_view(request, department_code):
    from io import BytesIO
    filters = _apply_department_filters_from_request(request)
    rows = get_department_consumption_detail(
        department_code=department_code,
        date_from=filters["date_from"] or None,
        date_to=filters["date_to"] or None,
    )
    wb = _build_department_detail_workbook(rows)
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    filename = f'department_detail_{_safe_filename(department_code)}.xlsx'
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response



@sql_login_required
@feature_required("reports")
def department_trends_view(request):
    filters = _apply_department_filters_from_request(request)
    rows = get_department_trends(
        department_code=filters["department_code"] or None,
        date_from=filters["date_from"] or None,
        date_to=filters["date_to"] or None,
    )
    departments = get_department_list()
    return render(
        request,
        "requests_app/department_trends.html",
        {
            "rows": rows,
            "departments": departments,
            "filters": filters,
        },
    )



@sql_login_required
@feature_required("reports")
def department_trends_export_excel_view(request):
    from io import BytesIO
    filters = _apply_department_filters_from_request(request)
    rows = get_department_trends(
        department_code=filters["department_code"] or None,
        date_from=filters["date_from"] or None,
        date_to=filters["date_to"] or None,
    )
    wb = _build_department_trends_workbook(rows)
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="department_trends.xlsx"'
    return response




def _apply_request_report_filters_from_request(request):
    return {
        "request_number": (request.GET.get("request_number") or "").strip(),
        "status_name": (request.GET.get("status_name") or "").strip(),
        "department_code": (request.GET.get("department_code") or "").strip(),
        "grower_number": (request.GET.get("grower_number") or "").strip(),
        "date_from": (request.GET.get("date_from") or "").strip(),
        "date_to": (request.GET.get("date_to") or "").strip(),
        "age_days": (request.GET.get("age_days") or "3").strip(),
    }



def _build_request_tracker_workbook(rows):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Request Tracker"
    ws.append([
        "Request Number",
        "Request Date",
        "Required Date",
        "Requested By",
        "Department Code",
        "Department Name",
        "Grower Number",
        "Farmer Name",
        "Status",
        "Total Requested",
        "Total Issued",
        "Total Reserved",
        "Balance Remaining",
        "Age Days",
    ])
    for row in rows:
        ws.append([
            row.get("RequestNumber"),
            row.get("RequestDate"),
            row.get("RequiredDate"),
            row.get("RequestedBy"),
            row.get("DepartmentCode"),
            row.get("DepartmentName"),
            row.get("GrowerNumber"),
            row.get("FarmerName"),
            row.get("StatusName"),
            row.get("TotalRequested"),
            row.get("TotalIssued"),
            row.get("TotalReserved"),
            row.get("BalanceRemaining"),
            row.get("AgeDays"),
        ])
    return wb



def _build_exception_workbook(rows):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Exceptions"
    ws.append([
        "Exception Type",
        "Request Number",
        "Request Date",
        "Required Date",
        "Requested By",
        "Department Name",
        "Grower Number",
        "Farmer Name",
        "Status",
        "Age Days",
        "Voucher Status",
        "Voucher Path",
        "Voucher Error",
    ])
    for row in rows:
        ws.append([
            row.get("ExceptionType"),
            row.get("RequestNumber"),
            row.get("RequestDate"),
            row.get("RequiredDate"),
            row.get("RequestedBy"),
            row.get("DepartmentName"),
            row.get("GrowerNumber"),
            row.get("FarmerName"),
            row.get("StatusName"),
            row.get("AgeDays"),
            row.get("VoucherStatus"),
            row.get("VoucherPath"),
            row.get("VoucherError"),
        ])
    return wb



@sql_login_required
@feature_required("reports")
def request_tracker_view(request):
    filters = _apply_request_report_filters_from_request(request)
    rows = get_request_tracker(
        request_number=filters["request_number"] or None,
        status_name=filters["status_name"] or None,
        department_code=filters["department_code"] or None,
        grower_number=filters["grower_number"] or None,
        date_from=filters["date_from"] or None,
        date_to=filters["date_to"] or None,
    )
    statuses = get_request_statuses()
    departments = get_request_departments()
    return render(
        request,
        "requests_app/request_tracker.html",
        {
            "rows": rows,
            "statuses": statuses,
            "departments": departments,
            "filters": filters,
        },
    )



@sql_login_required
@feature_required("reports")
def request_tracker_export_excel_view(request):
    from io import BytesIO
    filters = _apply_request_report_filters_from_request(request)
    rows = get_request_tracker(
        request_number=filters["request_number"] or None,
        status_name=filters["status_name"] or None,
        department_code=filters["department_code"] or None,
        grower_number=filters["grower_number"] or None,
        date_from=filters["date_from"] or None,
        date_to=filters["date_to"] or None,
    )
    wb = _build_request_tracker_workbook(rows)
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="request_tracker.xlsx"'
    return response



@sql_login_required
@feature_required("reports")
def request_tracker_export_pdf_view(request):
    from django.shortcuts import render
    filters = _apply_request_report_filters_from_request(request)
    rows = get_request_tracker(
        request_number=filters["request_number"] or None,
        status_name=filters["status_name"] or None,
        department_code=filters["department_code"] or None,
        grower_number=filters["grower_number"] or None,
        date_from=filters["date_from"] or None,
        date_to=filters["date_to"] or None,
    )
    return render(request, "requests_app/request_tracker_print.html", {
        "rows": rows,
        "filters": filters,
        "print_export": True,
    })



@sql_login_required
@feature_required("reports")
def exception_reports_view(request):
    filters = _apply_request_report_filters_from_request(request)
    try:
        age_days = int(filters["age_days"])
    except Exception:
        age_days = 3
    summary = get_request_exception_summary(age_days=age_days)
    rows = get_request_exceptions(age_days=age_days)
    return render(
        request,
        "requests_app/exception_reports.html",
        {
            "summary": summary,
            "rows": rows,
            "filters": filters,
        },
    )



@sql_login_required
@feature_required("reports")
def exception_reports_export_excel_view(request):
    from io import BytesIO
    filters = _apply_request_report_filters_from_request(request)
    try:
        age_days = int(filters["age_days"])
    except Exception:
        age_days = 3
    rows = get_request_exceptions(age_days=age_days)
    wb = _build_exception_workbook(rows)
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="request_exceptions.xlsx"'
    return response



@sql_login_required
@feature_required("reports")
def exception_reports_export_pdf_view(request):
    from django.shortcuts import render
    filters = _apply_request_report_filters_from_request(request)
    try:
        age_days = int(filters["age_days"])
    except Exception:
        age_days = 3
    summary = get_request_exception_summary(age_days=age_days)
    rows = get_request_exceptions(age_days=age_days)
    return render(request, "requests_app/exception_reports_print.html", {
        "summary": summary,
        "rows": rows,
        "filters": filters,
        "print_export": True,
    })



# ============================================================
# FARMER REPORTS
# ============================================================

# ============================================================
# STOCK REPORTS
# ============================================================
def _apply_stock_filters_from_request(request):
    return {
        "item_code": (request.GET.get("item_code") or "").strip(),
        "item_name": (request.GET.get("item_name") or "").strip(),
        "category_code": (request.GET.get("category_code") or "").strip(),
        "date_from": (request.GET.get("date_from") or "").strip(),
        "date_to": (request.GET.get("date_to") or "").strip(),
        "low_stock_only": (request.GET.get("low_stock_only") or "").strip(),
    }



def _build_stock_balance_workbook(rows, title="Stock Balance"):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = title[:31]
    ws.append([
        "Item Code",
        "Item Name",
        "Category Code",
        "Category Name",
        "UOM",
        "Physical Stock",
        "Reserved Qty",
        "Available Stock",
        "Min Stock Level",
        "Reorder Level",
        "Max Stock Level",
        "Is Low Stock",
    ])
    for row in rows:
        ws.append([
            row.get("ItemCode"),
            row.get("ItemName"),
            row.get("CategoryCode"),
            row.get("CategoryName"),
            row.get("UOMName") or row.get("UOMCode"),
            row.get("PhysicalStock"),
            row.get("ReservedQty"),
            row.get("AvailableStock"),
            row.get("MinStockLevel"),
            row.get("ReorderLevel"),
            row.get("MaxStockLevel"),
            "Yes" if row.get("IsLowStock") else "No",
        ])
    return wb



def _build_stock_card_workbook(summary, rows):
    from openpyxl import Workbook
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "Summary"
    ws1.append(["Field", "Value"])
    if summary:
        ws1.append(["Item Code", summary.get("ItemCode")])
        ws1.append(["Item Name", summary.get("ItemName")])
        ws1.append(["Category", summary.get("CategoryName")])
        ws1.append(["UOM", summary.get("UOMName") or summary.get("UOMCode")])
        ws1.append(["Physical Stock", summary.get("PhysicalStock")])
        ws1.append(["Reserved Qty", summary.get("ReservedQty")])
        ws1.append(["Available Stock", summary.get("AvailableStock")])
        ws1.append(["Min Stock Level", summary.get("MinStockLevel")])
        ws1.append(["Reorder Level", summary.get("ReorderLevel")])
        ws1.append(["Max Stock Level", summary.get("MaxStockLevel")])
    ws2 = wb.create_sheet("Stock Card")
    ws2.append([
        "Transaction Date",
        "Item Code",
        "Item Name",
        "Category Code",
        "Transaction Type",
        "Direction",
        "Signed Quantity",
    ])
    for row in rows:
        ws2.append([
            row.get("TransactionDate"),
            row.get("ItemCode"),
            row.get("ItemName"),
            row.get("CategoryCode"),
            row.get("TransactionType"),
            row.get("Direction"),
            row.get("SignedQuantity"),
        ])
    return wb


@sql_login_required
@feature_required("reports")
def stock_reports_view(request):
    filters = _apply_stock_filters_from_request(request)
    rows = get_stock_balance_report(
        item_code=filters["item_code"] or None,
        item_name=filters["item_name"] or None,
        category_code=filters["category_code"] or None,
        low_stock_only=(filters["low_stock_only"] == "1"),
    )
    categories = get_stock_categories()
    return render(
        request,
        "requests_app/stock_reports.html",
        {
            "rows": rows,
            "categories": categories,
            "filters": filters,
        },
    )



@sql_login_required
@feature_required("reports")
def stock_reports_export_excel_view(request):
    from io import BytesIO
    filters = _apply_stock_filters_from_request(request)
    rows = get_stock_balance_report(
        item_code=filters["item_code"] or None,
        item_name=filters["item_name"] or None,
        category_code=filters["category_code"] or None,
        low_stock_only=(filters["low_stock_only"] == "1"),
    )
    wb = _build_stock_balance_workbook(rows, "Stock Balance")
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="stock_balance_report.xlsx"'
    return response



@sql_login_required
@feature_required("reports")
def low_stock_report_view(request):
    filters = _apply_stock_filters_from_request(request)
    rows = get_low_stock_report(
        item_code=filters["item_code"] or None,
        item_name=filters["item_name"] or None,
        category_code=filters["category_code"] or None,
    )
    categories = get_stock_categories()
    return render(
        request,
        "requests_app/stock_reports.html",
        {
            "rows": rows,
            "categories": categories,
            "filters": filters,
            "page_title": "Low Stock Report",
            "is_low_stock_page": True,
        },
    )



@sql_login_required
@feature_required("reports")
def low_stock_report_export_excel_view(request):
    from io import BytesIO
    filters = _apply_stock_filters_from_request(request)
    rows = get_low_stock_report(
        item_code=filters["item_code"] or None,
        item_name=filters["item_name"] or None,
        category_code=filters["category_code"] or None,
    )
    wb = _build_stock_balance_workbook(rows, "Low Stock")
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="low_stock_report.xlsx"'
    return response



@sql_login_required
@feature_required("reports")
def stock_card_view(request, item_code):
    filters = _apply_stock_filters_from_request(request)
    summary = get_stock_item_summary(item_code)
    rows = get_stock_card(
        item_code=item_code,
        date_from=filters["date_from"] or None,
        date_to=filters["date_to"] or None,
    )
    return render(
        request,
        "requests_app/stock_card.html",
        {
            "summary": summary,
            "rows": rows,
            "filters": filters,
        },
    )



@sql_login_required
@feature_required("reports")
def stock_card_export_excel_view(request, item_code):
    from io import BytesIO
    filters = _apply_stock_filters_from_request(request)
    summary = get_stock_item_summary(item_code)
    rows = get_stock_card(
        item_code=item_code,
        date_from=filters["date_from"] or None,
        date_to=filters["date_to"] or None,
    )
    wb = _build_stock_card_workbook(summary, rows)
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="stock_card_{item_code}.xlsx"'
    return response



@sql_login_required
@feature_required("reports")
def stock_card_export_pdf_view(request, item_code):
    from django.shortcuts import render
    filters = _apply_stock_filters_from_request(request)
    summary = get_stock_item_summary(item_code)
    rows = get_stock_card(
        item_code=item_code,
        date_from=filters["date_from"] or None,
        date_to=filters["date_to"] or None,
    )
    return render(request, "requests_app/stock_card_print.html", {
        "summary": summary,
        "rows": rows,
        "filters": filters,
        "print_export": True,
    })



def _safe_filename(value):
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in str(value or "").strip())



def _apply_farmer_filters_from_request(request):
    return {
        "grower_number": (request.GET.get("grower_number") or "").strip(),
        "farmer_name": (request.GET.get("farmer_name") or "").strip(),
        "department_code": (request.GET.get("department_code") or "").strip(),
        "date_from": (request.GET.get("date_from") or "").strip(),
        "date_to": (request.GET.get("date_to") or "").strip(),
    }



def _build_farmer_summary_workbook(rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "Farmer Summary"
    headers = [
        "Grower Number", "Farmer Name", "Total Requested", "Total Issued", "Total Reserved", "Balance Remaining", "Request Count", "Last Transaction Date"
    ]
    ws.append(headers)
    for row in rows:
        ws.append([
            row.get("GrowerNumber"), row.get("FarmerName"), row.get("TotalRequested"), row.get("TotalIssued"), row.get("TotalReserved"), row.get("BalanceRemaining"), row.get("RequestCount"), row.get("LastTransactionDate")
        ])
    return wb



def _build_farmer_detail_workbook(summary, account_rows, collection_rows):
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "Summary"
    # ============================================================
    # FARMER REPORTS
    # ============================================================

    # ============================================================
    # STOCK REPORTS
    # ============================================================

    ws1.append(["Field", "Value"])
    ws1.append(["Grower Number", summary.get("GrowerNumber")])
    ws1.append(["Farmer Name", summary.get("FarmerName")])
    ws1.append(["Total Requested", summary.get("TotalRequested")])
    ws1.append(["Total Issued", summary.get("TotalIssued")])
    ws1.append(["Total Reserved", summary.get("TotalReserved")])
    ws1.append(["Balance Remaining", summary.get("BalanceRemaining")])
    ws1.append(["Request Count", summary.get("RequestCount")])
    ws1.append(["Last Transaction Date", summary.get("LastTransactionDate")])

    ws2 = wb.create_sheet("Outstanding")
    ws2.append([
        "Transaction Date", "Request Number", "Requested By", "Department", "Grower Number", "Farmer Name", "Line Number", "Item Code", "Item Name", "UOM", "Quantity Requested", "Quantity Issued", "Quantity Reserved", "Balance Remaining", "Status", "Stock Status"
    ])
    for row in account_rows:
        ws2.append([
            row.get("TransactionDate"), row.get("RequestNumber"), row.get("RequestedBy"), row.get("DepartmentName"), row.get("GrowerNumber"), row.get("FarmerName"), row.get("LineNumber"), row.get("ItemCode"), row.get("ItemName"), row.get("UOMName") or row.get("UOMCode"), row.get("QuantityRequested"), row.get("QuantityIssued"), row.get("QuantityReserved"), row.get("BalanceRemaining"), row.get("StatusName"), row.get("StockStatus")
        ])

    ws3 = wb.create_sheet("Collections")
    ws3.append([
        "Transaction Date", "Collection Number", "Request Number", "Requested By", "Department", "Grower Number", "Farmer Name", "Line Number", "Item Code", "Item Name", "UOM", "Quantity Requested", "This Issue Qty", "Total Issued To Date", "Remaining After Issue", "Status"
    ])
    for row in collection_rows:
        ws3.append([
            row.get("TransactionDate"), row.get("CollectionNumber"), row.get("RequestNumber"), row.get("RequestedBy"), row.get("DepartmentName"), row.get("GrowerNumber"), row.get("FarmerName"), row.get("LineNumber"), row.get("ItemCode"), row.get("ItemName"), row.get("UOM"), row.get("QuantityRequested"), row.get("ThisIssueQty"), row.get("TotalIssuedToDate"), row.get("RemainingAfterIssue"), row.get("StatusName")
        ])
    return wb



@sql_login_required
@feature_required("reports")
def farmer_reports_view(request):
    filters = _apply_farmer_filters_from_request(request)
    rows = get_farmer_reports(
        grower_number=filters["grower_number"] or None,
        farmer_name=filters["farmer_name"] or None,
        department_code=filters["department_code"] or None,
        date_from=filters["date_from"] or None,
        date_to=filters["date_to"] or None,
    )
    departments = get_farmer_departments()
    return render(
        request,
        "requests_app/farmer_reports.html",
        {
            "rows": rows,
            "departments": departments,
            "filters": filters,
        },
    )



@sql_login_required
@feature_required("reports")
def farmer_reports_export_excel_view(request):
    filters = _apply_farmer_filters_from_request(request)
    rows = get_farmer_reports(
        grower_number=filters["grower_number"] or None,
        farmer_name=filters["farmer_name"] or None,
        department_code=filters["department_code"] or None,
        date_from=filters["date_from"] or None,
        date_to=filters["date_to"] or None,
    )
    wb = _build_farmer_summary_workbook(rows)
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="farmer_reports_summary.xlsx"'
    return response



@sql_login_required
@feature_required("reports")
def farmer_report_detail_view(request, grower_number):
    date_from = (request.GET.get("date_from") or "").strip()
    date_to = (request.GET.get("date_to") or "").strip()
    summary = get_farmer_summary(
        grower_number=grower_number,
        date_from=date_from or None,
        date_to=date_to or None,
    )
    account_rows = get_farmer_account_statement(
        grower_number=grower_number,
        date_from=date_from or None,
        date_to=date_to or None,
    )
    collection_rows = get_farmer_collection_statement(
        grower_number=grower_number,
        date_from=date_from or None,
        date_to=date_to or None,
    )
    return render(
        request,
        "requests_app/farmer_report_detail.html",
        {
            "summary": summary,
            "account_rows": account_rows,
            "collection_rows": collection_rows,
            "filters": {
                "date_from": date_from,
                "date_to": date_to,
            },
        },
    )



@sql_login_required
@feature_required("reports")
def farmer_report_detail_export_excel_view(request, grower_number):
    date_from = (request.GET.get("date_from") or "").strip()
    date_to = (request.GET.get("date_to") or "").strip()
    summary = get_farmer_summary(
        grower_number=grower_number,
        date_from=date_from or None,
        date_to=date_to or None,
    )
    account_rows = get_farmer_account_statement(
        grower_number=grower_number,
        date_from=date_from or None,
        date_to=date_to or None,
    )
    collection_rows = get_farmer_collection_statement(
        grower_number=grower_number,
        date_from=date_from or None,
        date_to=date_to or None,
    )
    wb = _build_farmer_detail_workbook(summary, account_rows, collection_rows)
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    filename = f'farmer_statement_{_safe_filename(grower_number)}.xlsx'
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response



@sql_login_required
@feature_required("reports")
def farmer_report_detail_export_pdf_view(request, grower_number):
    from django.shortcuts import render
    date_from = (request.GET.get("date_from") or "").strip()
    date_to = (request.GET.get("date_to") or "").strip()
    summary = get_farmer_summary(
        grower_number=grower_number,
        date_from=date_from or None,
        date_to=date_to or None,
    )
    account_rows = get_farmer_account_statement(
        grower_number=grower_number,
        date_from=date_from or None,
        date_to=date_to or None,
    )
    collection_rows = get_farmer_collection_statement(
        grower_number=grower_number,
        date_from=date_from or None,
        date_to=date_to or None,
    )
    return render(request, "requests_app/farmer_report_print.html", {
        "summary": summary,
        "account_rows": account_rows,
        "collection_rows": collection_rows,
        "filters": {"date_from": date_from, "date_to": date_to},
        "print_export": True,
    })




# ============================================================
# REQUESTS

def _wait_for_voucher_path(collection_number, timeout_seconds=12, interval_seconds=1):
    """
    Poll collection detail briefly until VoucherPath becomes available.
    This handles async/slow SSRS generation updates.
    """
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        detail = get_collection_history_detail(collection_number)
        if detail and detail.get("header"):
            header = detail["header"]
            voucher_path = (header.get("VoucherPath") or "").strip()
            voucher_status = (header.get("VoucherStatus") or "").strip()

            if voucher_path:
                return {
                    "VoucherPath": voucher_path,
                    "VoucherStatus": voucher_status,
                    "VoucherError": header.get("VoucherError"),
                }

        time.sleep(interval_seconds)

    detail = get_collection_history_detail(collection_number)
    if detail and detail.get("header"):
        header = detail["header"]
        return {
            "VoucherPath": header.get("VoucherPath"),
            "VoucherStatus": header.get("VoucherStatus"),
            "VoucherError": header.get("VoucherError"),
        }

    return None


# ============================================================

@sql_login_required
@feature_required("create_request")
def request_cart(request):
    items_data = get_requestable_items()
    items = items_data["items"] if isinstance(items_data, dict) and "items" in items_data else items_data
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

        if not cart:
            return render(
                request,
                "requests_app/request_cart.html",
                {
                    "items": items,
                    "farmers": farmers,
                    "error_message": "Please add at least one item to the cart.",
                },
            )

        header = {
            "grower_number": request.POST.get("farmer"),
            "required_date": request.POST.get("required_date"),
            "collector_name": request.POST.get("collector_name"),
            "collector_national_id": request.POST.get("collector_national_id"),
            "truck_registration": request.POST.get("truck_registration"),
            "trailer_registration": request.POST.get("trailer_registration"),
            "authorization_required": 1 if request.POST.get("authorization_required") else 0,
            "department_code": user_context["DepartmentCode"],
            "justification": request.POST.get("justification"),
        }

        try:
            request_number = create_request_from_cart(
                user_email=user_email,
                header=header,
                cart=cart,
            )
            messages.success(request, f"Request {request_number} created successfully.")
            return redirect("my_requests")
        except Exception as ex:
            return render(
                request,
                "requests_app/request_cart.html",
                {
                    "items": items,
                    "farmers": farmers,
                    "error_message": str(ex),
                },
            )

    return render(
        request,
        "requests_app/request_cart.html",
        {
            "items": items,
            "farmers": farmers,
        },
    )



@sql_login_required
@feature_required("my_requests")
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



@sql_login_required
@feature_required("my_requests")
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



# ============================================================
# APPROVALS
# ============================================================

@sql_login_required
def approval_inbox(request):
    role_name = (request.session.get("role_name") or request.session.get("session_role_name") or "").strip()
    user_email = get_session_user_email(request)
    mode = (request.GET.get("mode") or "Pending").strip() or "Pending"

    can_view = role_name in ["Approver", "Authorizer", "Stores Controller"]
    if not can_view:
        messages.error(request, "You do not have access to the approval inbox.")
        return redirect("dashboard")

    show_all = role_name == "Stores Controller"

    approvals = get_approval_inbox(
        approver_email=user_email,
        mode=mode,
        show_all=show_all,
    )

    pending_count = len(
        [
            row for row in approvals
            if (row.get("ApprovalStatusName") or "").strip() == "Pending"
            and row.get("IsCurrent") in (1, True, "1", "True", "true")
        ]
    )

    return render(
        request,
        "requests_app/approval_inbox.html",
        {
            "approvals": approvals,
            "mode": mode,
            "pending_count": pending_count,
            "approval_view_all": show_all,
        },
    )



@sql_login_required
def approval_detail(request, request_number):
    role_name = (request.session.get("role_name") or request.session.get("session_role_name") or "").strip()
    user_email = get_session_user_email(request)

    can_view = role_name in ["Approver", "Authorizer", "Stores Controller"]
    if not can_view:
        messages.error(request, "You do not have access to approval details.")
        return redirect("dashboard")

    detail_email = None if role_name == "Stores Controller" else user_email
    details = get_request_details(request_number, detail_email)

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
        (row.get("ApproverEmail") or "").strip().lower() == (user_email or "").lower()
        and (row.get("ApprovalStatusName") or "").strip() == "Pending"
        and row.get("IsCurrent") in (1, True, "1", "True", "true")
        for row in approval_history
    )

    if role_name == "Stores Controller":
        can_act = False

    total_requested = sum(float(line.get("QuantityRequested") or 0) for line in details["lines"])
    total_issued = sum(float(line.get("QuantityIssued") or 0) for line in details["lines"])
    total_reserved = sum(float(line.get("QuantityReserved") or 0) for line in details["lines"])

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
            "approval_view_all": role_name == "Stores Controller",
            "total_requested": total_requested,
            "total_issued": total_issued,
            "total_reserved": total_reserved,
        },
    )



@sql_login_required
@require_http_methods(["POST"])
def approval_action(request, request_number):
    role_name = (request.session.get("role_name") or request.session.get("session_role_name") or "").strip()
    user_email = get_session_user_email(request)

    if role_name not in ["Approver", "Authorizer"]:
        messages.error(request, "You are not allowed to process approvals.")
        return redirect("approval_detail", request_number=request_number)

    decision = (request.POST.get("decision") or "").strip()
    comments = (request.POST.get("comments") or "").strip()

    if decision not in ["Approved", "Rejected"]:
        messages.error(request, "Invalid approval decision.")
        return redirect("approval_detail", request_number=request_number)

    try:
        process_approval(
            request_number=request_number,
            approver_email=user_email,
            decision=decision,
            comments=comments,
        )
        messages.success(request, "Approval processed successfully.")
    except Exception as ex:
        messages.error(request, str(ex))

    return redirect("approval_detail", request_number=request_number)



# ============================================================
# COLLECTIONS / DISBURSEMENT
# ============================================================

@sql_login_required
@feature_required("collections")
def collection_inbox(request):
    search = request.GET.get("search", "").strip()
    request_number = request.GET.get("request_number", "").strip()
    department = request.GET.get("department", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    rows = get_pending_collections(
        search=search,
        department_code=None,
        request_number=request_number,
        department_code_filter=department,
        date_from=date_from,
        date_to=date_to,
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
        # STEP 1: DISBURSE
        result = disburse_request_service(
            request_number=request_number,
            disbursed_by=get_session_user_email(request),
            issue_lines=issue_lines,
        )

        collection_number = (result or {}).get("CollectionNumber")
        print("DISBURSE RESULT:", result)

        if not collection_number:
            messages.error(
                request,
                f"Disbursement succeeded but no CollectionNumber was returned. Result: {result}"
            )
            return redirect("collection_history")

        # STEP 2: SSRS VOUCHER (existing)
        try:
            regenerate_collection_voucher(collection_number)
        except Exception as voucher_ex:
            messages.warning(
                request,
                f"SSRS voucher generation failed: {voucher_ex}"
            )

        # STEP 3: DJANGO VOUCHER (NEW 🔥)
        try:
            build_collection_voucher_pdf(collection_number)
        except Exception as django_ex:
            messages.warning(
                request,
                f"Django voucher generation failed: {django_ex}"
            )

        # STEP 4: WAIT FOR SSRS PATH (existing logic)
        voucher_info = _wait_for_voucher_path(
            collection_number,
            timeout_seconds=12,
            interval_seconds=1
        )

        voucher_path = (voucher_info or {}).get("VoucherPath")
        voucher_status = (voucher_info or {}).get("VoucherStatus")
        voucher_error = (voucher_info or {}).get("VoucherError")

        # STEP 5: FINAL UX
        if voucher_path:
            messages.success(
                request,
                f"Disbursement successful. Collection: {collection_number}. Voucher ready."
            )
            return redirect(f"/requests/collections/history/{collection_number}/?auto_open=1&auto_open_django=1")

        if voucher_status and voucher_status.lower() == "generated":
            messages.success(
                request,
                f"Disbursement successful. Collection: {collection_number}. Voucher ready."
            )
            return redirect(f"/requests/collections/history/{collection_number}/?auto_open=1&auto_open_django=1")

        if voucher_error:
            messages.warning(
                request,
                f"Disbursement successful. Collection: {collection_number}. Voucher error: {voucher_error}"
            )
        else:
            messages.warning(
                request,
                f"Disbursement successful. Collection: {collection_number}. Voucher still processing."
            )

        return redirect("collection_history_detail", collection_number=collection_number)

    except Exception as ex:
        messages.error(request, f"Error: {ex}")
        return redirect("collection_detail", request_number=request_number)

        voucher_info = _wait_for_voucher_path(collection_number, timeout_seconds=12, interval_seconds=1)
        voucher_path = (voucher_info or {}).get("VoucherPath")
        voucher_status = (voucher_info or {}).get("VoucherStatus")
        voucher_error = (voucher_info or {}).get("VoucherError")

        if voucher_path:
            messages.success(
                request,
                f"Disbursement successful. Collection Number: {collection_number}. Voucher generated."
            )
            return redirect(f"/requests/collections/history/{collection_number}/?auto_open=1")

        if voucher_status and voucher_status.lower() == "generated":
            messages.success(
                request,
                f"Disbursement successful. Collection Number: {collection_number}. Voucher generated."
            )
            return redirect(f"/requests/collections/history/{collection_number}/?auto_open=1")

        if voucher_error:
            messages.warning(
                request,
                f"Disbursement successful. Collection Number: {collection_number}. Voucher error: {voucher_error}"
            )
        else:
            messages.warning(
                request,
                f"Disbursement successful. Collection Number: {collection_number}. Voucher is still pending."
            )

        return redirect("collection_history_detail", collection_number=collection_number)

    except Exception as ex:
        messages.error(request, f"Error: {ex}")
        return redirect("collection_detail", request_number=request_number)



# ============================================================
# COLLECTION HISTORY
# ============================================================

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



# ============================================================
# VOUCHER ACTIONS LIKE DJANGO PRINTING
# ============================================================

def _get_django_voucher_path(collection_number: str) -> str | None:
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DjangoVoucherPath
            FROM Collections
            WHERE CollectionNumber = %s
        """, [collection_number])
        row = cursor.fetchone()
    return row[0] if row and row[0] else None



@sql_login_required
@feature_required("collections")
def regenerate_collection_voucher_django_view(request, collection_number):
    try:
        build_collection_voucher_pdf(collection_number)
        messages.success(request, f"Django voucher generated successfully for {collection_number}.")
        return redirect(f"/requests/collections/history/{collection_number}/?auto_open_django=1")
    except Exception as ex:
        messages.error(request, f"Django voucher generation failed: {ex}")
        return redirect("collection_history_detail", collection_number=collection_number)



@sql_login_required
@feature_required("collections")
def open_collection_voucher_django_view(request, collection_number):
    file_path = _get_django_voucher_path(collection_number)
    if not file_path or not os.path.exists(file_path):
        raise Http404("Django voucher file not found.")

    return FileResponse(open(file_path, "rb"), content_type="application/pdf")



@sql_login_required
@feature_required("collections")
def download_collection_voucher_django_view(request, collection_number):
    file_path = _get_django_voucher_path(collection_number)
    if not file_path or not os.path.exists(file_path):
        raise Http404("Django voucher file not found.")

    response = FileResponse(open(file_path, "rb"), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{os.path.basename(file_path)}"'
    return response



@sql_login_required
@feature_required("collections")
def regenerate_collection_voucher_view(request, collection_number):
    try:
        regenerate_collection_voucher(collection_number)
        voucher_info = _wait_for_voucher_path(collection_number, timeout_seconds=12, interval_seconds=1)

        voucher_path = (voucher_info or {}).get("VoucherPath")
        voucher_error = (voucher_info or {}).get("VoucherError")

        if voucher_path:
            messages.success(request, f"Voucher regenerated successfully for {collection_number}.")
            return redirect(f"/requests/collections/history/{collection_number}/?auto_open=1")

        if voucher_error:
            messages.warning(request, f"Voucher regeneration completed with error: {voucher_error}")
        else:
            messages.warning(request, "Voucher regeneration completed, but no voucher path was returned.")

    except Exception as ex:
        messages.error(request, f"Voucher regeneration failed: {ex}")

    return redirect("collection_history_detail", collection_number=collection_number)



@sql_login_required
@feature_required("collections")
def open_collection_voucher_view(request, collection_number):
    detail = get_collection_history_detail(collection_number)

    if not detail or not detail["header"].get("VoucherPath"):
        messages.error(request, "Voucher not found.")
        return redirect("collection_history_detail", collection_number=collection_number)

    voucher_path = detail["header"]["VoucherPath"]

    if voucher_path.lower().startswith(("http://", "https://")):
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

    if voucher_path.lower().startswith(("http://", "https://")):
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