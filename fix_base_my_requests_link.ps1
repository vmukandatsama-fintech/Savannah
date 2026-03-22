$ErrorActionPreference = "Stop"

$basePath = ".\templates\base.html"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item $basePath "$basePath.bak_$timestamp"

$baseContent = Get-Content $basePath -Raw

if ($baseContent -notmatch '/requests/my-requests/') {
    $pattern = '<a href="/requests/create/">Create Request</a>|<a href="/requests/create/">Requests</a>'
    $replacement = @'
<a href="/requests/create/">Create Request</a>
                <a href="/requests/my-requests/">My Requests</a>
'@

    $baseContent = [regex]::Replace($baseContent, $pattern, $replacement, 1)
    Set-Content -Path $basePath -Value $baseContent -Encoding UTF8
    Write-Host "Updated base.html"
}
else {
    Write-Host "My Requests link already exists."
}