import json
from datetime import datetime
from typing import Any

from django.db import connection


def _fetch_all_as_dicts(cursor) -> list[dict[str, Any]]:
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]


def _fetch_first_resultset_as_dicts(cursor) -> list[dict[str, Any]]:
    while True:
        if cursor.description is not None:
            return _fetch_all_as_dicts(cursor)
        if not cursor.nextset():
            break
    return []


def _fetch_all_resultsets_as_dicts(cursor) -> list[list[dict[str, Any]]]:
    resultsets: list[list[dict[str, Any]]] = []
    while True:
        if cursor.description is not None:
            resultsets.append(_fetch_all_as_dicts(cursor))
        if not cursor.nextset():
            break
    return resultsets


def get_deliveries(
    search: str = "",
    supplier_code: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            EXEC dbo.sp_GetDeliveries
                @Search=%s,
                @SupplierCode=%s,
                @DateFrom=%s,
                @DateTo=%s
            """,
            [search or None, supplier_code, date_from, date_to],
        )
        return _fetch_first_resultset_as_dicts(cursor)


def get_delivery_by_number(delivery_number: str) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            "EXEC dbo.sp_GetDeliveryByNumber @DeliveryNumber=%s",
            [delivery_number],
        )
        resultsets = _fetch_all_resultsets_as_dicts(cursor)
        if not resultsets:
            return None

        header = resultsets[0][0] if resultsets[0] else None
        lines = resultsets[1] if len(resultsets) > 1 else []

        if not header:
            return None

        return {
            "header": header,
            "lines": lines,
        }


def get_active_suppliers() -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute("EXEC dbo.sp_GetActiveSuppliers")
        return _fetch_first_resultset_as_dicts(cursor)


def get_inventory_for_delivery() -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute("EXEC dbo.sp_GetInventoryForDelivery")
        return _fetch_first_resultset_as_dicts(cursor)


def create_delivery(
    delivery_date: str,
    supplier_code: str,
    vehicle_registration: str | None,
    driver_name: str | None,
    waybill_number: str | None,
    received_by_email: str,
    remarks: str | None,
    line_items: list[dict[str, Any]],
) -> dict[str, Any] | None:
    parsed_delivery_date = None
    if delivery_date:
        parsed_delivery_date = datetime.fromisoformat(delivery_date)

    normalized_line_items: list[dict[str, Any]] = []

    for line in line_items:
        expiry_date = line.get("ExpiryDate")

        if expiry_date in ("", None):
            expiry_date = None
        elif isinstance(expiry_date, str):
            expiry_date = datetime.fromisoformat(expiry_date).isoformat(sep=" ")

        normalized_line_items.append(
            {
                "LineNumber": line.get("LineNumber"),
                "ItemCode": line.get("ItemCode"),
                "QuantityReceived": line.get("QuantityReceived"),
                "UOMCode": line.get("UOMCode"),
                "BatchNumber": line.get("BatchNumber"),
                "ExpiryDate": expiry_date,
                "ConditionOnArrival": line.get("ConditionOnArrival"),
                "Remarks": line.get("Remarks"),
            }
        )

    seen_items: set[str] = set()
    for line in normalized_line_items:
        item_code = line.get("ItemCode")
        if item_code in seen_items:
            raise Exception(f"Duplicate item detected: {item_code}")
        seen_items.add(item_code)

    with connection.cursor() as cursor:
        cursor.execute(
            """
            EXEC dbo.sp_CreateDelivery
                @DeliveryDate=%s,
                @SupplierCode=%s,
                @VehicleRegistration=%s,
                @DriverName=%s,
                @WaybillNumber=%s,
                @ReceivedByEmail=%s,
                @Remarks=%s,
                @LineItems=%s
            """,
            [
                parsed_delivery_date,
                supplier_code,
                vehicle_registration,
                driver_name,
                waybill_number,
                received_by_email,
                remarks,
                json.dumps(normalized_line_items),
            ],
        )
        rows = _fetch_first_resultset_as_dicts(cursor)
        return rows[0] if rows else None
import json
from datetime import datetime
from typing import Any

from django.db import connection


def _fetch_all_as_dicts(cursor) -> list[dict[str, Any]]:
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]


def _fetch_first_resultset_as_dicts(cursor) -> list[dict[str, Any]]:
    while True:
        if cursor.description is not None:
            return _fetch_all_as_dicts(cursor)
        if not cursor.nextset():
            break
    return []


def _fetch_all_resultsets_as_dicts(cursor) -> list[list[dict[str, Any]]]:
    resultsets: list[list[dict[str, Any]]] = []
    while True:
        if cursor.description is not None:
            resultsets.append(_fetch_all_as_dicts(cursor))
        if not cursor.nextset():
            break
    return resultsets


def get_deliveries(
    search: str = "",
    supplier_code: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            EXEC dbo.sp_GetDeliveries
                @Search=%s,
                @SupplierCode=%s,
                @DateFrom=%s,
                @DateTo=%s
            """,
            [search or None, supplier_code, date_from, date_to],
        )
        return _fetch_first_resultset_as_dicts(cursor)


