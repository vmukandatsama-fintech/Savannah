$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Rewriting Savannah request catalog to use Inventory table..." -ForegroundColor Cyan

if (!(Test-Path "services")) {
    New-Item -ItemType Directory -Path "services" | Out-Null
}

if (!(Test-Path "templates\requests_app")) {
    New-Item -ItemType Directory -Path "templates\requests_app" | Out-Null
}

# services/item_service.py
$itemService = @'
from django.db import connection


def get_active_inventory_items():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                ItemCode,
                Name,
                UOMCode,
                CurrentStock
            FROM Inventory
            WHERE IsActive = 1
            ORDER BY Name
        """)
        rows = cursor.fetchall()

    return [
        {
            "code": row[0],
            "name": row[1],
            "uom": row[2],
            "available": float(row[3] or 0),
        }
        for row in rows
    ]
'@
Set-Content -Path "services\item_service.py" -Value $itemService -Encoding UTF8

# services/farmer_service.py
$farmerService = @'
from django.db import connection


def get_active_farmers():
    table_name = "Farmers"

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """, [table_name])
        columns = [row[0] for row in cursor.fetchall()]

    if not columns:
        raise Exception(f"Table '{table_name}' was not found or has no columns.")

    grower_number_candidates = [
        "GrowerNumber", "FarmerNumber", "GrowerNo", "FarmerNo", "Code", "Grower_Code"
    ]
    grower_name_candidates = [
        "GrowerName", "FarmerName", "Name", "Grower", "Farmer", "DisplayName"
    ]
    active_candidates = [
        "IsActive", "Active", "Is_Active", "RecordActive"
    ]

    grower_number_col = next((c for c in grower_number_candidates if c in columns), None)
    grower_name_col = next((c for c in grower_name_candidates if c in columns), None)
    active_col = next((c for c in active_candidates if c in columns), None)

    if not grower_number_col:
        raise Exception(
            "Could not find farmer number column in Farmers table. "
            f"Available columns: {', '.join(columns)}"
        )

    if not grower_name_col:
        raise Exception(
            "Could not find farmer name column in Farmers table. "
            f"Available columns: {', '.join(columns)}"
        )

    sql = f"SELECT {grower_number_col}, {grower_name_col} FROM {table_name}"

    if active_col:
        sql += f" WHERE {active_col} = 1"

    sql += f" ORDER BY {grower_name_col}"

    with connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()

    return [
        {
            "grower_number": row[0],
            "grower_name": row[1],
        }
        for row in rows
    ]
'@
Set-Content -Path "services\farmer_service.py" -Value $farmerService -Encoding UTF8

# requests_app/views.py
$requestsViews = @'
import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from services.request_service import create_request_from_cart
from services.farmer_service import get_active_farmers
from services.item_service import get_active_inventory_items


@login_required
def request_cart(request):
    items = get_active_inventory_items()
    farmers = get_active_farmers()

    if request.method == "POST":
        cart_json = request.POST.get("cart_json", "[]")

        try:
            cart = json.loads(cart_json)
        except json.JSONDecodeError:
            cart = []

        if not cart:
            return render(request, "requests_app/request_cart.html", {
                "items": items,
                "farmers": farmers,
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
                "items": items,
                "farmers": farmers,
                "error_message": str(e),
            })

    return render(request, "requests_app/request_cart.html", {
        "items": items,
        "farmers": farmers,
    })
'@
Set-Content -Path "requests_app\views.py" -Value $requestsViews -Encoding UTF8

# templates/requests_app/request_cart.html
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

    .error-box {
        background: #fee2e2;
        color: #991b1b;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 16px;
    }

    .warning-badge {
        display: inline-block;
        background: #fef3c7;
        color: #92400e;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 12px;
        margin-left: 8px;
    }
</style>

<div class="page-header">
    <h1>Create Request</h1>
    <p class="muted">Build a request like a shopping cart.</p>
</div>

{% if error_message %}
<div class="error-box">
    {{ error_message }}
</div>
{% endif %}

<form method="post" id="requestForm">
    {% csrf_token %}

    <div class="request-header-card">
        <h3>Request Header</h3>
        <div class="request-grid">
            <div class="field">
                <label>Farmer</label>
                <select name="farmer" required>
                    <option value="">Select farmer</option>
                    {% for farmer in farmers %}
                        <option value="{{ farmer.grower_number }}">
                            {{ farmer.grower_name }} ({{ farmer.grower_number }})
                        </option>
                    {% endfor %}
                </select>
            </div>

            <div class="field">
                <label>Required Date</label>
                <input type="date" name="required_date" required>
            </div>

            <div class="field">
                <label>Collector Name</label>
                <input type="text" name="collector_name" required>
            </div>

            <div class="field">
                <label>Collector National ID</label>
                <input type="text" name="collector_national_id" required>
            </div>

            <div class="field">
                <label>Truck Registration</label>
                <input type="text" name="truck_registration" required>
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
                        <div class="item-name">
                            {{ item.name }}
                            {% if item.available <= 0 %}
                                <span class="warning-badge">Out of stock</span>
                            {% endif %}
                        </div>
                        <div class="item-meta">
                            {{ item.code }} • UOM: {{ item.uom }} • Available: {{ item.available }}
                        </div>
                    </div>
                    <div class="muted-small">{{ item.uom }}</div>
                    <div class="qty-box">
                        <input type="number" min="1" value="1" id="qty_{{ item.code }}">
                    </div>
                    <div>
                        <button
                            type="button"
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
Write-Host "Inventory-backed request cart written successfully." -ForegroundColor Green
Write-Host "Next:" -ForegroundColor Cyan
Write-Host "1. python manage.py runserver"
Write-Host "2. Open http://127.0.0.1:8000/requests/create/"
Write-Host "3. Test with ITM002 or ITM007 using a low quantity"