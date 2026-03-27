$target = ".\services\collection_voucher_service.py"

$content = @'
import os
from datetime import datetime
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db import connection

from reportlab.graphics.barcode import code128
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def _safe_str(value: Any, default: str = "-") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _safe_num(value: Any) -> str:
    if value is None or value == "":
        return "-"
    try:
        dec = Decimal(str(value))
        return f"{dec:,.0f}"
    except Exception:
        return str(value)


def _fetchone_dict(cursor):
    row = cursor.fetchone()
    if not row:
        return None
    cols = [col[0] for col in cursor.description]
    return dict(zip(cols, row))


def _fetchall_dict(cursor):
    cols = [col[0] for col in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value

    if value is None:
        return datetime.now()

    text = str(value).strip()
    if not text:
        return datetime.now()

    for fmt in (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(text)
    except Exception:
        return datetime.now()


def _format_display_datetime(value: Any) -> str:
    dt_value = _parse_datetime(value)
    return dt_value.strftime("%d %b %Y %H:%M")


def _update_django_voucher_status(
    collection_number: str,
    status: str,
    path: str | None = None,
    error: str | None = None,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE dbo.Collections
            SET
                DjangoVoucherStatus = %s,
                DjangoVoucherPath = %s,
                DjangoVoucherError = %s
            WHERE CollectionNumber = %s
            """,
            [status, path, error, collection_number],
        )


def _voucher_folder_for_date(dt_value: Any) -> str:
    dt_value = _parse_datetime(dt_value)

    year_part = dt_value.strftime("%Y")
    month_part = dt_value.strftime("%B")

    base_folder = getattr(
        settings,
        "COLLECTION_VOUCHER_ROOT",
        r"C:\Savannah\CollectionVouchers",
    )

    folder = os.path.join(base_folder, year_part, month_part)
    os.makedirs(folder, exist_ok=True)
    return folder


def get_collection_live_data(collection_number: str) -> dict:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT TOP 1
                c.CollectionNumber,
                c.CollectionDate,
                c.RequestNumber,

                c.Farmer,
                r.FarmerName,

                c.RequestedBy,
                r.RequestorEmail,

                c.Approver,
                r.ApproverEmail,

                c.Authorizer,
                r.AuthorizerEmail,

                c.DriverName,
                c.DriverID,
                c.TruckRegistration,
                c.TrailerRegistration,
                c.ApprovalComments,
                c.AuthorizationComments,
                c.DisbursedBy,
                c.Source,

                COALESCE(d.Name, r.DepartmentCode, '-') AS DepartmentName,
                COALESCE(r.StatusName, '-') AS StatusName,

                c.DjangoVoucherPath,
                c.DjangoVoucherStatus,
                c.DjangoVoucherError
            FROM dbo.Collections c
            LEFT JOIN dbo.Requests r
                ON r.RequestNumber = c.RequestNumber
            LEFT JOIN dbo.Departments d
                ON d.DepartmentCode = r.DepartmentCode
            WHERE c.CollectionNumber = %s
            """,
            [collection_number],
        )
        header = _fetchone_dict(cursor)

        cursor.execute(
            """
            SELECT
                ci.LineNumber,
                ci.ItemCode,
                ci.ItemName,
                ci.UOM,
                ci.QuantityRequested,
                ci.ThisIssueQty,
                ci.TotalIssuedToDate,
                ci.RemainingAfterIssue
            FROM dbo.CollectionItems ci
            WHERE ci.CollectionNumber = %s
            ORDER BY ci.LineNumber
            """,
            [collection_number],
        )
        lines = _fetchall_dict(cursor)

    if not header:
        raise ValueError(f"No live collection data found for {collection_number}")

    return {
        "header": header,
        "lines": lines,
    }


def get_voucher_data(collection_number: str) -> dict:
    return get_collection_live_data(collection_number)


def _draw_label_value(
    pdf: canvas.Canvas,
    label: str,
    value: Any,
    x: float,
    y: float,
    label_width: float = 34 * mm,
) -> None:
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(x, y, label)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(x + label_width, y, _safe_str(value))


def build_collection_voucher_pdf(collection_number: str) -> str:
    data = get_voucher_data(collection_number)

    header = data.get("header", {}) or {}
    lines = data.get("lines", []) or []

    print("VOUCHER HEADER DEBUG:", header)

    collection_no = _safe_str(header.get("CollectionNumber", collection_number))
    collection_date = header.get("CollectionDate")
    collection_date_display = _format_display_datetime(collection_date)
    request_no = _safe_str(header.get("RequestNumber"))

    farmer_name = _safe_str(
        header.get("Farmer") or header.get("FarmerName")
    )

    requested_by = _safe_str(
        header.get("RequestedBy") or header.get("RequestorEmail")
    )

    approver_name = _safe_str(
        header.get("Approver") or header.get("ApproverEmail")
    )

    authorizer_name = _safe_str(
        header.get("Authorizer") or header.get("AuthorizerEmail")
    )

    driver_name = _safe_str(header.get("DriverName"))
    driver_id = _safe_str(header.get("DriverID"))
    truck_reg = _safe_str(header.get("TruckRegistration"))
    trailer_reg = _safe_str(header.get("TrailerRegistration"))

    approval_comments = _safe_str(header.get("ApprovalComments"), default="")
    authorization_comments = _safe_str(header.get("AuthorizationComments"), default="")
    disbursed_by = _safe_str(header.get("DisbursedBy"))
    department_name = _safe_str(header.get("DepartmentName"))
    status_name = _safe_str(header.get("StatusName"))

    folder = _voucher_folder_for_date(collection_date)
    file_name = f"{collection_no}_django.pdf"
    file_path = os.path.join(folder, file_name)

    _update_django_voucher_status(collection_number, "Generating", None, None)

    try:
        pdf = canvas.Canvas(file_path, pagesize=A4)
        width, height = A4

        margin_left = 15 * mm
        margin_right = 15 * mm
        current_y = height - 16 * mm

        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(margin_left, current_y, "Collection Voucher")

        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawRightString(width - margin_right, current_y + 2, collection_no)

        barcode = code128.Code128(collection_no, barHeight=12 * mm, barWidth=0.38)
        barcode.drawOn(pdf, width - 72 * mm, current_y - 11 * mm)

        current_y -= 18 * mm

        pdf.setStrokeColor(colors.black)
        pdf.setLineWidth(0.6)
        pdf.line(margin_left, current_y, width - margin_right, current_y)
        current_y -= 6 * mm

        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(margin_left, current_y, "REQUEST DETAILS")
        current_y -= 7 * mm

        _draw_label_value(pdf, "REQUEST NO", request_no, margin_left, current_y)
        _draw_label_value(pdf, "DATE", collection_date_display, 105 * mm, current_y)
        current_y -= 6 * mm

        _draw_label_value(pdf, "REQUESTED BY", requested_by, margin_left, current_y)
        _draw_label_value(pdf, "STATUS", status_name, 105 * mm, current_y)
        current_y -= 6 * mm

        _draw_label_value(pdf, "APPROVER", approver_name, margin_left, current_y)
        _draw_label_value(pdf, "AUTHORIZER", authorizer_name, 105 * mm, current_y)
        current_y -= 6 * mm

        _draw_label_value(
            pdf,
            "APPROVAL COMMENTS",
            approval_comments,
            margin_left,
            current_y,
            label_width=38 * mm,
        )
        current_y -= 6 * mm

        _draw_label_value(
            pdf,
            "AUTH COMMENTS",
            authorization_comments,
            margin_left,
            current_y,
            label_width=38 * mm,
        )
        current_y -= 10 * mm

        pdf.line(margin_left, current_y, width - margin_right, current_y)
        current_y -= 6 * mm

        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(margin_left, current_y, "COLLECTION DETAILS")
        current_y -= 7 * mm

        _draw_label_value(pdf, "DEPARTMENT", department_name, margin_left, current_y)
        _draw_label_value(pdf, "DISBURSED BY", disbursed_by, 105 * mm, current_y)
        current_y -= 6 * mm

        _draw_label_value(pdf, "FARMER", farmer_name, margin_left, current_y)
        _draw_label_value(pdf, "DRIVER", driver_name, 105 * mm, current_y)
        current_y -= 6 * mm

        _draw_label_value(pdf, "DRIVER ID", driver_id, margin_left, current_y)
        _draw_label_value(pdf, "TRUCK REG", truck_reg, 105 * mm, current_y)
        current_y -= 6 * mm

        _draw_label_value(pdf, "TRAILER REG", trailer_reg, margin_left, current_y)
        current_y -= 10 * mm

        pdf.line(margin_left, current_y, width - margin_right, current_y)
        current_y -= 6 * mm

        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(margin_left, current_y, "AUTHORIZATION AND CONFIRMATION")
        current_y -= 12 * mm

        sig_width = (width - margin_left - margin_right - 20 * mm) / 3
        sig_titles = ["DRIVER / COLLECTOR", "WAREHOUSE DISPATCH", "SECURITY"]

        for idx, sig_title in enumerate(sig_titles):
            sig_x = margin_left + idx * (sig_width + 10 * mm)
            pdf.setFont("Helvetica", 8)
            pdf.drawString(sig_x, current_y, sig_title)
            pdf.line(sig_x, current_y - 10 * mm, sig_x + sig_width, current_y - 10 * mm)

        current_y -= 18 * mm

        pdf.line(margin_left, current_y, width - margin_right, current_y)
        current_y -= 7 * mm

        col_x = {
            "line": margin_left,
            "item_code": margin_left + 12 * mm,
            "item_name": margin_left + 36 * mm,
            "uom": margin_left + 110 * mm,
            "requested": margin_left + 130 * mm,
            "issue": margin_left + 152 * mm,
            "issued_total": margin_left + 174 * mm,
            "remaining": width - margin_right,
        }

        def draw_table_header(y_pos: float) -> float:
            pdf.setFont("Helvetica-Bold", 8)
            pdf.drawString(col_x["line"], y_pos, "Line")
            pdf.drawString(col_x["item_code"], y_pos, "Item Code")
            pdf.drawString(col_x["item_name"], y_pos, "Item Name")
            pdf.drawString(col_x["uom"], y_pos, "UOM")
            pdf.drawRightString(col_x["requested"] + 18 * mm, y_pos, "Requested")
            pdf.drawRightString(col_x["issue"] + 18 * mm, y_pos, "This Issue")
            pdf.drawRightString(col_x["issued_total"] + 12 * mm, y_pos, "Issued")
            pdf.drawRightString(col_x["remaining"], y_pos, "After Issue")

            y_pos -= 4 * mm
            pdf.line(margin_left, y_pos, width - margin_right, y_pos)
            y_pos -= 6 * mm
            pdf.setFont("Helvetica", 8.5)
            return y_pos

        current_y = draw_table_header(current_y)

        for line in lines:
            if current_y < 25 * mm:
                pdf.showPage()
                current_y = height - 20 * mm
                current_y = draw_table_header(current_y)

            pdf.drawString(col_x["line"], current_y, _safe_str(line.get("LineNumber")))
            pdf.drawString(col_x["item_code"], current_y, _safe_str(line.get("ItemCode")))
            pdf.drawString(col_x["item_name"], current_y, _safe_str(line.get("ItemName")))
            pdf.drawString(col_x["uom"], current_y, _safe_str(line.get("UOM")))
            pdf.drawRightString(
                col_x["requested"] + 18 * mm,
                current_y,
                _safe_num(line.get("QuantityRequested")),
            )
            pdf.drawRightString(
                col_x["issue"] + 18 * mm,
                current_y,
                _safe_num(line.get("ThisIssueQty")),
            )
            pdf.drawRightString(
                col_x["issued_total"] + 12 * mm,
                current_y,
                _safe_num(line.get("TotalIssuedToDate")),
            )
            pdf.drawRightString(
                col_x["remaining"],
                current_y,
                _safe_num(line.get("RemainingAfterIssue")),
            )

            current_y -= 6 * mm

        pdf.save()

        _update_django_voucher_status(collection_number, "Generated", file_path, None)
        return file_path

    except Exception as exc:
        _update_django_voucher_status(collection_number, "Failed", None, str(exc))
        raise
'@

if (-not (Test-Path ".\services")) {
    throw "services folder not found. Run this from the Savannah project root."
}

if (Test-Path $target) {
    Copy-Item $target "$target.bak" -Force
    Write-Host "Backup created: $target.bak"
}

Set-Content -Path $target -Value $content -Encoding UTF8

Write-Host "Updated: $target"
Write-Host "Next:"
Write-Host "1. Stop Django completely"
Write-Host "2. Start again: python manage.py runserver"
Write-Host "3. Regenerate the voucher"
Write-Host "4. Check terminal for: VOUCHER HEADER DEBUG"