def get_delivery_by_number(delivery_number: str) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            "EXEC dbo.sp_GetDeliveryByNumber @DeliveryNumber=%s",
            [delivery_number],
        )
        resultsets = _fetch_all_resultsets_as_dicts(cursor)
        if not resultsets:
            return None

        header = resultsets[0][0] if resultsets[0] else None
        lines = resultsets[1] if len(resultsets) > 1 else []

        if not header:
            return None

        return {
            "header": header,
            "lines": lines,
        }


def get_active_suppliers() -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute("EXEC dbo.sp_GetActiveSuppliers")
        return _fetch_first_resultset_as_dicts(cursor)


def get_inventory_for_delivery() -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute("EXEC dbo.sp_GetInventoryForDelivery")
        return _fetch_first_resultset_as_dicts(cursor)


def create_delivery(
    delivery_date: str,
    supplier_code: str,
    vehicle_registration: str | None,
    driver_name: str | None,
    waybill_number: str | None,
    received_by_email: str,
    remarks: str | None,
    line_items: list[dict[str, Any]],
) -> dict[str, Any] | None:
    parsed_delivery_date = None
    if delivery_date:
        parsed_delivery_date = datetime.fromisoformat(delivery_date)

    normalized_line_items: list[dict[str, Any]] = []

    for line in line_items:
        expiry_date = line.get("ExpiryDate")

        if expiry_date in ("", None):
            expiry_date = None
        elif isinstance(expiry_date, str):
            expiry_date = datetime.fromisoformat(expiry_date).isoformat(sep=" ")

        normalized_line_items.append(
            {
                "LineNumber": line.get("LineNumber"),
                "ItemCode": line.get("ItemCode"),
                "QuantityReceived": line.get("QuantityReceived"),
                "UOMCode": line.get("UOMCode"),
                "BatchNumber": line.get("BatchNumber"),
                "ExpiryDate": expiry_date,
                "ConditionOnArrival": line.get("ConditionOnArrival"),
                "Remarks": line.get("Remarks"),
            }
        )

    with connection.cursor() as cursor:
        cursor.execute(
            """
            EXEC dbo.sp_CreateDelivery
                @DeliveryDate=%s,
                @SupplierCode=%s,
                @VehicleRegistration=%s,
                @DriverName=%s,
                @WaybillNumber=%s,
                @ReceivedByEmail=%s,
                @Remarks=%s,
                @LineItems=%s
            """,
            [
                parsed_delivery_date,
                supplier_code,
                vehicle_registration,
                driver_name,
                waybill_number,
                received_by_email,
                remarks,
                json.dumps(normalized_line_items),
            ],
        )
        rows = _fetch_first_resultset_as_dicts(cursor)
        return rows[0] if rows else None
def get_inventory_for_delivery() -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute("EXEC dbo.sp_GetInventoryForDelivery")
        return _fetch_first_resultset_as_dicts(cursor)