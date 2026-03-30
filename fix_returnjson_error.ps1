$ErrorActionPreference = "Stop"

Write-Host "=== Savannah Returns Fix: @ReturnJson patch ===" -ForegroundColor Cyan

$root = Get-Location
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = Join-Path $root "backup_return_fix_$timestamp"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

Write-Host "Project root: $($root.Path)"
Write-Host "Backup folder: $backupDir"

function Backup-File {
    param(
        [string]$filePath
    )

    $resolved = (Resolve-Path $filePath).Path
    $relative = $resolved.Substring($root.Path.Length).TrimStart('\')
    $dest = Join-Path $backupDir $relative
    $destDir = Split-Path $dest -Parent

    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }

    Copy-Item $filePath $dest -Force
}

$pyFiles = Get-ChildItem -Path $root -Recurse -Filter *.py | Where-Object {
    $_.FullName -notmatch '\\.venv\\' -and
    $_.FullName -notmatch '\\venv\\' -and
    $_.FullName -notmatch '\\site-packages\\' -and
    $_.FullName -notmatch '\\__pycache__\\'
}

$targetFiles = @()

foreach ($file in $pyFiles) {
    $content = Get-Content $file.FullName -Raw
    if ($content -match 'sp_ReturnIssuedStock' -or $content -match 'def\s+process_return\s*\(') {
        $targetFiles += $file.FullName
    }
}

if ($targetFiles.Count -eq 0) {
    Write-Host "No matching Python files found." -ForegroundColor Yellow
    exit
}

Write-Host ""
Write-Host "Files to inspect/patch:" -ForegroundColor Green
$targetFiles | ForEach-Object { Write-Host " - $_" }
Write-Host ""

$replacementExec = @'
cursor.execute(
            """
            EXEC dbo.sp_ReturnIssuedStock
                @CollectionNumber=%s,
                @ReturnedBy=%s,
                @ReturnJson=%s,
                @Reason=%s
            """,
            [collection_number, returned_by, return_json, reason],
        )
'@

foreach ($filePath in $targetFiles) {
    $original = Get-Content $filePath -Raw
    $updated = $original
    $changed = $false

    # 1. Update simple function signature
    $pattern1 = 'def\s+process_return\s*\(\s*collection_number\s*,\s*returned_by\s*,\s*reason\s*\)\s*:'
    $replacement1 = 'def process_return(collection_number, returned_by, reason, return_json):'
    $newText = [regex]::Replace($updated, $pattern1, $replacement1)
    if ($newText -ne $updated) {
        $updated = $newText
        $changed = $true
        Write-Host "Updated simple function signature in $filePath" -ForegroundColor Yellow
    }

    # 2. Update typed function signature
    $pattern2 = 'def\s+process_return\s*\(\s*collection_number\s*:\s*str\s*,\s*returned_by\s*:\s*str\s*,\s*reason\s*:\s*str\s*\)\s*(->\s*None)?\s*:'
    $replacement2 = 'def process_return(collection_number: str, returned_by: str, reason: str, return_json: str) -> None:'
    $newText = [regex]::Replace($updated, $pattern2, $replacement2)
    if ($newText -ne $updated) {
        $updated = $newText
        $changed = $true
        Write-Host "Updated typed function signature in $filePath" -ForegroundColor Yellow
    }

    # 3. Replace multiline EXEC call missing @ReturnJson
    $pattern3 = @'
(?s)cursor\.execute\(\s*"""
\s*EXEC\s+dbo\.sp_ReturnIssuedStock\s+@CollectionNumber=%s,\s*@ReturnedBy=%s,\s*@Reason=%s
\s*"""\s*,\s*\[\s*collection_number\s*,\s*returned_by\s*,\s*reason\s*\]\s*\)
'@
    $newText = [regex]::Replace($updated, $pattern3.Trim(), [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $replacementExec })
    if ($newText -ne $updated) {
        $updated = $newText
        $changed = $true
        Write-Host "Updated multiline cursor.execute call in $filePath" -ForegroundColor Yellow
    }

    # 4. Replace single-line double-quoted EXEC call missing @ReturnJson
    $pattern4 = 'cursor\.execute\(\s*"EXEC\s+dbo\.sp_ReturnIssuedStock\s+@CollectionNumber=%s,\s*@ReturnedBy=%s,\s*@Reason=%s"\s*,\s*\[\s*collection_number\s*,\s*returned_by\s*,\s*reason\s*\]\s*\)'
    $newText = [regex]::Replace($updated, $pattern4, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $replacementExec })
    if ($newText -ne $updated) {
        $updated = $newText
        $changed = $true
        Write-Host "Updated single-line double-quoted cursor.execute call in $filePath" -ForegroundColor Yellow
    }

    # 5. Replace single-line single-quoted EXEC call missing @ReturnJson
    $pattern5 = "cursor\.execute\(\s*'EXEC\s+dbo\.sp_ReturnIssuedStock\s+@CollectionNumber=%s,\s*@ReturnedBy=%s,\s*@Reason=%s'\s*,\s*\[\s*collection_number\s*,\s*returned_by\s*,\s*reason\s*\]\s*\)"
    $newText = [regex]::Replace($updated, $pattern5, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $replacementExec })
    if ($newText -ne $updated) {
        $updated = $newText
        $changed = $true
        Write-Host "Updated single-line single-quoted cursor.execute call in $filePath" -ForegroundColor Yellow
    }

    if ($changed -and $updated -ne $original) {
        Backup-File -filePath $filePath
        Set-Content -Path $filePath -Value $updated -Encoding UTF8
        Write-Host "Saved patched file: $filePath" -ForegroundColor Green
    }
    else {
        Write-Host "No direct patch applied to: $filePath" -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "=== Patch complete ===" -ForegroundColor Cyan
Write-Host "Backups are in: $backupDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "Now check for any remaining process_return calls:" -ForegroundColor Yellow
Write-Host 'Get-ChildItem -Recurse -Filter *.py | Select-String -Pattern "process_return\("' -ForegroundColor White
Write-Host ""
Write-Host "Expected service call now includes return_json." -ForegroundColor Yellow