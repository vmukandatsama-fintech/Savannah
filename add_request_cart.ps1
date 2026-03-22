$ErrorActionPreference = "Stop"

Write-Host "Adding Savannah Request Cart module..." -ForegroundColor Cyan

Set-Location $PSScriptRoot

# Ensure folders exist
$folders = @(
    "requests_app",
    "templates",
    "templates\requests_app"
)

foreach ($folder in $folders) {
    if (!(Test-Path $folder)) {
        New-Item -ItemType Directory -Path $folder | Out-Null
    }
}

# 1. Write requests_app/urls.py
$requestsUrls = @'
from django.urls import path
from .views import request_cart

urlpatterns = [
    path("create/", request_cart, name="request_cart"),
]
'@
Set-Content -Path "requests_app\urls.py" -Value $requestsUrls -Encoding UTF8

# 2. Write requests_app/views.py
$requestsViews = @'
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

    return render(request, "requests_app/request_cart.html", {
        "items": sample_items
    })
'@
Set-Content -Path "requests_app\views.py" -Value $requestsViews -Encoding UTF8

# 3. Update config/urls.py
$configUrls = @'
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(url="/login/", permanent=False)),
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("requests/", include("requests_app.urls")),
]
'@
Set-Content -Path "config\urls.py" -Value $configUrls -Encoding UTF8

