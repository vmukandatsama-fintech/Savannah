$ErrorActionPreference = "Stop"

$requestServicePath = ".\services\request_service.py"
$settingsPath = ".\config\settings.py"

if (-not (Test-Path $requestServicePath)) {
    throw "request_service.py not found at: $requestServicePath"
}

if (-not (Test-Path $settingsPath)) {
    throw "settings.py not found at: $settingsPath"
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

Copy-Item $requestServicePath "$requestServicePath.bak_$timestamp"
Copy-Item $settingsPath "$settingsPath.bak_$timestamp"

Write-Host "Backups created."

$requestServiceContent = @'
import json
import logging
from django.db import connection

logger = logging.getLogger(__name__)


def create_request_from_cart(user_email, header, cart):
    normalized_cart = [
        {
            "LineNumber": index + 1,
            "ItemCode": str(item["code"]).strip(),
            "QuantityRequested": float(item["qty"]),
            "UOMCode": str(item["uom"]).strip(),
        }
        for index, item in enumerate(cart)
    ]

    cart_json = json.dumps(normalized_cart, ensure_ascii=False)

    logger.warning("========== CREATE REQUEST FROM CART ==========")
    logger.warning("UserEmail=%r", user_email)
    logger.warning("Header=%r", header)
    logger.warning("CartRaw=%r", cart)
    logger.warning("CartNormalized=%r", normalized_cart)
    logger.warning("CartJson=%s", cart_json)

    precheck_sql = """
        SELECT
            l.LineNumber,
            l.ItemCode,
            l.UOMCode,
            l.QuantityRequested,
            i.IsActive,
            b.PhysicalStock,
            b.ReservedQty,
            b.AvailableStock,
            CASE
                WHEN i.ItemCode IS NULL THEN 'INVALID ITEM'
                WHEN b.ItemCode IS NULL THEN 'NO STOCK VIEW ROW'
                WHEN ISNULL(CAST(b.AvailableStock AS DECIMAL(18,2)), 0) < l.QuantityRequested THEN 'INSUFFICIENT'
                ELSE 'OK'
            END AS ValidationResult
        FROM OPENJSON(%s)
        WITH
        (
            LineNumber INT '$.LineNumber',
            ItemCode NVARCHAR(100) '$.ItemCode',
            QuantityRequested DECIMAL(18,2) '$.QuantityRequested',
            UOMCode NVARCHAR(20) '$.UOMCode'
        ) l
        LEFT JOIN dbo.Inventory i
            ON l.ItemCode = i.ItemCode
        LEFT JOIN dbo.vw_StockBalance b
            ON l.ItemCode = b.ItemCode
        ORDER BY l.LineNumber;
    """

    try:
        with connection.cursor() as cursor:
            cursor.execute(precheck_sql, [cart_json])
            precheck_rows = cursor.fetchall()
            precheck_columns = [col[0] for col in cursor.description]

        logger.warning("PrecheckColumns=%r", precheck_columns)

        bad_rows = []
        for row in precheck_rows:
            row_dict = dict(zip(precheck_columns, row))
            logger.warning("PrecheckRow=%r", row_dict)
            if row_dict["ValidationResult"] != "OK":
                bad_rows.append(row_dict)

        if bad_rows:
            first_bad = bad_rows[0]
            raise Exception(
                "Cart validation failed before SQL submit. "
                f"Line={first_bad.get('LineNumber')}, "
                f"ItemCode={first_bad.get('ItemCode')}, "
                f"UOM={first_bad.get('UOMCode')}, "
                f"Requested={first_bad.get('QuantityRequested')}, "
                f"Available={first_bad.get('AvailableStock')}, "
                f"Result={first_bad.get('ValidationResult')}"
            )

        with connection.cursor() as cursor:
            cursor.execute(
                """
                EXEC sp_CreateRequest
                    @RequestorEmail = %s,
                    @DepartmentCode = %s,
                    @RequiredDate = %s,
                    @GrowerNumber = %s,
                    @CollectorName = %s,
                    @CollectorNationalID = %s,
                    @TruckRegistration = %s,
                    @TrailerRegistration = %s,
                    @AuthorizationRequired = %s,
                    @Justification = %s,
                    @CartJson = %s
                """,
                [
                    user_email,
                    header["department_code"],
                    header["required_date"],
                    header["grower_number"],
                    header["collector_name"],
                    header["collector_national_id"],
                    header["truck_registration"],
                    header["trailer_registration"],
                    header["authorization_required"],
                    header["justification"],
                    cart_json,
                ]
            )

            row = cursor.fetchone()
            logger.warning("StoredProcedureRow=%r", row)

            if row:
                return row[0]

        return None

    except Exception:
        logger.exception("create_request_from_cart failed")
        raise
'@

Set-Content -Path $requestServicePath -Value $requestServiceContent -Encoding UTF8
Write-Host "Updated request_service.py"

$settingsContent = Get-Content $settingsPath -Raw

if ($settingsContent -notmatch '(?ms)^\s*LOGGING\s*=') {
    $loggingBlock = @'

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}
'@

    Add-Content -Path $settingsPath -Value $loggingBlock -Encoding UTF8
    Write-Host "Appended LOGGING block to settings.py"
}
else {
    Write-Host "LOGGING already exists in settings.py"
}

Write-Host "Patch applied successfully."