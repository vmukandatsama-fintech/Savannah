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
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


def _safe_str(value: Any, default: str = "-") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _safe_num(value: Any, default: str = "-") -> str:
    if value is None or value == "":
        return default
    try:
        dec = Decimal(str(value))
        return f"{int(dec):,}"
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


def _get_logo_path() -> str | None:
    base_dir = getattr(settings, "BASE_DIR", "")

    candidates = [
        os.path.join(base_dir, "static", "img", "logo.png"),
        os.path.join(base_dir, "static", "images", "logo.png"),
        getattr(settings, "COLLECTION_VOUCHER_LOGO", ""),
    ]

    for path in candidates:
        if path and os.path.exists(path):
            print("LOGO FOUND:", path)
            return path

    print("LOGO NOT FOUND IN:", candidates)
    return None


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
                COALESCE(u.Name, c.DisbursedBy, '-') AS DisbursedBy,
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
            LEFT JOIN dbo.Users u
                ON u.Email = c.DisbursedBy
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


def _draw_wrapped_text(
    pdf: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    max_width: float,
    font_name: str = "Helvetica",
    font_size: float = 8.7,
    line_height: float = 4.2 * mm,
    max_lines: int | None = None,
) -> float:
    text = _safe_str(text, "")
    if not text:
        return y

    words = text.split()
    if not words:
        return y

    pdf.setFont(font_name, font_size)

    lines: list[str] = []
    current = ""

    for word in words:
        trial = word if not current else f"{current} {word}"
        if stringWidth(trial, font_name, font_size) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while stringWidth(last + "...", font_name, font_size) > max_width and last:
            last = last[:-1]
        lines[-1] = (last.rstrip() + "...") if last else "..."

    for line in lines:
        pdf.drawString(x, y, line)
        y -= line_height

    return y


def _draw_label_value_multiline(
    pdf: canvas.Canvas,
    label: str,
    value: Any,
    x: float,
    y: float,
    value_x: float,
    value_width: float,
    font_size: float = 8.7,
    max_lines: int | None = 2,
) -> float:
    pdf.setFont("Helvetica-Bold", 7.8)
    pdf.setFillColor(colors.HexColor("#4B5563"))
    pdf.drawString(x, y, label)

    pdf.setFillColor(colors.black)
    bottom_y = _draw_wrapped_text(
        pdf,
        _safe_str(value),
        value_x,
        y,
        value_width,
        font_name="Helvetica",
        font_size=font_size,
        line_height=4.2 * mm,
        max_lines=max_lines,
    )
    return bottom_y


def _draw_footer(
    pdf: canvas.Canvas,
    width: float,
    generated_on: str,
    page_number: int,
) -> None:
    footer_y = 10 * mm

    pdf.setStrokeColor(colors.HexColor("#D1D5DB"))
    pdf.setLineWidth(0.4)
    pdf.line(15 * mm, footer_y + 5 * mm, width - 15 * mm, footer_y + 5 * mm)

    pdf.setFont("Helvetica", 7.5)
    pdf.setFillColor(colors.HexColor("#6B7280"))
    pdf.drawString(15 * mm, footer_y, f"Generated on {generated_on}")
    pdf.drawRightString(width - 15 * mm, footer_y, f"Page {page_number}")


