from typing import Any
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

def get_item_types() -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute("EXEC dbo.sp_GetItemTypes")
        return _fetch_first_resultset_as_dicts(cursor)

def get_item_type_by_code(item_type_code: str) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            "EXEC dbo.sp_GetItemTypeByCode @ItemTypeCode=%s",
            [item_type_code],
        )
        rows = _fetch_first_resultset_as_dicts(cursor)
        return rows[0] if rows else None

def create_item_type(item_type_code: str, item_type_name: str) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            EXEC dbo.sp_CreateItemType
                @ItemTypeCode=%s,
                @ItemTypeName=%s
            """,
            [item_type_code, item_type_name],
        )
        rows = _fetch_first_resultset_as_dicts(cursor)
        return rows[0] if rows else None

def update_item_type(item_type_code: str, item_type_name: str) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            EXEC dbo.sp_UpdateItemType
                @ItemTypeCode=%s,
                @ItemTypeName=%s
            """,
            [item_type_code, item_type_name],
        )
        rows = _fetch_first_resultset_as_dicts(cursor)
        return rows[0] if rows else None

def toggle_item_type_status(item_type_code: str) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            "EXEC dbo.sp_ToggleItemTypeStatus @ItemTypeCode=%s",
            [item_type_code],
        )
        rows = _fetch_first_resultset_as_dicts(cursor)
        return rows[0] if rows else None
