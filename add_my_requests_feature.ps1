$ErrorActionPreference = "Stop"

$servicePath = ".\services\request_history_service.py"
$viewsPath = ".\requests_app\views.py"
$urlsPath = ".\requests_app\urls.py"
$templatePath = ".\templates\requests_app\my_requests.html"
$basePath = ".\templates\base.html"

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

foreach ($path in @($viewsPath, $urlsPath, $basePath)) {
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
Copy-Item $basePath "$basePath.bak_$timestamp"

Write-Host "Backups created."

$serviceContent = @'
from django.db import connection


def get_my_requests(user_email, search="", status="", page=1, page_size=10):
    page = max(int(page or 1), 1)
    page_size = max(int(page_size or 10), 1)
    offset = (page - 1) * page_size

    search = (search or "").strip()
    status = (status or "").strip()

    where_clauses = ["r.RequestorEmail = %s"]
    params = [user_email]

    if search:
        where_clauses.append("r.RequestNumber LIKE %s")
        params.append(f"%{search}%")

    if status:
        where_clauses.append("r.StatusName = %s")
        params.append(status)

    where_sql = " AND ".join(where_clauses)

    count_sql = f"""
        SELECT COUNT(1)
        FROM dbo.Requests r
        WHERE {where_sql}
    """

    data_sql = f"""
        SELECT
            r.RequestNumber,
            r.RequestDate,
            r.FarmerName,
            r.DepartmentCode,
            r.StatusName,
            COUNT(ri.LineItemID) AS TotalLines
        FROM dbo.Requests r
        LEFT JOIN dbo.RequestedItems ri
            ON r.RequestNumber = ri.RequestNumber
        WHERE {where_sql}
        GROUP BY
            r.RequestNumber,
            r.RequestDate,
            r.FarmerName,
            r.DepartmentCode,
            r.StatusName
        ORDER BY r.RequestDate DESC
        OFFSET %s ROWS FETCH NEXT %s ROWS ONLY
    """

    with connection.cursor() as cursor:
        cursor.execute(count_sql, params)
        total_count = cursor.fetchone()[0]

        cursor.execute(data_sql, params + [offset, page_size])
        rows = cursor.fetchall()

    requests = [
        {
            "request_number": row[0],
            "request_date": row[1],
            "farmer_name": row[2],
            "department_code": row[3],
            "status_name": row[4],
            "total_lines": row[5],
        }
        for row in rows
    ]

    return {
        "rows": requests,
        "page": page,
        "page_size": page_size,
        "total_count": total_count,
        "has_previous": page > 1,
        "has_next": (offset + page_size) < total_count,
        "previous_page": page - 1,
        "next_page": page + 1,
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
'@

Set-Content -Path $viewsPath -Value $viewsContent -Encoding UTF8
Write-Host "Updated: $viewsPath"

$urlsContent = @'
from django.urls import path
from . import views

urlpatterns = [
    path("create/", views.request_cart, name="request_cart"),
    path("my-requests/", views.my_requests, name="my_requests"),
]
'@

Set-Content -Path $urlsPath -Value $urlsContent -Encoding UTF8
Write-Host "Updated: $urlsPath"

$templateContent = @'
{% extends 'base.html' %}

{% block content %}
<div class="card">
    <h1>My Requests</h1>

    <form method="get" style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px;">
        <input type="text" name="search" value="{{ filters.search }}" placeholder="Request number" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;">
        
        <select name="status" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;">
            <option value="">All Statuses</option>
            <option value="Pending Approval" {% if filters.status == 'Pending Approval' %}selected{% endif %}>Pending Approval</option>
            <option value="Pending Collection" {% if filters.status == 'Pending Collection' %}selected{% endif %}>Pending Collection</option>
            <option value="Rejected" {% if filters.status == 'Rejected' %}selected{% endif %}>Rejected</option>
            <option value="Collected" {% if filters.status == 'Collected' %}selected{% endif %}>Collected</option>
        </select>

        <select name="page_size" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;">
            <option value="10" {% if filters.page_size == 10 %}selected{% endif %}>10</option>
            <option value="20" {% if filters.page_size == 20 %}selected{% endif %}>20</option>
            <option value="30" {% if filters.page_size == 30 %}selected{% endif %}>30</option>
        </select>

        <button type="submit">Apply</button>
    </form>

    <table style="width:100%;border-collapse:collapse;background:white;">
        <thead>
            <tr>
                <th style="text-align:left;padding:12px;border-bottom:1px solid #e5e7eb;">Request Number</th>
                <th style="text-align:left;padding:12px;border-bottom:1px solid #e5e7eb;">Date</th>
                <th style="text-align:left;padding:12px;border-bottom:1px solid #e5e7eb;">Farmer</th>
                <th style="text-align:left;padding:12px;border-bottom:1px solid #e5e7eb;">Department</th>
                <th style="text-align:left;padding:12px;border-bottom:1px solid #e5e7eb;">Status</th>
                <th style="text-align:left;padding:12px;border-bottom:1px solid #e5e7eb;">Total Lines</th>
            </tr>
        </thead>
        <tbody>
            {% for row in request_history.rows %}
            <tr>
                <td style="padding:12px;border-bottom:1px solid #f1f5f9;">{{ row.request_number }}</td>
                <td style="padding:12px;border-bottom:1px solid #f1f5f9;">{{ row.request_date|date:"d-m-Y H:i" }}</td>
                <td style="padding:12px;border-bottom:1px solid #f1f5f9;">{{ row.farmer_name }}</td>
                <td style="padding:12px;border-bottom:1px solid #f1f5f9;">{{ row.department_code }}</td>
                <td style="padding:12px;border-bottom:1px solid #f1f5f9;">{{ row.status_name }}</td>
                <td style="padding:12px;border-bottom:1px solid #f1f5f9;">{{ row.total_lines }}</td>
            </tr>
            {% empty %}
            <tr>
                <td colspan="6" style="padding:12px;">No requests found.</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <div style="display:flex;justify-content:space-between;align-items:center;margin-top:16px;">
        <div>Showing {{ request_history.rows|length }} of {{ request_history.total_count }}</div>
        <div>
            {% if request_history.has_previous %}
                <a href="?search={{ filters.search }}&status={{ filters.status }}&page_size={{ filters.page_size }}&page={{ request_history.previous_page }}" style="margin-right:12px;">Previous</a>
            {% endif %}
            {% if request_history.has_next %}
                <a href="?search={{ filters.search }}&status={{ filters.status }}&page_size={{ filters.page_size }}&page={{ request_history.next_page }}">Next</a>
            {% endif %}
        </div>
    </div>
</div>
{% endblock %}
'@

Set-Content -Path $templatePath -Value $templateContent -Encoding UTF8
Write-Host "Created: $templatePath"

$baseContent = Get-Content $basePath -Raw

if ($baseContent -notmatch '/requests/my-requests/') {
    $baseContent = $baseContent -replace (
        '<a href="/requests/create/">Requests</a>',
        '<a href="/requests/create/">Create Request</a>' + "`r`n" + '                <a href="/requests/my-requests/">My Requests</a>'
    )

    Set-Content -Path $basePath -Value $baseContent -Encoding UTF8
    Write-Host "Updated: $basePath"
}
else {
    Write-Host "Sidebar link already exists in base.html"
}

Write-Host ""
Write-Host "My Requests feature added."
Write-Host "Now run:"
Write-Host "python manage.py runserver"
Write-Host "Then open:"
Write-Host "http://127.0.0.1:8000/requests/my-requests/"