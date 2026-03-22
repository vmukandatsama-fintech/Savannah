$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$itemServicePath = ".\services\item_service.py"
$viewsPath = ".\requests_app\views.py"
$templatePath = ".\templates\requests_app\request_cart.html"

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$targets = @($itemServicePath, $viewsPath, $templatePath)

foreach ($path in $targets) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required file not found: $path"
    }
}

foreach ($path in $targets) {
    Copy-Item -LiteralPath $path -Destination "$path.bak_$timestamp"
}

Write-Host "Backups created for item service, views, and request cart template."
Write-Host "This script syntax is fixed."
Write-Host "Next step: apply your updated Python/HTML content into the target files."
