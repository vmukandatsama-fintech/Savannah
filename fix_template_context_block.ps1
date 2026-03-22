$ErrorActionPreference = "Stop"

$templatePath = ".\templates\requests_app\request_cart.html"

if (-not (Test-Path $templatePath)) {
    throw "Template not found."
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item $templatePath "$templatePath.bak_$timestamp"

Write-Host "Backup created."

$content = Get-Content $templatePath -Raw

# Remove ANY broken user_context blocks
$content = [regex]::Replace(
    $content,
    '(?s)\{% if user_context %\}.*?\{% endif %\}',
    ''
)

# Clean double blank lines
$content = [regex]::Replace($content, "(\r?\n){3,}", "`r`n`r`n")

# Correct block to insert
$block = @'

{% if user_context %}
<div style="position:fixed;right:18px;bottom:18px;width:320px;background:#fff;border:1px solid #ddd;border-radius:10px;box-shadow:0 8px 25px rgba(0,0,0,0.15);padding:12px;font-size:13px;z-index:999;">
    <div style="font-weight:600;margin-bottom:8px;">User Context</div>
    <div><b>Name:</b> {{ user_context.Name }}</div>
    <div><b>Email:</b> {{ user_context.Email }}</div>
    <div><b>Dept:</b> {{ user_context.DepartmentName }}</div>
    <div><b>Role:</b> {{ user_context.RoleName }}</div>
</div>
{% endif %}

'@

# Insert INSIDE block content (safe)
$content = $content -replace '({% block content %})', "`$1`r`n$block"

Set-Content $templatePath $content -Encoding UTF8

Write-Host "Template fixed successfully."
Write-Host "Refresh your browser."