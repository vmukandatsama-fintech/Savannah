$ErrorActionPreference = "Stop"

$servicePath = ".\services\request_details_service.py"
$viewsPath = ".\requests_app\views.py"
$urlsPath = ".\requests_app\urls.py"
$templatePath = ".\templates\requests_app\request_details.html"
$historyTemplatePath = ".\templates\requests_app\my_requests.html"

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

foreach ($path in @($viewsPath, $urlsPath, $historyTemplatePath)) {
    if (-not (Test-Path $path)) {
        throw "Required file not found: $path"
    }
}

if (Test-Path $servicePath) {
    Copy-Item $servicePath "$servicePath.bak_$timestamp"
}
if (Test-Path $templatePath) {
    Copy-Item $templatePath "$templatePath.bak_$timestamp"
}

Copy-Item $viewsPath "$viewsPath.bak_$timestamp"
Copy-Item $urlsPath "$urlsPath.bak_$timestamp"
Copy-Item $historyTemplatePath "$historyTemplatePath.bak_$timestamp"

Write-Host "Backups created."

$serviceContent = @'
from django.db import connection


def get_request_details(request_number, user_email):
    header_sql = """
        SELECT TOP 1
            r.RequestNumber,
            r.RequestDate,
            r.RequiredDate,
            r.RequestorEmail,
            r.DepartmentCode,
            r.StatusName,
            r.AuthorizationRequired,
            r.Justification,
            r.CollectorName,
            r.CollectorNationalID,
            r.TruckRegistration,
            r.TrailerRegistration,
            r.GrowerNumber,
            r.FarmerName,
            r.CreatedAt
        FROM dbo.Requests r
        WHERE r.RequestNumber = %s
          AND r.RequestorEmail = %s
    """

    lines_sql = """
        SELECT
            ri.LineNumber,
            ri.ItemCode,
            i.Name AS ItemName,
            ri.QuantityRequested,
            ri.QuantityIssued,
            ri.QuantityReserved,
            ri.UOMCode,
            ri.StockStatus,
            ri.LineStatus
        FROM dbo.RequestedItems ri
        LEFT JOIN dbo.Inventory i
            ON ri.ItemCode = i.ItemCode
        WHERE ri.RequestNumber = %s
        ORDER BY ri.LineNumber
    """

    approvals_sql = """
        SELECT
            ApprovalLevel,
            ApproverEmail,
            ApprovalStatusName,
            ApprovalRole,
            IsCurrent,
            CreatedDate
        FROM dbo.Approvals
        WHERE RequestNumber = %s
        ORDER BY ApprovalLevel, ApproverEmail
    """

    with connection.cursor() as cursor:
        cursor.execute(header_sql, [request_number, user_email])
        header_row = cursor.fetchone()

        if not header_row:
            return None

        header_columns = [col[0] for col in cursor.description]
        header = dict(zip(header_columns, header_row))

        cursor.execute(lines_sql, [request_number])
        line_rows = cursor.fetchall()
        line_columns = [col[0] for col in cursor.description]
        lines = [dict(zip(line_columns, row)) for row in line_rows]

        cursor.execute(approvals_sql, [request_number])
        approval_rows = cursor.fetchall()
        approval_columns = [col[0] for col in cursor.description]
        approvals = [dict(zip(approval_columns, row)) for row in approval_rows]

    return {
        "header": header,
        "lines": lines,
        "approvals": approvals,
    }
'@

Set-Content -Path $servicePath -Value $serviceContent -Encoding UTF8
Write-Host "Created: $servicePath"

$viewsContent = @'
import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from services.farmer_service import get_active_farmers
from services.item_service import get_requestable_items
from services.request_details_service import get_request_details
from services.request_history_service import get_my_requests
from services.request_service import create_request_from_cart
from services.user_service import get_user_context


