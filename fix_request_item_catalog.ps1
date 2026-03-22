$ErrorActionPreference = "Stop"

$itemServicePath = ".\services\item_service.py"
$viewsPath = ".\requests_app\views.py"

if (-not (Test-Path ".\services")) {
    throw "services folder not found."
}

if (-not (Test-Path $viewsPath)) {
    throw "views.py not found at: $viewsPath"
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

if (Test-Path $itemServicePath) {
    Copy-Item $itemServicePath "$itemServicePath.bak_$timestamp"
}

Copy-Item $viewsPath "$viewsPath.bak_$timestamp"

Write-Host "Backups created."

$itemServiceContent = @'
from django.db import connection


def get_requestable_items():
    sql = """
        SELECT
            i.ItemCode,
            i.Name,
            i.UOMCode,
            CAST(ISNULL(b.AvailableStock, 0) AS DECIMAL(18,2)) AS AvailableStock
        FROM dbo.Inventory i
        LEFT JOIN dbo.vw_StockBalance b
            ON i.ItemCode = b.ItemCode
        WHERE i.IsActive = 1
        ORDER BY i.Name;
    """

    with connection.cursor() as cursor:
        cursor.execute(sql)
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

$viewsContent = @'
import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from services.farmer_service import get_active_farmers
from services.item_service import get_requestable_items
from services.request_service import create_request_from_cart


@login_required
def request_cart(request):
    items = get_requestable_items()
    farmers = get_active_farmers()

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
            "department_code": "DEP-005",
            "justification": request.POST.get("justification", ""),
        }

        try:
            request_number = create_request_from_cart(
                user_email="vmukandatsama@premiumzimbabwe.com",
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
'@

Set-Content -Path $itemServicePath -Value $itemServiceContent -Encoding UTF8
Write-Host "Created/Updated: $itemServicePath"

Set-Content -Path $viewsPath -Value $viewsContent -Encoding UTF8
Write-Host "Updated: $viewsPath"

Write-Host ""
Write-Host "Patch applied successfully."
Write-Host "Next steps:"
Write-Host "1. Run: python manage.py runserver"
Write-Host "2. Open the request page"
Write-Host "3. Confirm items now come from SQL Inventory/vw_StockBalance"
Write-Host "4. Test ITM002 again and verify the displayed name matches SQL"