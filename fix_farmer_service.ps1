$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Rewriting farmer_service.py with column auto-detection..." -ForegroundColor Cyan

if (!(Test-Path "services")) {
    New-Item -ItemType Directory -Path "services" | Out-Null
}

$farmerService = @'
from django.db import connection


def get_active_farmers():
    table_name = "Farmers"

    with connection.cursor() as cursor:
        # Read actual column names from SQL Server
        cursor.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """, [table_name])
        columns = [row[0] for row in cursor.fetchall()]

    if not columns:
        raise Exception(f"Table '{table_name}' was not found or has no columns.")

    # Likely candidate columns
    grower_number_candidates = [
        "GrowerNumber", "FarmerNumber", "GrowerNo", "FarmerNo", "Code", "Grower_Code"
    ]
    grower_name_candidates = [
        "GrowerName", "FarmerName", "Name", "Grower", "Farmer", "DisplayName"
    ]
    active_candidates = [
        "IsActive", "Active", "Is_Active", "RecordActive"
    ]

    grower_number_col = next((c for c in grower_number_candidates if c in columns), None)
    grower_name_col = next((c for c in grower_name_candidates if c in columns), None)
    active_col = next((c for c in active_candidates if c in columns), None)

    if not grower_number_col:
        raise Exception(
            "Could not find farmer number column in Farmers table. "
            f"Available columns: {', '.join(columns)}"
        )

    if not grower_name_col:
        raise Exception(
            "Could not find farmer name column in Farmers table. "
            f"Available columns: {', '.join(columns)}"
        )

    sql = f"SELECT {grower_number_col}, {grower_name_col} FROM {table_name}"

    if active_col:
        sql += f" WHERE {active_col} = 1"

    sql += f" ORDER BY {grower_name_col}"

    with connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()

    return [
        {
            "grower_number": row[0],
            "grower_name": row[1],
        }
        for row in rows
    ]
'@

Set-Content -Path "services\farmer_service.py" -Value $farmerService -Encoding UTF8

Write-Host ""
Write-Host "farmer_service.py updated successfully." -ForegroundColor Green
Write-Host "Next:" -ForegroundColor Cyan
Write-Host "1. python manage.py runserver"
Write-Host "2. Open http://127.0.0.1:8000/requests/create/"