$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Connecting Savannah to SQL Server..." -ForegroundColor Cyan

# =========================
# EDIT THESE VALUES FIRST
# =========================
$SqlHost = "POWERAPPSSVR"
$SqlPort = "1433"
$SqlDatabase = "SavannahStores_DEV"
$SqlUser = "sa"
$SqlPassword = "Pr3m1um@"
$OdbcDriver = "ODBC Driver 18 for SQL Server"
# Set to $true only if you need to bypass certificate validation in dev
$TrustServerCertificate = $true

# 1. Verify packages
Write-Host "Installing/confirming packages..." -ForegroundColor Yellow
python -m pip install --upgrade pip
pip install mssql-django pyodbc

# 2. Rewrite config/settings.py to SQL Server
$settingsContent = @"
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
        "ENGINE": "mssql",
        "NAME": "$SqlDatabase",
        "USER": "$SqlUser",
        "PASSWORD": "$SqlPassword",
        "HOST": "$SqlHost",
        "PORT": "$SqlPort",
        "OPTIONS": {
            "driver": "$OdbcDriver",
            "trust_server_certificate": $($TrustServerCertificate.ToString().ToLower())
        },
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
"@
Set-Content -Path "config\settings.py" -Value $settingsContent -Encoding UTF8

# 3. Add a simple SQL connection test view in core/views.py
$coreViews = @'
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import HttpResponse


@login_required
def sql_test(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT DB_NAME() AS db_name, @@SERVERNAME AS server_name")
        row = cursor.fetchone()

    return HttpResponse(
        f"Connected successfully. Database: {row[0]} | Server: {row[1]}"
    )
'@
Set-Content -Path "core\views.py" -Value $coreViews -Encoding UTF8

# 4. Add core/urls.py
$coreUrls = @'
from django.urls import path
from .views import sql_test

urlpatterns = [
    path("sql-test/", sql_test, name="sql_test"),
]
'@
Set-Content -Path "core\urls.py" -Value $coreUrls -Encoding UTF8

# 5. Rewrite config/urls.py to include core
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
    path("", include("core.urls")),
]
'@
Set-Content -Path "config\urls.py" -Value $configUrls -Encoding UTF8

Write-Host ""
Write-Host "SQL Server settings written." -ForegroundColor Green
Write-Host "Next commands:" -ForegroundColor Cyan
Write-Host "1. python manage.py check"
Write-Host "2. python manage.py runserver"
Write-Host "3. Open http://127.0.0.1:8000/sql-test/ after login"