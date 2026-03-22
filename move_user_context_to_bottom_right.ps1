$ErrorActionPreference = "Stop"

$templatePath = ".\templates\requests_app\request_cart.html"

if (-not (Test-Path $templatePath)) {
    throw "Template not found at: $templatePath"
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item $templatePath "$templatePath.bak_$timestamp"

Write-Host "Backup created: $templatePath.bak_$timestamp"

$templateContent = Get-Content $templatePath -Raw

$newBlock = @'
{% if user_context %}
<div style="position:fixed;right:18px;bottom:18px;width:340px;max-width:calc(100vw - 36px);background:#ffffff;border:1px solid #d7dce2;border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,0.12);z-index:999;padding:0;overflow:hidden;">
    <div style="background:#f6f8fa;padding:12px 14px;border-bottom:1px solid #e5e7eb;font-size:15px;font-weight:600;">
        Current User Context
    </div>
    <div style="padding:12px 14px;font-size:13px;line-height:1.5;">
        <div style="margin-bottom:6px;"><strong>Name:</strong> {{ user_context.Name }}</div>
        <div style="margin-bottom:6px;word-break:break-word;"><strong>Email:</strong> {{ user_context.Email }}</div>
        <div style="margin-bottom:6px;"><strong>Department:</strong> {{ user_context.DepartmentName }} ({{ user_context.DepartmentCode }})</div>
        <div style="margin-bottom:6px;"><strong>Role:</strong> {{ user_context.RoleName }}</div>
        <div style="margin-bottom:6px;"><strong>App Target:</strong> {{ user_context.AppTarget }}</div>
        <div><strong>Auth Required:</strong> {% if user_context.AuthRequired %}Yes{% else %}No{% endif %}</div>
    </div>
</div>
{% endif %}
'@

$pattern = '(?s)\{% if user_context %\}.*?Current User Context.*?\{% endif %\}'

if ($templateContent -notmatch 'Current User Context') {
    throw "Could not find the existing Current User Context block to replace."
}

$updatedContent = [regex]::Replace(
    $templateContent,
    $pattern,
    [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $newBlock },
    1
)

Set-Content -Path $templatePath -Value $updatedContent -Encoding UTF8

Write-Host "Updated: $templatePath"
Write-Host "Refresh the request page to see the drawer at the bottom-right."