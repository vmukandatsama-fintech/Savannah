$ErrorActionPreference = "Stop"

$templatePath = ".\templates\requests_app\request_cart.html"

if (-not (Test-Path $templatePath)) {
    throw "Template not found at: $templatePath"
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item $templatePath "$templatePath.bak_$timestamp"

Write-Host "Backup created: $templatePath.bak_$timestamp"

$templateContent = Get-Content $templatePath -Raw

$contextBlock = @'
{% if user_context %}
<div style="background:#f8f9fa;border:1px solid #dcdfe3;border-radius:8px;padding:14px 16px;margin-bottom:18px;">
    <div style="font-size:16px;font-weight:600;margin-bottom:10px;">Current User Context</div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px 18px;font-size:14px;">
        <div><strong>Name:</strong> {{ user_context.Name }}</div>
        <div><strong>Email:</strong> {{ user_context.Email }}</div>
        <div><strong>Department:</strong> {{ user_context.DepartmentName }} ({{ user_context.DepartmentCode }})</div>
        <div><strong>Role:</strong> {{ user_context.RoleName }}</div>
        <div><strong>App Target:</strong> {{ user_context.AppTarget }}</div>
        <div><strong>Auth Required:</strong> {% if user_context.AuthRequired %}Yes{% else %}No{% endif %}</div>
    </div>
</div>
{% endif %}
'@

if ($templateContent.Contains("Current User Context")) {
    Write-Host "User context block already exists. No changes made."
    exit 0
}

if ($templateContent -match '(?s)(<h1[^>]*>.*?</h1>)') {
    $updatedContent = [regex]::Replace(
        $templateContent,
        '(?s)(<h1[^>]*>.*?</h1>)',
        "`$1`r`n$contextBlock",
        1
    )
}
elseif ($templateContent -match '(<main[^>]*>)') {
    $updatedContent = [regex]::Replace(
        $templateContent,
        '(<main[^>]*>)',
        "`$1`r`n$contextBlock",
        1
    )
}
elseif ($templateContent -match '({% block content %})') {
    $updatedContent = [regex]::Replace(
        $templateContent,
        '({% block content %})',
        "`$1`r`n$contextBlock",
        1
    )
}
else {
    $updatedContent = $contextBlock + "`r`n" + $templateContent
}

Set-Content -Path $templatePath -Value $updatedContent -Encoding UTF8

Write-Host "Updated: $templatePath"
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Refresh the request page"
Write-Host "2. Confirm the Current User Context box appears"
Write-Host "3. Check Name, Email, Department, Role, App Target, and Auth Required"