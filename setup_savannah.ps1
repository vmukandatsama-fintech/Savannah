$ErrorActionPreference = "Stop"

Write-Host "Starting Savannah setup..." -ForegroundColor Cyan

# Ensure we are in the script folder
Set-Location $PSScriptRoot

# 1. Create virtual environment if missing
if (!(Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    py -m venv .venv
}

# 2. Activate venv
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\.venv\Scripts\Activate.ps1"

# 3. Upgrade pip and install packages
Write-Host "Installing packages..." -ForegroundColor Yellow
python -m pip install --upgrade pip
pip install Django mssql-django pyodbc

# 4. Create Django project if missing
if (!(Test-Path "manage.py")) {
    Write-Host "Creating Django project..." -ForegroundColor Yellow
    django-admin startproject config .
}

# 5. Create apps if missing
$apps = @("core", "accounts", "dashboard", "requests_app", "stock")

foreach ($app in $apps) {
    if (!(Test-Path $app)) {
        Write-Host "Creating app: $app" -ForegroundColor Yellow
        python manage.py startapp $app
    }
}

# 6. Create folders
$folders = @(
    "templates",
    "templates\registration",
    "templates\dashboard",
    "templates\partials",
    "static",
    "static\css",
    "static\js",
    "static\images"
)

foreach ($folder in $folders) {
    if (!(Test-Path $folder)) {
        New-Item -ItemType Directory -Path $folder | Out-Null
    }
}

# 7. Write config/settings.py
$settingsContent = @'
"""
Django settings for config project.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "dev-secret-key"
DEBUG = True
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "core",
    "accounts",
    "dashboard",
    "requests_app",
    "stock",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Harare"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/login/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
'@
Set-Content -Path "config\settings.py" -Value $settingsContent -Encoding UTF8

# 8. Write dashboard/views.py
$dashboardViews = @'
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def dashboard_home(request):
    return render(request, "dashboard/home.html")
'@
Set-Content -Path "dashboard\views.py" -Value $dashboardViews -Encoding UTF8

# 9. Write dashboard/urls.py
$dashboardUrls = @'
from django.urls import path
from .views import dashboard_home

urlpatterns = [
    path("", dashboard_home, name="dashboard_home"),
]
'@
Set-Content -Path "dashboard\urls.py" -Value $dashboardUrls -Encoding UTF8

# 10. Write accounts/urls.py
$accountsUrls = @'
from django.contrib.auth import views as auth_views
from django.urls import path

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
'@
Set-Content -Path "accounts\urls.py" -Value $accountsUrls -Encoding UTF8

# 11. Write config/urls.py
$configUrls = @'
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("dashboard/", include("dashboard.urls")),
]
'@
Set-Content -Path "config\urls.py" -Value $configUrls -Encoding UTF8

# 12. Write templates/base.html
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
                <a href="#">Requests</a>
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

# 13. Write templates/registration/login.html
$loginHtml = @'
{% extends "base.html" %}

{% block auth_content %}
<div class="login-wrap">
    <div class="login-card">
        <h2>Sign In</h2>
        <p class="muted">Savannah Stores</p>

        <form method="post">
            {% csrf_token %}
            {{ form.non_field_errors }}

            <label for="id_username">Username</label>
            {{ form.username }}

            <label for="id_password">Password</label>
            {{ form.password }}

            <button type="submit">Login</button>
        </form>
    </div>
</div>
{% endblock %}
'@
Set-Content -Path "templates\registration\login.html" -Value $loginHtml -Encoding UTF8

# 14. Write templates/dashboard/home.html
$homeHtml = @'
{% extends "base.html" %}

{% block content %}
<h1>Dashboard</h1>
<p class="muted">Welcome to Savannah Stores.</p>

<div class="stats">
    <div class="stat-box">
        <div class="muted">Open Requests</div>
        <h2>0</h2>
    </div>
    <div class="stat-box">
        <div class="muted">Pending Approvals</div>
        <h2>0</h2>
    </div>
    <div class="stat-box">
        <div class="muted">Pending Collections</div>
        <h2>0</h2>
    </div>
    <div class="stat-box">
        <div class="muted">Low Stock Items</div>
        <h2>0</h2>
    </div>
</div>

<div class="card" style="margin-top:20px;">
    <h3>Next Build Target</h3>
    <p>Request cart page.</p>
</div>
{% endblock %}
'@
Set-Content -Path "templates\dashboard\home.html" -Value $homeHtml -Encoding UTF8

# 15. Run migrations
Write-Host "Running migrations..." -ForegroundColor Yellow
python manage.py migrate

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Next commands:" -ForegroundColor Cyan
Write-Host "1. python manage.py createsuperuser"
Write-Host "2. python manage.py runserver"