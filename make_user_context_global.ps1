$ErrorActionPreference = "Stop"

$contextProcessorPath = ".\core\context_processors.py"
$settingsPath = ".\config\settings.py"
$viewsPath = ".\requests_app\views.py"

if (-not (Test-Path ".\core")) {
    throw "core folder not found."
}

if (-not (Test-Path $settingsPath)) {
    throw "settings.py not found at: $settingsPath"
}

if (-not (Test-Path $viewsPath)) {
    throw "views.py not found at: $viewsPath"
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

if (Test-Path $contextProcessorPath) {
    Copy-Item $contextProcessorPath "$contextProcessorPath.bak_$timestamp"
}

Copy-Item $settingsPath "$settingsPath.bak_$timestamp"
Copy-Item $viewsPath "$viewsPath.bak_$timestamp"

Write-Host "Backups created."

$contextProcessorContent = @'
from services.user_service import get_user_context


def global_user_context(request):
    if not getattr(request, "user", None):
        return {}

    if not request.user.is_authenticated:
        return {}

    user_email = (getattr(request.user, "email", "") or "").strip()
    if not user_email:
        return {}

    try:
        user_context = get_user_context(user_email)
        return {"user_context": user_context} if user_context else {}
    except Exception:
        return {}
'@

Set-Content -Path $contextProcessorPath -Value $contextProcessorContent -Encoding UTF8
Write-Host "Created/Updated: $contextProcessorPath"

$settingsContent = Get-Content $settingsPath -Raw

if ($settingsContent -notmatch "core\.context_processors\.global_user_context") {
    $settingsContent = $settingsContent -replace (
        "'django\.contrib\.messages\.context_processors\.messages',",
        "'django.contrib.messages.context_processors.messages',`r`n                'core.context_processors.global_user_context',"
    )

    Set-Content -Path $settingsPath -Value $settingsContent -Encoding UTF8
    Write-Host "Updated settings.py with global_user_context"
}
else {
    Write-Host "settings.py already contains global_user_context"
}

$viewsContent = @'
import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from services.farmer_service import get_active_farmers
from services.item_service import get_requestable_items
from services.request_service import create_request_from_cart
from services.user_service import get_user_context


@login_required
def request_cart(request):
    items = get_requestable_items()
    farmers = get_active_farmers()

    user_email = (request.user.email or "").strip()
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
'@

Set-Content -Path $viewsPath -Value $viewsContent -Encoding UTF8
Write-Host "Updated: $viewsPath"

Write-Host ""
Write-Host "Patch applied successfully."
Write-Host "Next:"
Write-Host "1. Run: python manage.py runserver"
Write-Host "2. Refresh the request page"
Write-Host "3. Confirm user context still appears in base.html sidebar"
Write-Host "4. Confirm other pages can now also use {{ user_context }}"