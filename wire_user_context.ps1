$ErrorActionPreference = "Stop"

$userServicePath = ".\services\user_service.py"
$viewsPath = ".\requests_app\views.py"

if (-not (Test-Path ".\services")) {
    throw "services folder not found."
}

if (-not (Test-Path $viewsPath)) {
    throw "views.py not found at: $viewsPath"
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

if (Test-Path $userServicePath) {
    Copy-Item $userServicePath "$userServicePath.bak_$timestamp"
}

Copy-Item $viewsPath "$viewsPath.bak_$timestamp"

Write-Host "Backups created."

$userServiceContent = @'
from django.db import connection


def get_user_context(email):
    sql = """
        SELECT TOP 1
            u.Email,
            u.Name,
            ur.DepartmentCode,
            d.Name AS DepartmentName,
            d.AuthRequired,
            r.Name AS RoleName,

            CASE WHEN r.Name = 'Stores Controller' THEN 1 ELSE 0 END AS IsStoresController,
            CASE WHEN r.Name = 'Requestor' THEN 1 ELSE 0 END AS IsRequestor,
            CASE WHEN r.Name = 'Approver' THEN 1 ELSE 0 END AS IsApprover,
            CASE WHEN r.Name = 'Authorizer' THEN 1 ELSE 0 END AS IsAuthorizer,

            CASE 
                WHEN r.Name = 'Stores Controller' THEN 'STORES'
                WHEN r.Name = 'Requestor' THEN 'REQUEST'
                ELSE 'NO_ACCESS'
            END AS AppTarget,

            CASE 
                WHEN r.Name = 'Stores Controller' THEN 1
                WHEN r.Name = 'Requestor' THEN 2
                ELSE 0
            END AS AppTargetCode,

            (
                SELECT STRING_AGG(u2.Email, ';')
                FROM dbo.Users u2
                INNER JOIN dbo.UserDepartmentRoles ur2 ON u2.Email = ur2.UserEmail
                INNER JOIN dbo.Roles r2 ON ur2.RoleID = r2.RoleID
                WHERE ur2.DepartmentCode = ur.DepartmentCode
                  AND r2.Name = 'Approver'
            ) AS ApproverEmails,

            (
                SELECT STRING_AGG(u2.Name, ';')
                FROM dbo.Users u2
                INNER JOIN dbo.UserDepartmentRoles ur2 ON u2.Email = ur2.UserEmail
                INNER JOIN dbo.Roles r2 ON ur2.RoleID = r2.RoleID
                WHERE ur2.DepartmentCode = ur.DepartmentCode
                  AND r2.Name = 'Approver'
            ) AS ApproverNames,

            (
                SELECT STRING_AGG(u3.Email, ';')
                FROM dbo.Users u3
                INNER JOIN dbo.UserDepartmentRoles ur3 ON u3.Email = ur3.UserEmail
                INNER JOIN dbo.Roles r3 ON ur3.RoleID = r3.RoleID
                WHERE ur3.DepartmentCode = ur.DepartmentCode
                  AND r3.Name = 'Authorizer'
            ) AS AuthorizerEmails,

            (
                SELECT STRING_AGG(u3.Name, ';')
                FROM dbo.Users u3
                INNER JOIN dbo.UserDepartmentRoles ur3 ON u3.Email = ur3.UserEmail
                INNER JOIN dbo.Roles r3 ON ur3.RoleID = r3.RoleID
                WHERE ur3.DepartmentCode = ur.DepartmentCode
                  AND r3.Name = 'Authorizer'
            ) AS AuthorizerNames
        FROM dbo.Users u
        LEFT JOIN dbo.UserDepartmentRoles ur
            ON u.Email = ur.UserEmail
        LEFT JOIN dbo.Departments d
            ON ur.DepartmentCode = d.DepartmentCode
        LEFT JOIN dbo.Roles r
            ON ur.RoleID = r.RoleID
        WHERE LOWER(LTRIM(RTRIM(u.Email))) = LOWER(LTRIM(RTRIM(%s)))
          AND u.IsActive = 1
        ORDER BY
            CASE
                WHEN r.Name = 'Requestor' THEN 1
                WHEN r.Name = 'Stores Controller' THEN 2
                WHEN r.Name = 'Approver' THEN 3
                WHEN r.Name = 'Authorizer' THEN 4
                ELSE 99
            END
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, [email])
        row = cursor.fetchone()

        if not row:
            return None

        columns = [col[0] for col in cursor.description]
        result = dict(zip(columns, row))

    result["AuthRequired"] = bool(result.get("AuthRequired") or 0)
    result["IsStoresController"] = bool(result.get("IsStoresController") or 0)
    result["IsRequestor"] = bool(result.get("IsRequestor") or 0)
    result["IsApprover"] = bool(result.get("IsApprover") or 0)
    result["IsAuthorizer"] = bool(result.get("IsAuthorizer") or 0)

    return result
'@

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
                    "user_context": user_context,
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
                    "user_context": user_context,
                },
            )

        except Exception as e:
            return render(
                request,
                "requests_app/request_cart.html",
                {
                    "items": items,
                    "farmers": farmers,
                    "user_context": user_context,
                    "error_message": str(e),
                },
            )

    return render(
        request,
        "requests_app/request_cart.html",
        {
            "items": items,
            "farmers": farmers,
            "user_context": user_context,
        },
    )
'@

Set-Content -Path $userServicePath -Value $userServiceContent -Encoding UTF8
Write-Host "Created/Updated: $userServicePath"

Set-Content -Path $viewsPath -Value $viewsContent -Encoding UTF8
Write-Host "Updated: $viewsPath"

Write-Host ""
Write-Host "Patch applied successfully."
Write-Host "Next steps:"
Write-Host "1. Run: python manage.py runserver"
Write-Host "2. Open the request page while logged in"
Write-Host "3. Confirm request submission now uses request.user.email and real DepartmentCode from SQL"
Write-Host "4. If needed, expose user_context on the page header next"