# 4. Update templates/base.html
$baseHtml = @'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Savannah Stores</title>
    <style>
        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #f4f6f8;
        }
        .topbar {
            background: #1f2937;
            color: white;
            padding: 14px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .layout {
            display: flex;
            min-height: calc(100vh - 52px);
        }
        .sidebar {
            width: 240px;
            background: #111827;
            color: white;
            padding: 20px 0;
        }
        .sidebar a {
            display: block;
            color: white;
            text-decoration: none;
            padding: 12px 20px;
        }
        .sidebar a:hover {
            background: #1f2937;
        }
        .content {
            flex: 1;
            padding: 24px;
        }
        .card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            margin-bottom: 20px;
        }
        .login-wrap {
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #f4f6f8;
        }
        .login-card {
            width: 360px;
            background: white;
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        input[type="text"], input[type="password"] {
            width: 100%;
            padding: 10px;
            margin-top: 6px;
            margin-bottom: 16px;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            box-sizing: border-box;
        }
        button {
            background: #1f2937;
            color: white;
            border: none;
            padding: 10px 16px;
            border-radius: 8px;
            cursor: pointer;
        }
        button:hover {
            background: #111827;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
        }
        .stat-box {
            background: white;
            padding: 18px;
            border-radius: 10px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }
        .muted {
            color: #6b7280;
            font-size: 14px;
        }
        .errorlist {
            color: #b91c1c;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    {% if user.is_authenticated %}
        <div class="topbar">
            <div><strong>Savannah Stores</strong></div>
            <div>
                {{ user.username }} |
                <a href="{% url 'logout' %}" style="color:white;">Logout</a>
            </div>
        </div>

        <div class="layout">
            <div class="sidebar">
                <a href="/dashboard/">Dashboard</a>
                <a href="/requests/create/">Requests</a>
                <a href="#">Collections</a>
                <a href="#">Stock</a>
                <a href="#">Reports</a>
            </div>

            <div class="content">
                {% block content %}{% endblock %}
            </div>
        </div>
    {% else %}
        {% block auth_content %}{% endblock %}
    {% endif %}
</body>
</html>
'@
Set-Content -Path "templates\base.html" -Value $baseHtml -Encoding UTF8

# 5. Write templates/requests_app/request_cart.html
$requestCartHtml = @'
{% extends 'base.html' %}

{% block content %}
<style>
    .page-header {
        margin-bottom: 20px;
    }

    .request-header-card,
    .catalog-card,
    .cart-card {
        background: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        margin-bottom: 20px;
    }

    .request-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
    }

    .request-grid .full-width {
        grid-column: span 4;
    }

    .field label {
        display: block;
        font-size: 14px;
        margin-bottom: 6px;
        color: #374151;
    }

    .field input,
    .field select,
    .field textarea {
        width: 100%;
        padding: 10px;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        box-sizing: border-box;
    }

    .field textarea {
        min-height: 80px;
        resize: vertical;
    }

    .cart-layout {
        display: grid;
        grid-template-columns: 1.5fr 1fr;
        gap: 20px;
        align-items: start;
    }

    .catalog-list {
        display: grid;
        gap: 12px;
    }

    .item-card {
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 14px;
        display: grid;
        grid-template-columns: 2fr 100px 100px 110px;
        gap: 12px;
        align-items: center;
    }

    .item-name {
        font-weight: bold;
    }

    .item-meta {
        color: #6b7280;
        font-size: 13px;
        margin-top: 4px;
    }

    .qty-box input {
        width: 100%;
        padding: 8px;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        box-sizing: border-box;
    }

    .btn {
        background: #1f2937;
        color: white;
        border: none;
        padding: 10px 14px;
        border-radius: 8px;
        cursor: pointer;
    }

    .btn:hover {
        background: #111827;
    }

    .btn-light {
        background: #e5e7eb;
        color: #111827;
    }

    .btn-light:hover {
        background: #d1d5db;
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

    .cart-summary {
        margin-top: 16px;
        padding-top: 16px;
        border-top: 1px solid #e5e7eb;
    }

    .actions-row {
        display: flex;
        gap: 10px;
        margin-top: 16px;
    }

    .muted-small {
        color: #6b7280;
        font-size: 13px;
    }

    .danger-link {
        color: #b91c1c;
        cursor: pointer;
        text-decoration: none;
        font-size: 13px;
    }

    .search-box {
        margin-bottom: 16px;
    }

    .search-box input {
        width: 100%;
        padding: 10px;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        box-sizing: border-box;
    }
</style>

<div class="page-header">
    <h1>Create Request</h1>
    <p class="muted">Build a request like a shopping cart.</p>
</div>

<form method="post" id="requestForm">
    {% csrf_token %}

    <div class="request-header-card">
        <h3>Request Header</h3>
        <div class="request-grid">
            <div class="field">
                <label>Farmer</label>
                <input type="text" name="farmer" placeholder="Enter farmer name or code">
            </div>
            <div class="field">
                <label>Required Date</label>
                <input type="date" name="required_date">
            </div>
            <div class="field">
                <label>Collector Name</label>
                <input type="text" name="collector_name">
            </div>
            <div class="field">
                <label>Collector National ID</label>
                <input type="text" name="collector_national_id">
            </div>

            <div class="field">
                <label>Truck Registration</label>
                <input type="text" name="truck_registration">
            </div>
            <div class="field">
                <label>Trailer Registration</label>
                <input type="text" name="trailer_registration">
            </div>
            <div class="field">
                <label>Authorization Required</label>
                <select name="authorization_required">
                    <option value="0">No</option>
                    <option value="1">Yes</option>
                </select>
            </div>
            <div class="field">
                <label>Department</label>
                <input type="text" name="department" value="Stores" readonly>
            </div>

            <div class="field full-width">
                <label>Justification</label>
                <textarea name="justification" placeholder="Enter reason for request"></textarea>
            </div>
        </div>
    </div>

    <div class="cart-layout">
        <div class="catalog-card">
            <h3>Item Catalog</h3>
            <div class="search-box">
                <input type="text" id="itemSearch" placeholder="Search items by code or name">
            </div>

            <div class="catalog-list" id="catalogList">
                {% for item in items %}
                <div class="item-card" data-code="{{ item.code }}" data-name="{{ item.name|lower }}">
                    <div>
                        <div class="item-name">{{ item.name }}</div>
                        <div class="item-meta">
                            {{ item.code }} • UOM: {{ item.uom }} • Available: {{ item.available }}
                        </div>
                    </div>
                    <div class="muted-small">{{ item.uom }}</div>
                    <div class="qty-box">
                        <input type="number" min="1" value="1" id="qty_{{ item.code }}">
                    </div>
                    <div>
                        <button type="button"
                                class="btn"
                                onclick="addToCart('{{ item.code }}', '{{ item.name }}', '{{ item.uom }}', {{ item.available }})">
                            Add
                        </button>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <div class="cart-card">
            <h3>Request Cart</h3>
            <table class="cart-table">
                <thead>
                    <tr>
                        <th>Item</th>
                        <th>Qty</th>
                        <th>UOM</th>
                        <th>Available</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody id="cartBody">
                    <tr id="emptyRow">
                        <td colspan="5" class="muted-small">No items in cart yet.</td>
                    </tr>
                </tbody>
            </table>

            <div class="cart-summary">
                <div><strong>Total Lines:</strong> <span id="totalLines">0</span></div>
                <div><strong>Total Quantity:</strong> <span id="totalQty">0</span></div>
            </div>

            <div class="actions-row">
                <button type="button" class="btn-light btn" onclick="clearCart()">Clear Cart</button>
                <button type="submit" class="btn">Submit Request</button>
            </div>

            <input type="hidden" name="cart_json" id="cartJson">
        </div>
    </div>
</form>

<script>
    let cart = [];

    function refreshCart() {
        const cartBody = document.getElementById('cartBody');
        const totalLines = document.getElementById('totalLines');
        const totalQty = document.getElementById('totalQty');
        const cartJson = document.getElementById('cartJson');

        cartBody.innerHTML = '';

        if (cart.length === 0) {
            cartBody.innerHTML = `
                <tr id="emptyRow">
                    <td colspan="5" class="muted-small">No items in cart yet.</td>
                </tr>
            `;
        } else {
            cart.forEach((item, index) => {
                cartBody.innerHTML += `
                    <tr>
                        <td>${item.name}</td>
                        <td>
                            <input type="number" min="1" value="${item.qty}" style="width:70px;"
                                   onchange="updateQty(${index}, this.value)">
                        </td>
                        <td>${item.uom}</td>
                        <td>${item.available}</td>
                        <td><a class="danger-link" onclick="removeItem(${index})">Remove</a></td>
                    </tr>
                `;
            });
        }

        totalLines.textContent = cart.length;
        totalQty.textContent = cart.reduce((sum, item) => sum + Number(item.qty), 0);
        cartJson.value = JSON.stringify(cart);
    }

    function addToCart(code, name, uom, available) {
        const qtyInput = document.getElementById(`qty_${code}`);
        const qty = Number(qtyInput.value);

        if (!qty || qty <= 0) {
            alert('Enter a valid quantity.');
            return;
        }

        const existing = cart.find(item => item.code === code);

        if (existing) {
            existing.qty = Number(existing.qty) + qty;
        } else {
            cart.push({
                code: code,
                name: name,
                qty: qty,
                uom: uom,
                available: available
            });
        }

        qtyInput.value = 1;
        refreshCart();
    }

    function removeItem(index) {
        cart.splice(index, 1);
        refreshCart();
    }

    function updateQty(index, value) {
        const qty = Number(value);

        if (!qty || qty <= 0) {
            cart[index].qty = 1;
        } else {
            cart[index].qty = qty;
        }

        refreshCart();
    }

    function clearCart() {
        cart = [];
        refreshCart();
    }

    document.getElementById('itemSearch').addEventListener('input', function() {
        const search = this.value.toLowerCase();
        const cards = document.querySelectorAll('.item-card');

        cards.forEach(card => {
            const code = card.dataset.code.toLowerCase();
            const name = card.dataset.name.toLowerCase();

            if (code.includes(search) || name.includes(search)) {
                card.style.display = 'grid';
            } else {
                card.style.display = 'none';
            }
        });
    });

    refreshCart();
</script>
{% endblock %}
'@
Set-Content -Path "templates\requests_app\request_cart.html" -Value $requestCartHtml -Encoding UTF8

Write-Host ""
Write-Host "Request Cart module added successfully." -ForegroundColor Green
Write-Host "Next run:" -ForegroundColor Cyan
Write-Host "python manage.py runserver"
Write-Host "Open: http://127.0.0.1:8000/requests/create/"