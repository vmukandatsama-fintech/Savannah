$ErrorActionPreference = "Stop"

$settingsPath = ".\config\settings.py"
$contextProcessorPath = ".\core\context_processors.py"

if (-not (Test-Path $settingsPath)) {
    throw "settings.py not found at: $settingsPath"
}

if (-not (Test-Path $contextProcessorPath)) {
    throw "context_processors.py not found at: $contextProcessorPath"
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

Copy-Item $settingsPath "$settingsPath.bak_$timestamp"
Copy-Item $contextProcessorPath "$contextProcessorPath.bak_$timestamp"

Write-Host "Backups created."

# Fix core/context_processors.py
$contextProcessorContent = @'
from services.user_service import get_user_context


def global_user_context(request):
    user = getattr(request, "user", None)

    if not user or not user.is_authenticated:
        return {}

    user_email = (getattr(user, "email", "") or "").strip()

    if not user_email:
        user_email = (getattr(user, "username", "") or "").strip()

    if not user_email:
        return {}

    try:
        user_context = get_user_context(user_email)
        return {"user_context": user_context} if user_context else {}
    except Exception:
        return {}
'@

Set-Content -Path $contextProcessorPath -Value $contextProcessorContent -Encoding UTF8
Write-Host "Updated: $contextProcessorPath"

# Fix settings.py
$settingsContent = Get-Content $settingsPath -Raw

if ($settingsContent -notmatch "core\.context_processors\.global_user_context") {
    $settingsContent = $settingsContent -replace (
        '"django\.contrib\.messages\.context_processors\.messages",',
        '"django.contrib.messages.context_processors.messages",' + "`r`n" + '                "core.context_processors.global_user_context",'
    )

    Set-Content -Path $settingsPath -Value $settingsContent -Encoding UTF8
    Write-Host "Updated: $settingsPath"
}
else {
    Write-Host "Context processor already registered in settings.py"
}

Write-Host ""
Write-Host "Done."
Write-Host "Now restart Django:"
Write-Host "python manage.py runserver"