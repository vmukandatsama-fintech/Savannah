$ErrorActionPreference = "Stop"

Write-Host "Adding Savannah request submit flow..." -ForegroundColor Cyan

Set-Location $PSScriptRoot

# Ensure template folder exists
if (!(Test-Path "templates\requests_app")) {
    New-Item -ItemType Directory -Path "templates\requests_app" | Out-Null
}

# 1. Write requests_app/views.py
$requestsViews = @'
import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


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

        header = {
            "farmer": request.POST.get("farmer", ""),
            "required_date": request.POST.get("required_date", ""),
            "collector_name": request.POST.get("collector_name", ""),
            "collector_national_id": request.POST.get("collector_national_id", ""),
            "truck_registration": request.POST.get("truck_registration", ""),
            "trailer_registration": request.POST.get("trailer_registration", ""),
            "authorization_required": request.POST.get("authorization_required", "0"),
            "department": request.POST.get("department", ""),
            "justification": request.POST.get("justification", ""),
        }

        total_qty = sum(int(float(item.get("qty", 0))) for item in cart) if cart else 0

        return render(request, "requests_app/request_confirm.html", {
            "header": header,
            "cart": cart,
            "cart_json": json.dumps(cart, indent=2),
            "total_lines": len(cart),
            "total_qty": total_qty,
        })

    return render(request, "requests_app/request_cart.html", {
        "items": sample_items
    })
'@
Set-Content -Path "requests_app\views.py" -Value $requestsViews -Encoding UTF8

# 2. Write templates/requests_app/request_confirm.html
$requestConfirmHtml = @'
{% extends 'base.html' %}

{% block content %}
<style>
    .confirm-card {
        background: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        margin-bottom: 20px;
    }
    .section-title {
        margin-bottom: 12px;
    }
    .detail-grid {
        display: grid;
        grid-template-columns: 220px 1fr;
        gap: 10px 16px;
    }
    .detail-label {
        color: #6b7280;
        font-weight: bold;
    }
    .cart-table {
        width: 100%;
        border-collapse: collapse;
    }
    .cart-table th,
    .cart-table td {
        padding: 10px;
        border-bottom: 1px solid #e5e7eb;
        text-align: left;
        font-size: 14px;
    }
    pre {
        background: #111827;
        color: #f9fafb;
        padding: 16px;
        border-radius: 10px;
        overflow-x: auto;
    }
    .btn {
        display: inline-block;
        background: #1f2937;
        color: white;
        text-decoration: none;
        padding: 10px 14px;
        border-radius: 8px;
    }
    .btn:hover {
        background: #111827;
    }
</style>

<h1>Request Confirmation</h1>
<p class="muted">This confirms Django is receiving the header and cart correctly.</p>

<div class="confirm-card">
    <h3 class="section-title">Header Details</h3>
    <div class="detail-grid">
        <div class="detail-label">Farmer</div><div>{{ header.farmer }}</div>
        <div class="detail-label">Required Date</div><div>{{ header.required_date }}</div>
        <div class="detail-label">Collector Name</div><div>{{ header.collector_name }}</div>
        <div class="detail-label">Collector National ID</div><div>{{ header.collector_national_id }}</div>
        <div class="detail-label">Truck Registration</div><div>{{ header.truck_registration }}</div>
        <div class="detail-label">Trailer Registration</div><div>{{ header.trailer_registration }}</div>
        <div class="detail-label">Authorization Required</div><div>{{ header.authorization_required }}</div>
        <div class="detail-label">Department</div><div>{{ header.department }}</div>
        <div class="detail-label">Justification</div><div>{{ header.justification }}</div>
    </div>
</div>

<div class="confirm-card">
    <h3 class="section-title">Cart Items</h3>
    <table class="cart-table">
        <thead>
            <tr>
                <th>Item Code</th>
                <th>Item Name</th>
                <th>Quantity</th>
                <th>UOM</th>
                <th>Available</th>
            </tr>
        </thead>
        <tbody>
            {% for item in cart %}
            <tr>
                <td>{{ item.code }}</td>
                <td>{{ item.name }}</td>
                <td>{{ item.qty }}</td>
                <td>{{ item.uom }}</td>
                <td>{{ item.available }}</td>
            </tr>
            {% empty %}
            <tr>
                <td colspan="5">No cart items submitted.</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <p><strong>Total Lines:</strong> {{ total_lines }}</p>
    <p><strong>Total Quantity:</strong> {{ total_qty }}</p>
</div>

<div class="confirm-card">
    <h3 class="section-title">Raw Cart JSON</h3>
    <pre>{{ cart_json }}</pre>
</div>

<a href="/requests/create/" class="btn">Back to Request Cart</a>
{% endblock %}
'@
Set-Content -Path "templates\requests_app\request_confirm.html" -Value $requestConfirmHtml -Encoding UTF8

Write-Host ""
Write-Host "Request submit preview flow added successfully." -ForegroundColor Green
Write-Host "Next run:" -ForegroundColor Cyan
Write-Host "python manage.py runserver"
Write-Host "Open: http://127.0.0.1:8000/requests/create/"
Write-Host "Add items and click Submit Request."