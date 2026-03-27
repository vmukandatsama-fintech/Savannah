from django.urls import path
from . import views

urlpatterns = [

    # ============================================================
    # RETURNS / REVERSALS
    # ============================================================
    path("returns/", views.returns_list_view, name="returns_list"),
    path("returns/<str:collection_number>/", views.return_detail_view, name="return_detail"),
    path("requests/<str:request_number>/cancel-remaining/", views.cancel_remaining_balance_view, name="cancel_remaining_balance"),

    path("reports/reversals/", views.reversal_reports_view, name="reversal_reports"),
    path("reports/reversals/export/excel/", views.reversal_reports_export_excel_view, name="reversal_reports_export_excel"),
    path("reports/reversals/export/pdf/", views.reversal_reports_export_pdf_view, name="reversal_reports_export_pdf"),

    # ============================================================
    # DEPARTMENT REPORTS
    # ============================================================
    path("reports/departments/", views.department_reports_view, name="department_reports"),
    path("reports/departments/export/excel/", views.department_reports_export_excel_view, name="department_reports_export_excel"),
    path("reports/departments/<str:department_code>/", views.department_report_detail_view, name="department_report_detail"),
    path("reports/departments/<str:department_code>/export/excel/", views.department_report_detail_export_excel_view, name="department_report_detail_export_excel"),
    path("reports/departments/<str:department_code>/export/pdf/", views.department_report_detail_export_pdf_view, name="department_report_detail_export_pdf"),

    path("reports/departments/trends/", views.department_trends_view, name="department_trends"),
    path("reports/departments/trends/export/excel/", views.department_trends_export_excel_view, name="department_trends_export_excel"),
    path("reports/departments/trends/export/pdf/", views.department_trends_export_pdf_view, name="department_trends_export_pdf"),

    # ============================================================
    # REQUEST TRACKER / EXCEPTIONS
    # ============================================================
    path("reports/request-tracker/", views.request_tracker_view, name="request_tracker"),
    path("reports/request-tracker/export/excel/", views.request_tracker_export_excel_view, name="request_tracker_export_excel"),
    path("reports/request-tracker/export/pdf/", views.request_tracker_export_pdf_view, name="request_tracker_export_pdf"),

    path("reports/exceptions/", views.exception_reports_view, name="exception_reports"),
    path("reports/exceptions/export/excel/", views.exception_reports_export_excel_view, name="exception_reports_export_excel"),
    path("reports/exceptions/export/pdf/", views.exception_reports_export_pdf_view, name="exception_reports_export_pdf"),

    # ============================================================
    # STOCK REPORTS
    # ============================================================
    path("reports/stock/", views.stock_reports_view, name="stock_reports"),
    path("reports/stock/export/excel/", views.stock_reports_export_excel_view, name="stock_reports_export_excel"),

    path("reports/stock/low-stock/", views.low_stock_report_view, name="low_stock_report"),
    path("reports/stock/low-stock/export/excel/", views.low_stock_report_export_excel_view, name="low_stock_report_export_excel"),

    path("reports/stock-card/<str:item_code>/", views.stock_card_view, name="stock_card"),
    path("reports/stock-card/<str:item_code>/export/excel/", views.stock_card_export_excel_view, name="stock_card_export_excel"),
    path("reports/stock-card/<str:item_code>/export/pdf/", views.stock_card_export_pdf_view, name="stock_card_export_pdf"),

    # ============================================================
    # FARMER REPORTS
    # ============================================================
    path("reports/farmers/", views.farmer_reports_view, name="farmer_reports"),
    path("reports/farmers/export/excel/", views.farmer_reports_export_excel_view, name="farmer_reports_export_excel"),
    path("reports/farmers/<str:grower_number>/", views.farmer_report_detail_view, name="farmer_report_detail"),
    path("reports/farmers/<str:grower_number>/export/excel/", views.farmer_report_detail_export_excel_view, name="farmer_report_detail_export_excel"),
    path("reports/farmers/<str:grower_number>/export/pdf/", views.farmer_report_detail_export_pdf_view, name="farmer_report_detail_export_pdf"),

    # ============================================================
    # REQUESTS
    # ============================================================
    path("create/", views.request_cart, name="request_cart"),
    path("my-requests/", views.my_requests, name="my_requests"),
    path("my-requests/<str:request_number>/", views.request_details, name="request_details"),

    # ============================================================
    # APPROVALS
    # ============================================================
    path("approvals/", views.approval_inbox, name="approval_inbox"),
    path("approvals/<str:request_number>/", views.approval_detail, name="approval_detail"),
    path("approvals/<str:request_number>/action/", views.approval_action, name="approval_action"),

    # ============================================================
    # COLLECTION HISTORY
    # ============================================================
    path("collections/history/", views.collection_history, name="collection_history"),
    path("collections/history/<str:collection_number>/", views.collection_history_detail, name="collection_history_detail"),

    # SSRS Voucher (existing - DO NOT TOUCH)
    path("collections/history/<str:collection_number>/regenerate-voucher/", views.regenerate_collection_voucher_view, name="regenerate_collection_voucher"),
    path("collections/history/<str:collection_number>/open-voucher/", views.open_collection_voucher_view, name="open_collection_voucher"),
    path("collections/history/<str:collection_number>/download-voucher/", views.download_collection_voucher_view, name="download_collection_voucher"),

    # Django Voucher (NEW PARALLEL FLOW)
    path("collections/history/<str:collection_number>/voucher/django/regenerate/", views.regenerate_collection_voucher_django_view, name="regenerate_collection_voucher_django"),
    path("collections/history/<str:collection_number>/voucher/django/open/", views.open_collection_voucher_django_view, name="open_collection_voucher_django"),
    path("collections/history/<str:collection_number>/voucher/django/download/", views.download_collection_voucher_django_view, name="download_collection_voucher_django"),

    # ============================================================
    # COLLECTION OPERATIONS
    # ============================================================
    path("collections/", views.collection_inbox, name="collection_inbox"),
    path("collections/<str:request_number>/", views.collection_detail, name="collection_detail"),
    path("collections/<str:request_number>/disburse/", views.disburse_request_view, name="disburse_request"),
]