def build_collection_voucher_pdf(collection_number: str) -> str:
    data = get_voucher_data(collection_number)

    header = data.get("header", {}) or {}
    lines = data.get("lines", []) or []

    collection_no = _safe_str(header.get("CollectionNumber", collection_number))
    collection_date = header.get("CollectionDate")
    collection_date_display = _format_display_datetime(collection_date)
    request_no = _safe_str(header.get("RequestNumber"))

    farmer_name = _safe_str(header.get("Farmer") or header.get("FarmerName"))
    requested_by = _safe_str(header.get("RequestedBy") or header.get("RequestorEmail"))
    approver_name = _safe_str(header.get("Approver") or header.get("ApproverEmail"))
    authorizer_name = _safe_str(header.get("Authorizer") or header.get("AuthorizerEmail"))

    driver_name = _safe_str(header.get("DriverName"))
    driver_id = _safe_str(header.get("DriverID"))
    truck_reg = _safe_str(header.get("TruckRegistration"))
    trailer_reg = _safe_str(header.get("TrailerRegistration"))

    approval_comments = _safe_str(header.get("ApprovalComments"), default="")
    authorization_comments = _safe_str(header.get("AuthorizationComments"), default="")
    disbursed_by = _safe_str(header.get("DisbursedBy"))
    department_name = _safe_str(header.get("DepartmentName"))
    status_name = _safe_str(header.get("StatusName"))
    source_name = _safe_str(header.get("Source"), default="")

    generated_on = datetime.now().strftime("%d %b %Y %H:%M")

    folder = _voucher_folder_for_date(collection_date)
    file_name = f"{collection_no}_django.pdf"
    file_path = os.path.join(folder, file_name)

    _update_django_voucher_status(collection_number, "Generating", None, None)

    try:
        pdf = canvas.Canvas(file_path, pagesize=A4)
        width, height = A4
        page_number = 1

        margin_left = 15 * mm
        margin_right = 15 * mm
        top_margin = 14 * mm
        bottom_margin = 22 * mm
        content_width = width - margin_left - margin_right

        brand_primary = colors.HexColor("#1F2937")
        brand_muted = colors.HexColor("#6B7280")
        line_color = colors.HexColor("#D1D5DB")
        table_header_fill = colors.HexColor("#EEF2F7")
        table_alt_fill = colors.HexColor("#FAFAFA")

        logo_path = _get_logo_path()

        signature_block_height = 44 * mm

        def draw_page_frame(page_no: int) -> float:
            current_y = height - top_margin

            pdf.setTitle(f"Collection Voucher - {collection_no}")
            pdf.setAuthor("Savannah Stores")
            pdf.setSubject("Collection Voucher")

            header_top = current_y
            logo_drawn = False

            pdf.setFillColor(colors.black)
            pdf.setFont("Helvetica-Bold", 10)
            request_text = request_no
            pdf.drawString(margin_left, header_top - 1 * mm, request_text)

            collection_text_width = stringWidth(collection_no, "Helvetica-Bold", 10)
            collection_text_x = width - margin_right - collection_text_width
            pdf.drawString(collection_text_x, header_top - 1 * mm, collection_no)

            if logo_path:
                try:
                    logo = ImageReader(logo_path)
                    img_width_px, img_height_px = logo.getSize()

                    logo_height = 10 * mm
                    if img_height_px and img_width_px:
                        logo_width = logo_height * (img_width_px / img_height_px)
                    else:
                        logo_width = 10 * mm

                    pdf.drawImage(
                        logo,
                        margin_left,
                        header_top - 16 * mm,
                        width=logo_width,
                        height=logo_height,
                        preserveAspectRatio=True,
                        mask="auto",
                    )
                    logo_drawn = True
                except Exception as e:
                    print("LOGO DRAW ERROR:", repr(e))
                    logo_drawn = False
            else:
                print("LOGO PATH NOT FOUND")

            pdf.setFillColor(brand_primary)
            pdf.setFont("Helvetica-Bold", 16)
            title_text = "COLLECTION VOUCHER"
            title_width = stringWidth(title_text, "Helvetica-Bold", 16)
            title_x = (width - title_width) / 2
            pdf.drawString(title_x, header_top - 2 * mm, title_text)

            pdf.setFont("Helvetica", 8.5)
            pdf.setFillColor(brand_muted)
            subtitle = "Savannah Stores"
            subtitle_width = stringWidth(subtitle, "Helvetica", 8.5)
            subtitle_x = (width - subtitle_width) / 2
            pdf.drawString(subtitle_x, header_top - 7 * mm, subtitle)

            approx_modules = max(len(collection_no) * 11, 1)
            bar_width = collection_text_width / approx_modules
            bar_width = max(0.22, min(bar_width, 0.60))

            barcode = code128.Code128(
                collection_no,
                barHeight=10 * mm,
                barWidth=bar_width,
            )
            barcode.drawOn(pdf, collection_text_x, header_top - 16 * mm)

            header_rule_y = header_top - 19 * mm
            pdf.setStrokeColor(line_color)
            pdf.setLineWidth(0.7)
            pdf.line(margin_left, header_rule_y, width - margin_right, header_rule_y)

            _draw_footer(pdf, width, generated_on, page_no)
            return header_rule_y - 6 * mm

        def start_page() -> float:
            nonlocal page_number

            if page_number > 1:
                pdf.showPage()

            y = draw_page_frame(page_number)
            page_number += 1
            return y

        def ensure_space(current_y: float, required_height: float) -> float:
            if current_y - required_height < bottom_margin:
                return start_page()
            return current_y

        def draw_section_title(title: str, current_y: float) -> float:
            current_y = ensure_space(current_y, 10 * mm)

            pdf.setFillColor(brand_primary)
            pdf.setFont("Helvetica-Bold", 10.5)
            pdf.drawString(margin_left, current_y, title)

            pdf.setStrokeColor(line_color)
            pdf.setLineWidth(0.5)
            pdf.line(margin_left, current_y - 2.5 * mm, width - margin_right, current_y - 2.5 * mm)

            pdf.setFillColor(colors.black)
            return current_y - 7 * mm

        def draw_table_header(
            y: float,
            col_x: dict,
            col_widths: dict,
            row_height: float,
            table_width: float,
        ) -> float:
            pdf.setFillColor(table_header_fill)
            pdf.setStrokeColor(line_color)
            pdf.rect(margin_left, y - row_height + 1.2 * mm, table_width, row_height, fill=1, stroke=1)

            pdf.setFillColor(brand_primary)
            pdf.setFont("Helvetica-Bold", 7.2)

            pdf.drawString(col_x["line"] + 1.1 * mm, y - 4.4 * mm, "Ln")
            pdf.drawString(col_x["item_code"] + 1.1 * mm, y - 4.4 * mm, "Item Code")
            pdf.drawString(col_x["item_name"] + 1.1 * mm, y - 4.4 * mm, "Item Name")
            pdf.drawString(col_x["uom"] + 1.1 * mm, y - 4.4 * mm, "UOM")
            pdf.drawRightString(col_x["requested"] + col_widths["requested"] - 1.1 * mm, y - 4.4 * mm, "Requested")
            pdf.drawRightString(col_x["this_issue"] + col_widths["this_issue"] - 1.5 * mm, y - 4.4 * mm, "Issued")
            pdf.drawRightString(col_x["issued_total"] + col_widths["issued_total"] - 1.5 * mm, y - 4.4 * mm, "To Date")
            pdf.drawRightString(col_x["remaining"] + col_widths["remaining"] - 1.1 * mm, y - 4.4 * mm, "Remaining")

            return y - row_height

        def draw_signatures_at_bottom():
            section_y = bottom_margin + signature_block_height - 10 * mm

            pdf.setFillColor(brand_primary)
            pdf.setFont("Helvetica-Bold", 10.5)
            pdf.drawString(margin_left, section_y, "Authorisation and Confirmation")

            pdf.setStrokeColor(line_color)
            pdf.setLineWidth(0.5)
            pdf.line(margin_left, section_y - 2.5 * mm, width - margin_right, section_y - 2.5 * mm)

            sig_gap = 8 * mm
            sig_width = (content_width - (2 * sig_gap)) / 3

            stamp_space_driver = 20 * mm
            standard_space = 6 * mm

            base_line_y = bottom_margin + 0 * mm
            note_y = base_line_y - 4 * mm
            title_y = base_line_y + stamp_space_driver + 6 * mm

            blocks = [
                {"title": "Driver / Collector", "space": stamp_space_driver},
                {"title": "Warehouse Dispatch", "space": standard_space},
                {"title": "Security", "space": standard_space},
            ]

            for idx, block in enumerate(blocks):
                sig_x = margin_left + idx * (sig_width + sig_gap)

                pdf.setFont("Helvetica", 8)
                pdf.setFillColor(brand_muted)
                pdf.drawString(sig_x, title_y, block["title"])

                pdf.setStrokeColor(colors.black)
                pdf.setLineWidth(0.9)
                pdf.line(sig_x, base_line_y, sig_x + sig_width, base_line_y)

                pdf.setFont("Helvetica", 7)
                pdf.setFillColor(brand_muted)
                pdf.drawString(sig_x, note_y, "Name / Signature / Date")

        current_y = start_page()

        current_y = draw_section_title("Request Details", current_y)

        left_x = margin_left
        right_x = margin_left + (content_width / 2) + 4 * mm
        value_offset = 30 * mm
        value_width = (content_width / 2) - value_offset - 4 * mm

        row_bottom = min(
            _draw_label_value_multiline(
                pdf, "Request No", request_no, left_x, current_y, left_x + value_offset, value_width, max_lines=1
            ),
            _draw_label_value_multiline(
                pdf, "Date", collection_date_display, right_x, current_y, right_x + value_offset, value_width, max_lines=1
            ),
        )
        current_y = row_bottom - 2 * mm

        row_bottom = min(
            _draw_label_value_multiline(
                pdf, "Requested By", requested_by, left_x, current_y, left_x + value_offset, value_width, max_lines=2
            ),
            _draw_label_value_multiline(
                pdf, "Status", status_name, right_x, current_y, right_x + value_offset, value_width, max_lines=1
            ),
        )
        current_y = row_bottom - 2 * mm

        row_bottom = min(
            _draw_label_value_multiline(
                pdf, "Approver", approver_name, left_x, current_y, left_x + value_offset, value_width, max_lines=2
            ),
            _draw_label_value_multiline(
                pdf, "Authorizer", authorizer_name, right_x, current_y, right_x + value_offset, value_width, max_lines=2
            ),
        )
        current_y = row_bottom - 2 * mm

        if approval_comments or authorization_comments:
            row_bottom = min(
                _draw_label_value_multiline(
                    pdf,
                    "Approval Comments",
                    approval_comments or "-",
                    left_x,
                    current_y,
                    left_x + value_offset,
                    value_width,
                    font_size=8.5,
                    max_lines=3,
                ),
                _draw_label_value_multiline(
                    pdf,
                    "Auth Comments",
                    authorization_comments or "-",
                    right_x,
                    current_y,
                    right_x + value_offset,
                    value_width,
                    font_size=8.5,
                    max_lines=3,
                ),
            )
            current_y = row_bottom - 3 * mm

        current_y = draw_section_title("Collection Details", current_y)

        row_bottom = min(
            _draw_label_value_multiline(
                pdf, "Department", department_name, left_x, current_y, left_x + value_offset, value_width, max_lines=2
            ),
            _draw_label_value_multiline(
                pdf, "Disbursed By", disbursed_by, right_x, current_y, right_x + value_offset, value_width, max_lines=2
            ),
        )
        current_y = row_bottom - 2 * mm

        row_bottom = min(
            _draw_label_value_multiline(
                pdf, "Farmer", farmer_name, left_x, current_y, left_x + value_offset, value_width, max_lines=2
            ),
            _draw_label_value_multiline(
                pdf, "Driver", driver_name, right_x, current_y, right_x + value_offset, value_width, max_lines=2
            ),
        )
        current_y = row_bottom - 2 * mm

        row_bottom = min(
            _draw_label_value_multiline(
                pdf, "Driver ID", driver_id, left_x, current_y, left_x + value_offset, value_width, max_lines=1
            ),
            _draw_label_value_multiline(
                pdf, "Truck Reg", truck_reg, right_x, current_y, right_x + value_offset, value_width, max_lines=1
            ),
        )
        current_y = row_bottom - 2 * mm

        row_bottom = min(
            _draw_label_value_multiline(
                pdf, "Trailer Reg", trailer_reg, left_x, current_y, left_x + value_offset, value_width, max_lines=1
            ),
            _draw_label_value_multiline(
                pdf, "Source", source_name, right_x, current_y, right_x + value_offset, value_width, max_lines=1
            ),
        )
        current_y = row_bottom - 3 * mm

        current_y = draw_section_title("Items Issued", current_y)

        row_height = 7 * mm

        col_widths = {
            "line": 8 * mm,
            "item_code": 20 * mm,
            "item_name": 70 * mm,
            "uom": 11 * mm,
            "requested": 18 * mm,
            "this_issue": 20 * mm,
            "issued_total": 18 * mm,
            "remaining": 18 * mm,
        }

        col_x = {}
        running_x = margin_left
        for key, w in col_widths.items():
            col_x[key] = running_x
            running_x += w

        table_width = sum(col_widths.values())

        current_y = draw_table_header(current_y, col_x, col_widths, row_height, table_width)

        for idx, line in enumerate(lines, start=1):
            required_after_row = row_height + signature_block_height + 4 * mm
            if current_y - required_after_row < bottom_margin:
                current_y = start_page()
                current_y = draw_section_title("Items Issued (continued)", current_y)
                current_y = draw_table_header(current_y, col_x, col_widths, row_height, table_width)

            if idx % 2 == 0:
                pdf.setFillColor(table_alt_fill)
                pdf.setStrokeColor(line_color)
                pdf.rect(
                    margin_left,
                    current_y - row_height + 1.2 * mm,
                    table_width,
                    row_height,
                    fill=1,
                    stroke=0,
                )

            pdf.setFillColor(colors.black)
            pdf.setStrokeColor(colors.HexColor("#D7DCE2"))
            pdf.rect(
                margin_left,
                current_y - row_height + 1.2 * mm,
                table_width,
                row_height,
                fill=0,
                stroke=1,
            )

            line_value = _safe_str(line.get("LineNumber"), str(idx))
            item_code = _safe_str(line.get("ItemCode"))
            item_name = _safe_str(line.get("ItemName"))
            uom = _safe_str(line.get("UOM"))
            qty_requested = _safe_num(line.get("QuantityRequested"))
            qty_issue = _safe_num(line.get("ThisIssueQty"))
            qty_issued_total = _safe_num(line.get("TotalIssuedToDate"))
            qty_remaining = _safe_num(line.get("RemainingAfterIssue"))

            text_y = current_y - 4.6 * mm

            pdf.setFont("Helvetica", 7.4)
            pdf.drawString(col_x["line"] + 1.1 * mm, text_y, line_value)
            pdf.drawString(col_x["item_code"] + 1.1 * mm, text_y, item_code)

            max_item_name_width = col_widths["item_name"] - 2.2 * mm
            item_name_text = item_name
            while stringWidth(item_name_text, "Helvetica", 7.4) > max_item_name_width and len(item_name_text) > 1:
                item_name_text = item_name_text[:-1]
            if item_name_text != item_name:
                item_name_text = item_name_text.rstrip() + "…"

            pdf.drawString(col_x["item_name"] + 1.1 * mm, text_y, item_name_text)
            pdf.drawString(col_x["uom"] + 1.1 * mm, text_y, uom)
            pdf.drawRightString(col_x["requested"] + col_widths["requested"] - 1.1 * mm, text_y, qty_requested)
            pdf.drawRightString(col_x["this_issue"] + col_widths["this_issue"] - 1.1 * mm, text_y, qty_issue)
            pdf.drawRightString(col_x["issued_total"] + col_widths["issued_total"] - 1.1 * mm, text_y, qty_issued_total)
            pdf.drawRightString(col_x["remaining"] + col_widths["remaining"] - 1.1 * mm, text_y, qty_remaining)

            current_y -= row_height

        if current_y - signature_block_height < bottom_margin:
            current_y = start_page()

        draw_signatures_at_bottom()

        pdf.save()

        _update_django_voucher_status(collection_number, "Generated", file_path, None)
        return file_path

    except Exception as exc:
        _update_django_voucher_status(collection_number, "Failed", None, str(exc))
        raise