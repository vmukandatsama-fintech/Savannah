$ErrorActionPreference = "Stop"

$basePath = ".\templates\base.html"
$requestCartPath = ".\templates\requests_app\request_cart.html"

if (-not (Test-Path $basePath)) {
    throw "base.html not found at: $basePath"
}

if (-not (Test-Path $requestCartPath)) {
    throw "request_cart.html not found at: $requestCartPath"
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

Copy-Item $basePath "$basePath.bak_$timestamp"
Copy-Item $requestCartPath "$requestCartPath.bak_$timestamp"

Write-Host "Backups created."

$baseContent = Get-Content $basePath -Raw
$requestCartContent = Get-Content $requestCartPath -Raw

# 1. Remove any floating user context block from request_cart.html
$requestCartContent = [regex]::Replace(
    $requestCartContent,
    '(?s)\{% if user_context %\}\s*<div style="position:fixed;.*?\{% endif %\}\s*',
    ''
)

Set-Content -Path $requestCartPath -Value $requestCartContent -Encoding UTF8
Write-Host "Removed floating user context block from request_cart.html"

# 2. Ensure base.html has a style block we can patch
if ($baseContent -notmatch '(?s)<style.*?</style>') {
    $baseContent = $baseContent -replace '(<head[^>]*>)', "`$1`r`n<style>`r`n</style>"
}

# 3. Add sticky header and sidebar layout CSS
$cssToAdd = @'

/* Savannah layout fixes */
.sidebar {
    display: flex;
    flex-direction: column;
    height: 100vh;
}

header,
.topbar,
.navbar,
.app-header {
    position: sticky;
    top: 0;
    z-index: 1000;
}

/* Fallback if the header wrapper uses a different class */
body > header {
    position: sticky;
    top: 0;
    z-index: 1000;
}

.sidebar-user-context {
    margin-top: auto;
    padding: 14px;
    border-top: 1px solid rgba(255,255,255,0.1);
    font-size: 13px;
    color: #e5e7eb;
}

.sidebar-user-context-title {
    font-weight: 600;
    margin-bottom: 6px;
}

.sidebar-user-context-email {
    opacity: 0.7;
    font-size: 12px;
    margin-bottom: 8px;
    word-break: break-word;
}

.sidebar-user-context-meta {
    font-size: 12px;
    opacity: 0.85;
}
'@

$baseContent = [regex]::Replace(
    $baseContent,
    '(?s)(<style.*?>)(.*?)(</style>)',
    [System.Text.RegularExpressions.MatchEvaluator]{
        param($m)

        $existingCss = $m.Groups[2].Value
        if ($existingCss -match 'Savannah layout fixes') {
            return $m.Value
        }

        return $m.Groups[1].Value + $existingCss + "`r`n" + $cssToAdd + "`r`n" + $m.Groups[3].Value
    },
    1
)

# 4. Insert user context block inside sidebar
$userContextBlock = @'

{% if user_context %}
<div class="sidebar-user-context">
    <div class="sidebar-user-context-title">User Context</div>
    <div><strong>Name:</strong> {{ user_context.Name }}</div>
    <div class="sidebar-user-context-email">{{ user_context.Email }}</div>
    <div class="sidebar-user-context-meta">
        <div><strong>Dept:</strong> {{ user_context.DepartmentName }}</div>
        <div><strong>Role:</strong> {{ user_context.RoleName }}</div>
    </div>
</div>
{% endif %}
'@

if ($baseContent -notmatch 'sidebar-user-context') {
    if ($baseContent -match '(?s)(<div[^>]*class="[^"]*sidebar[^"]*"[^>]*>)') {
        $baseContent = [regex]::Replace(
            $baseContent,
            '(?s)(<div[^>]*class="[^"]*sidebar[^"]*"[^>]*>)(.*?)(</div>)',
            [System.Text.RegularExpressions.MatchEvaluator]{
                param($m)
                $open = $m.Groups[1].Value
                $inner = $m.Groups[2].Value
                $close = $m.Groups[3].Value

                return $open + $inner + "`r`n" + $userContextBlock + "`r`n" + $close
            },
            1
        )
    }
    else {
        Write-Host "Could not confidently find sidebar block in base.html. CSS was added, but sidebar user context was not inserted automatically."
    }
}

Set-Content -Path $basePath -Value $baseContent -Encoding UTF8
Write-Host "Updated base.html"

Write-Host ""
Write-Host "Patch applied."
Write-Host "Next:"
Write-Host "1. Run: python manage.py runserver"
Write-Host "2. Refresh the page"
Write-Host "3. Confirm the header stays sticky"
Write-Host "4. Confirm user context appears at the bottom of the left drawer"