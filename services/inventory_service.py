from typing import Any
from django.db import connection

def get_item_types(active_only: bool = False) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        if active_only:
            cursor.execute("EXEC dbo.sp_GetActiveItemTypes")
        else:
            cursor.execute("EXEC dbo.sp_GetItemTypes")
        return _fetch_first_resultset_as_dicts(cursor)

def get_categories() -> list[str]:
    sql = """
        SELECT DISTINCT
            CategoryCode
        FROM dbo.Inventory
        WHERE IsActive = 1
          AND CategoryCode IS NOT NULL
          AND LTRIM(RTRIM(CategoryCode)) <> ''
        ORDER BY CategoryCode
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
    return [row[0] for row in rows]

def get_uoms() -> list[str]:
    sql = """
        SELECT DISTINCT
            UOMCode
        FROM dbo.Inventory
        WHERE IsActive = 1
          AND UOMCode IS NOT NULL
          AND LTRIM(RTRIM(UOMCode)) <> ''
        ORDER BY UOMCode
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
    return [row[0] for row in rows]
from django.db import connection


def _fetch_all_as_dict(cursor) -> list[dict[str, Any]]:
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _fetch_first_resultset_as_dicts(cursor) -> list[dict[str, Any]]:
    while True:
        if cursor.description is not None:
            return _fetch_all_as_dict(cursor)

        if not cursor.nextset():
            break
    return []


def get_inventory_items() -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute("EXEC dbo.sp_GetInventoryItems")
        return _fetch_first_resultset_as_dicts(cursor)


def get_inventory_item_by_code(item_code: str) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            "EXEC dbo.sp_GetInventoryItemByCode @ItemCode=%s",
            [item_code],
        )
        rows = _fetch_first_resultset_as_dicts(cursor)
        return rows[0] if rows else None


def create_inventory_item(
    name: str,
    description: str | None,
    item_type: str | None,
    category_code: str | None,
    uom_code: str | None,
    reorder_level: float,
    min_stock_level: float,
    max_stock_level: float,
    enabled_stock_alert: bool,
    item_image_path: str | None,
) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            EXEC dbo.sp_CreateInventoryItem
                @Name=%s,
                @Description=%s,
                @ItemType=%s,
                @CategoryCode=%s,
                @UOMCode=%s,
                @ReorderLevel=%s,
                @MinStockLevel=%s,
                @MaxStockLevel=%s,
                @EnabledStockAlert=%s,
                @ItemImagePath=%s
            """,
            [
                name,
                description,
                item_type,
                category_code,
                uom_code,
                reorder_level,
                min_stock_level,
                max_stock_level,
                enabled_stock_alert,
                item_image_path,
            ],
        )
        rows = _fetch_first_resultset_as_dicts(cursor)
        return rows[0] if rows else None


def update_inventory_item(
    item_code: str,
    name: str,
    description: str | None,
    item_type: str | None,
    category_code: str | None,
    uom_code: str | None,
    reorder_level: float,
    min_stock_level: float,
    max_stock_level: float,
    enabled_stock_alert: bool,
    item_image_path: str | None,
) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            EXEC dbo.sp_UpdateInventoryItem
                @ItemCode=%s,
                @Name=%s,
                @Description=%s,
                @ItemType=%s,
                @CategoryCode=%s,
                @UOMCode=%s,
                @ReorderLevel=%s,
                @MinStockLevel=%s,
                @MaxStockLevel=%s,
                @EnabledStockAlert=%s,
                @ItemImagePath=%s
            """,
            [
                item_code,
                name,
                description,
                item_type,
                category_code,
                uom_code,
                reorder_level,
                min_stock_level,
                max_stock_level,
                enabled_stock_alert,
                item_image_path,
            ],
        )
        rows = _fetch_first_resultset_as_dicts(cursor)
        return rows[0] if rows else None


def toggle_inventory_item_status(item_code: str) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            "EXEC dbo.sp_ToggleInventoryItemStatus @ItemCode=%s",
            [item_code],
        )
        rows = _fetch_first_resultset_as_dicts(cursor)
        return rows[0] if rows else None
