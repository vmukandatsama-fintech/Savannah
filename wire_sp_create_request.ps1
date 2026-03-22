$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Wiring Savannah request submit to sp_CreateRequest..." -ForegroundColor Cyan

# Ensure services folder exists
if (!(Test-Path "services")) {
    New-Item -ItemType Directory -Path "services" | Out-Null
}

# services/__init__.py
if (!(Test-Path "services\__init__.py")) {
    New-Item -ItemType File -Path "services\__init__.py" | Out-Null
}

# 1. services/request_service.py
$requestService = @'
import json
from django.db import connection


def create_request_from_cart(user_email, header, cart):
    cart_json = json.dumps([
        {
            "LineNumber": index + 1,
            "ItemCode": item["code"],
            "QuantityRequested": float(item["qty"]),
            "UOMCode": item["uom"],
        }
        for index, item in enumerate(cart)
    ])

    with connection.cursor() as cursor:
        cursor.execute(
            """
            EXEC sp_CreateRequest
                @RequestorEmail = %s,
                @DepartmentCode = %s,
                @RequiredDate = %s,
                @GrowerNumber = %s,
                @CollectorName = %s,
                @CollectorNationalID = %s,
                @TruckRegistration = %s,
                @TrailerRegistration = %s,
                @AuthorizationRequired = %s,
                @Justification = %s,
                @CartJson = %s
            """,
            [
                user_email,
                header["department_code"],
                header["required_date"],
                header["grower_number"],
                header["collector_name"],
                header["collector_national_id"],
                header["truck_registration"],
                header["trailer_registration"],
                header["authorization_required"],
                header["justification"],
                cart_json,
            ]
        )

        row = cursor.fetchone()
        if row:
            return row[0]

    return None
'@
Set-Content -Path "services\request_service.py" -Value $requestService -Encoding UTF8

# 2. requests_app/views.py
$requestsViews = @'
import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from services.request_service import create_request_from_cart


@login_required
def request_cart(request):
    sample_items = [
        {"code": "ITM001", "name": "Compound D", "uom": "BAG", "available": 120},
        {"code": "ITM002", "name": "Ammonium Nitrate", "uom": "BAG", "available": 85},
        {"code": "ITM003", "name": "Twine", "uom": "EA", "available": 240},
        {"code": "ITM004", "name": "Chemical A", "uom": "LTR", "available": 40},
        {"code": "ITM005", "name": "Seed Maize", "uom": "BAG", "available": 15},
    ]

    if request.method == "POST":
        cart_json = request.POST.get("cart_json", "[]")

        try:
            cart = json.loads(cart_json)
        except json.JSONDecodeError:
            cart = []

        if not cart:
            return render(request, "requests_app/request_cart.html", {
                "items": sample_items,
                "error_message": "Please add at least one item to the cart."
            })

        header = {
            "grower_number": request.POST.get("farmer", ""),
            "required_date": request.POST.get("required_date", ""),
            "collector_name": request.POST.get("collector_name", ""),
            "collector_national_id": request.POST.get("collector_national_id", ""),
            "truck_registration": request.POST.get("truck_registration", ""),
            "trailer_registration": request.POST.get("trailer_registration", ""),
            "authorization_required": request.POST.get("authorization_required", "0"),
            "department_code": "DEP-005",
            "justification": request.POST.get("justification", ""),
        }

        try:
            request_number = create_request_from_cart(
                user_email="vmukandatsama@premiumzimbabwe.com",
                header=header,
                cart=cart,
            )

            return render(request, "requests_app/request_success.html", {
                "request_number": request_number,
                "cart": cart,
            })

        except Exception as e:
            return render(request, "requests_app/request_cart.html", {
                "items": sample_items,
                "error_message": str(e),
            })

    return render(request, "requests_app/request_cart.html", {
        "items": sample_items
    })
'@
Set-Content -Path "requests_app\views.py" -Value $requestsViews -Encoding UTF8

# 3. Ensure templates folder exists
if (!(Test-Path "templates\requests_app")) {
    New-Item -ItemType Directory -Path "templates\requests_app" | Out-Null
}

# 4. templates/requests_app/request_success.html
$requestSuccess = @'
{% extends 'base.html' %}

{% block content %}
<div class="card">
    <h1>Request Submitted</h1>
    <p class="muted">Your request has been created successfully.</p>

    <p><strong>Request Number:</strong> {{ request_number }}</p>

    <h3>Submitted Items</h3>
    <table class="cart-table">
        <thead>
            <tr>
                <th>Item Code</th>
                <th>Item Name</th>
                <th>Qty</th>
                <th>UOM</th>
            </tr>
        </thead>
        <tbody>
            {% for item in cart %}
            <tr>
                <td>{{ item.code }}</td>
                <td>{{ item.name }}</td>
                <td>{{ item.qty }}</td>
                <td>{{ item.uom }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <div style="margin-top: 20px;">
        <a href="/requests/create/" class="btn">Create Another Request</a>
    </div>
</div>

<style>
    .cart-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 12px;
    }
    .cart-table th,
    .cart-table td {
        padding: 10px;
        border-bottom: 1px solid #e5e7eb;
        text-align: left;
    }
    .btn {
        display: inline-block;
        background: #1f2937;
        color: white;
        text-decoration: none;
        padding: 10px 14px;
        border-radius: 8px;
    }
</style>
{% endblock %}
'@
Set-Content -Path "templates\requests_app\request_success.html" -Value $requestSuccess -Encoding UTF8

# 5. Add error block to request_cart.html if missing
$requestCartPath = "templates\requests_app\request_cart.html"
if (Test-Path $requestCartPath) {
    $content = Get-Content $requestCartPath -Raw
    $marker = "<div class=`"page-header`">"
    $errorBlock = @'
{% if error_message %}
<div style="background:#fee2e2; color:#991b1b; padding:12px; border-radius:8px; margin-bottom:16px;">
    {{ error_message }}
</div>
{% endif %}
'@

    if ($content -notmatch [regex]::Escape("{{ error_message }}")) {
        $replacement = @"
$marker
$errorBlock
"@
        $content = $content -replace [regex]::Escape($marker), [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $replacement }
        Set-Content -Path $requestCartPath -Value $content -Encoding UTF8
    }
}

Write-Host ""
Write-Host "Stored procedure wiring files written." -ForegroundColor Green
Write-Host "Next:" -ForegroundColor Cyan
Write-Host "1. python manage.py runserver"
Write-Host "2. Open http://127.0.0.1:8000/requests/create/"
Write-Host "3. Submit a test request"