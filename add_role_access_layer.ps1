$ErrorActionPreference = "Stop"

function Backup-File {
    param(
        [string]$Path
    )

    if (Test-Path $Path) {
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        Copy-Item $Path "$Path.bak_$timestamp"
        Write-Host "Backup created: $Path.bak_$timestamp"
    }
}

function Ensure-Directory {
    param(
        [string]$Path
    )

    if (!(Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
        Write-Host "Created directory: $Path"
    }
}

Write-Host "=== Savannah Stores: Adding role-based access layer ==="

# ------------------------------------------------------------
# 1. Ensure core folder exists
# ------------------------------------------------------------
Ensure-Directory ".\core"

# ------------------------------------------------------------
# 2. Create core/role_config.py
# ------------------------------------------------------------
$roleConfigPath = ".\core\role_config.py"
Backup-File $roleConfigPath

@'
ROLE_FEATURES = {
    "Requestor": {
        "dashboard": True,
        "create_request": True,
        "my_requests": True,
        "approvals": False,
        "collections": False,
        "reports": False,
        "admin": False,
    },
    "Approver": {
        "dashboard": True,
        "create_request": True,
        "my_requests": True,
        "approvals": True,
        "collections": False,
        "reports": False,
        "admin": False,
    },
    "Authorizer": {
        "dashboard": True,
        "create_request": True,
        "my_requests": True,
        "approvals": True,
        "collections": False,
        "reports": False,
        "admin": False,
    },
    "Stores Controller": {
        "dashboard": True,
        "create_request": False,
        "my_requests": False,
        "approvals": False,
        "collections": True,
        "reports": True,
        "admin": False,
    },
}


def get_role_features(role_name: str | None) -> dict:
    if not role_name:
        return {}

    return ROLE_FEATURES.get(role_name, {})
'@ | Set-Content -Path $roleConfigPath -Encoding UTF8

Write-Host "Created/Updated: $roleConfigPath"

# ------------------------------------------------------------
# 3. Create core/context_processors.py
# ------------------------------------------------------------
$contextProcessorPath = ".\core\context_processors.py"
Backup-File $contextProcessorPath

@'
from core.role_config import get_role_features


def user_context(request):
    role_name = request.session.get("role_name")
    features = get_role_features(role_name)

    return {
        "session_user_email": request.session.get("user_email"),
        "session_user_name": request.session.get("user_name"),
        "session_role_name": role_name,
        "session_department_code": request.session.get("department_code"),
        "session_department_name": request.session.get("department_name"),
        "session_features": features,
    }
'@ | Set-Content -Path $contextProcessorPath -Encoding UTF8

Write-Host "Created/Updated: $contextProcessorPath"

# ------------------------------------------------------------
# 4. Update core/decorators.py
# ------------------------------------------------------------
$decoratorsPath = ".\core\decorators.py"
Backup-File $decoratorsPath

@'
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from core.role_config import get_role_features


def sql_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get("user_email"):
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def feature_required(feature_name: str):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.session.get("user_email"):
                return redirect("login")

            role_name = request.session.get("role_name")
            features = get_role_features(role_name)

            if not features.get(feature_name, False):
                messages.error(request, "You do not have access to that page.")
                return redirect("dashboard")

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
'@ | Set-Content -Path $decoratorsPath -Encoding UTF8

Write-Host "Created/Updated: $decoratorsPath"

# ------------------------------------------------------------
# 5. Create helper instruction file for manual updates
# ------------------------------------------------------------
$instructionPath = ".\ROLE_ACCESS_NEXT_STEPS.txt"

@'
SAVANNAH STORES - ROLE ACCESS NEXT STEPS

1) Add the context processor to settings.py

Find:
TEMPLATES = [
    {
        ...
        "OPTIONS": {
            "context_processors": [
                ...
            ],
        },
    },
]

Add:
"core.context_processors.user_context",

Example:
"OPTIONS": {
    "context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "core.context_processors.user_context",
    ],
},

------------------------------------------------------------

2) Update your base.html sidebar to use session_features

Use this block:

<ul class="nav flex-column">

    {% if session_features.dashboard %}
    <li class="nav-item">
        <a class="nav-link" href="{% url 'dashboard' %}">Dashboard</a>
    </li>
    {% endif %}

    {% if session_features.create_request %}
    <li class="nav-item">
        <a class="nav-link" href="{% url 'create_request' %}">Create Request</a>
    </li>
    {% endif %}

    {% if session_features.my_requests %}
    <li class="nav-item">
        <a class="nav-link" href="{% url 'my_requests' %}">My Requests</a>
    </li>
    {% endif %}

    {% if session_features.approvals %}
    <li class="nav-item">
        <a class="nav-link" href="{% url 'approval_inbox' %}">Approvals</a>
    </li>
    {% endif %}

    {% if session_features.collections %}
    <li class="nav-item">
        <a class="nav-link" href="{% url 'collection_inbox' %}">Pending Collections</a>
    </li>
    {% endif %}

    {% if session_features.reports %}
    <li class="nav-item">
        <a class="nav-link" href="#">Reports</a>
    </li>
    {% endif %}

</ul>

------------------------------------------------------------

3) Update the user context section in base.html

Example:

<div class="small text-muted">
    <div>{{ session_user_name }}</div>
    <div>{{ session_role_name }}</div>
    <div>{{ session_department_name }}</div>
</div>

------------------------------------------------------------

4) Protect views using feature_required

Examples:

from core.decorators import sql_login_required, feature_required

@sql_login_required
@feature_required("dashboard")
def dashboard_view(request):
    ...

@sql_login_required
@feature_required("create_request")
def create_request_view(request):
    ...

@sql_login_required
@feature_required("my_requests")
def my_requests_view(request):
    ...

@sql_login_required
@feature_required("approvals")
def approval_inbox_view(request):
    ...

@sql_login_required
@feature_required("collections")
def collection_inbox_view(request):
    ...

------------------------------------------------------------

5) Recommended role behavior

Requestor:
- Dashboard
- Create Request
- My Requests

Approver:
- Dashboard
- Create Request
- My Requests
- Approvals

Authorizer:
- Dashboard
- Create Request
- My Requests
- Approvals

Stores Controller:
- Dashboard
- Pending Collections
- Reports

------------------------------------------------------------

6) After finishing, run:

python manage.py check
python manage.py runserver
'@ | Set-Content -Path $instructionPath -Encoding UTF8

Write-Host "Created: $instructionPath"

Write-Host ""
Write-Host "=== Done ==="
Write-Host "Files created/updated:"
Write-Host " - core/role_config.py"
Write-Host " - core/context_processors.py"
Write-Host " - core/decorators.py"
Write-Host " - ROLE_ACCESS_NEXT_STEPS.txt"
Write-Host ""
Write-Host "Next:"
Write-Host " 1. Update settings.py with core.context_processors.user_context"
Write-Host " 2. Update base.html sidebar and user context block"
Write-Host " 3. Apply @feature_required(...) on protected views"