@login_required
def request_cart(request):
    items = get_requestable_items()
    farmers = get_active_farmers()

    user_email = (request.user.email or "").strip()
    if not user_email:
        user_email = (request.user.username or "").strip()

    user_context = get_user_context(user_email) if user_email else None

    if not user_context:
        return render(
            request,
            "requests_app/request_cart.html",
            {
                "items": items,
                "farmers": farmers,
                "error_message": "No active user context was found for your account.",
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
            "grower_number": request.POST.get("farmer", ""),
            "required_date": request.POST.get("required_date", ""),
            "collector_name": request.POST.get("collector_name", ""),
            "collector_national_id": request.POST.get("collector_national_id", ""),
            "truck_registration": request.POST.get("truck_registration", ""),
            "trailer_registration": request.POST.get("trailer_registration", ""),
            "authorization_required": 1 if request.POST.get("authorization_required") else 0,
            "department_code": user_context["DepartmentCode"],
            "justification": request.POST.get("justification", ""),
        }

        try:
            request_number = create_request_from_cart(
                user_email=user_email,
                header=header,
                cart=cart,
            )

            return render(
                request,
                "requests_app/request_success.html",
                {
                    "request_number": request_number,
                    "cart": cart,
                },
            )

        except Exception as e:
            return render(
                request,
                "requests_app/request_cart.html",
                {
                    "items": items,
                    "farmers": farmers,
                    "error_message": str(e),
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


@login_required
def my_requests(request):
    user_email = (request.user.email or "").strip()
    if not user_email:
        user_email = (request.user.username or "").strip()

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


@login_required
def request_details(request, request_number):
    user_email = (request.user.email or "").strip()
    if not user_email:
        user_email = (request.user.username or "").strip()

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
'@

Set-Content -Path $viewsPath -Value $viewsContent -Encoding UTF8
Write-Host "Updated: $viewsPath"

$urlsContent = @'
from django.urls import path
from . import views

urlpatterns = [
    path("create/", views.request_cart, name="request_cart"),
    path("my-requests/", views.my_requests, name="my_requests"),
    path("<str:request_number>/", views.request_details, name="request_details"),
]
'@

Set-Content -Path $urlsPath -Value $urlsContent -Encoding UTF8
Write-Host "Updated: $urlsPath"

$templateContent = @'
{% extends 'base.html' %}

{% block content %}
<div class="card">
    {% if not_found %}
        <h1>Request Not Found</h1>
        <p>No request details were found for {{ request_number }}.</p>
        <p><a href="/requests/my-requests/">Back to My Requests</a></p>
    {% else %}
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
            <div>
                <h1 style="margin:0;">Request Details</h1>
                <div class="muted">{{ header.RequestNumber }}</div>
            </div>
            <div>
                <a href="/requests/my-requests/">Back to My Requests</a>
            </div>
        </div>

        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:20px;">
            <div class="card" style="margin-bottom:0;">
                <div><strong>Request Number:</strong> {{ header.RequestNumber }}</div>
                <div><strong>Request Date:</strong> {{ header.RequestDate|date:"d-m-Y H:i" }}</div>
                <div><strong>Required Date:</strong> {{ header.RequiredDate|date:"d-m-Y" }}</div>
                <div><strong>Status:</strong> {{ header.StatusName }}</div>
            </div>

            <div class="card" style="margin-bottom:0;">
                <div><strong>Farmer:</strong> {{ header.FarmerName }}</div>
                <div><strong>Grower Number:</strong> {{ header.GrowerNumber }}</div>
                <div><strong>Department:</strong> {{ header.DepartmentCode }}</div>
                <div><strong>Requested By:</strong> {{ header.RequestorEmail }}</div>
            </div>

            <div class="card" style="margin-bottom:0;">
                <div><strong>Collector:</strong> {{ header.CollectorName }}</div>
                <div><strong>Collector ID:</strong> {{ header.CollectorNationalID }}</div>
                <div><strong>Truck:</strong> {{ header.TruckRegistration }}</div>
                <div><strong>Trailer:</strong> {{ header.TrailerRegistration|default:"-" }}</div>
            </div>
        </div>

        <div class="card">
            <h3>Justification</h3>
            <div>{{ header.Justification|default:"-" }}</div>
            <div style="margin-top:10px;">
                <strong>Authorization Required:</strong>
                {% if header.AuthorizationRequired %}Yes{% else %}No{% endif %}
            </div>
        </div>

        <div class="card">
            <h3>Requested Items</h3>
            <table style="width:100%;border-collapse:collapse;background:white;">
                <thead>
                    <tr>
                        <th style="text-align:left;padding:12px;border-bottom:1px solid #e5e7eb;">Line</th>
                        <th style="text-align:left;padding:12px;border-bottom:1px solid #e5e7eb;">Item Code</th>
                        <th style="text-align:left;padding:12px;border-bottom:1px solid #e5e7eb;">Item Name</th>
                        <th style="text-align:left;padding:12px;border-bottom:1px solid #e5e7eb;">Requested</th>
                        <th style="text-align:left;padding:12px;border-bottom:1px solid #e5e7eb;">Issued</th>
                        <th style="text-align:left;padding:12px;border-bottom:1px solid #e5e7eb;">Reserved</th>
                        <th style="text-align:left;padding:12px;border-bottom:1px solid #e5e7eb;">UOM</th>
                        <th style="text-align:left;padding:12px;border-bottom:1px solid #e5e7eb;">Stock Status</th>
                        <th style="text-align:left;padding:12px;border-bottom:1px solid #e5e7eb;">Line Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for line in lines %}
                    <tr>
                        <td style="padding:12px;border-bottom:1px solid #f1f5f9;">{{ line.LineNumber }}</td>
                        <td style="padding:12px;border-bottom:1px solid #f1f5f9;">{{ line.ItemCode }}</td>
                        <td style="padding:12px;border-bottom:1px solid #f1f5f9;">{{ line.ItemName }}</td>
                        <td style="padding:12px;border-bottom:1px solid #f1f5f9;">{{ line.QuantityRequested }}</td>
                        <td style="padding:12px;border-bottom:1px solid #f1f5f9;">{{ line.QuantityIssued }}</td>
                        <td style="padding:12px;border-bottom:1px solid #f1f5f9;">{{ line.QuantityReserved }}</td>
                        <td style="padding:12px;border-bottom:1px solid #f1f5f9;">{{ line.UOMCode }}</td>
                        <td style="padding:12px;border-bottom:1px solid #f1f5f9;">{{ line.StockStatus }}</td>
                        <td style="padding:12px;border-bottom:1px solid #f1f5f9;">{{ line.LineStatus }}</td>
                    </tr>
                    {% empty %}
                    <tr>
                        <td colspan="9" style="padding:12px;">No line items found.</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <div class="card">
            <h3>Approvals</h3>
            <table style="width:100%;border-collapse:collapse;background:white;">
                <thead>
                    <tr>
                        <th style="text-align:left;padding:12px;border-bottom:1px solid #e5e7eb;">Level</th>
                        <th style="text-align:left;padding:12px;border-bottom:1px solid #e5e7eb;">Approver</th>
                        <th style="text-align:left;padding:12px;border-bottom:1px solid #e5e7eb;">Role</th>
                        <th style="text-align:left;padding:12px;border-bottom:1px solid #e5e7eb;">Status</th>
                        <th style="text-align:left;padding:12px;border-bottom:1px solid #e5e7eb;">Current</th>
                        <th style="text-align:left;padding:12px;border-bottom:1px solid #e5e7eb;">Created</th>
                    </tr>
                </thead>
                <tbody>
                    {% for approval in approvals %}
                    <tr>
                        <td style="padding:12px;border-bottom:1px solid #f1f5f9;">{{ approval.ApprovalLevel }}</td>
                        <td style="padding:12px;border-bottom:1px solid #f1f5f9;">{{ approval.ApproverEmail }}</td>
                        <td style="padding:12px;border-bottom:1px solid #f1f5f9;">{{ approval.ApprovalRole }}</td>
                        <td style="padding:12px;border-bottom:1px solid #f1f5f9;">{{ approval.ApprovalStatusName }}</td>
                        <td style="padding:12px;border-bottom:1px solid #f1f5f9;">
                            {% if approval.IsCurrent %}Yes{% else %}No{% endif %}
                        </td>
                        <td style="padding:12px;border-bottom:1px solid #f1f5f9;">{{ approval.CreatedDate|date:"d-m-Y H:i" }}</td>
                    </tr>
                    {% empty %}
                    <tr>
                        <td colspan="6" style="padding:12px;">No approvals found.</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    {% endif %}
</div>
{% endblock %}
'@

Set-Content -Path $templatePath -Value $templateContent -Encoding UTF8
Write-Host "Created: $templatePath"

$historyContent = Get-Content $historyTemplatePath -Raw

if ($historyContent -notmatch 'request_details') {
    $historyContent = $historyContent -replace `
'<td style="padding:12px;border-bottom:1px solid #f1f5f9;">\{\{ row\.request_number \}\}</td>', `
'<td style="padding:12px;border-bottom:1px solid #f1f5f9;"><a href="{% url ''request_details'' row.request_number %}">{{ row.request_number }}</a></td>'

    Set-Content -Path $historyTemplatePath -Value $historyContent -Encoding UTF8
    Write-Host "Updated: $historyTemplatePath"
}
else {
    Write-Host "Request number link already exists in my_requests.html"
}

Write-Host ""
Write-Host "Request Details feature added."
Write-Host "Run:"
Write-Host "python manage.py runserver"
Write-Host "Then open:"
Write-Host "http://127.0.0.1:8000/requests/my-requests/"
Write-Host "Click any request number to view full details."