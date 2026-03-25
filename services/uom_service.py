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

def get_uoms_master() -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute("EXEC dbo.sp_GetUOMs")
        return _fetch_first_resultset_as_dicts(cursor)

def get_uom_by_code(uom_code: str) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            "EXEC dbo.sp_GetUOMByCode @UOMCode=%s",
            [uom_code],
        )
        rows = _fetch_first_resultset_as_dicts(cursor)
        return rows[0] if rows else None

def create_uom(
    uom_code: str,
    name: str,
    uom_type: str | None,
    description: str | None,
) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            EXEC dbo.sp_CreateUOM
                @UOMCode=%s,
                @Name=%s,
                @UOMType=%s,
                @Description=%s
            """,
            [uom_code, name, uom_type, description],
        )
        rows = _fetch_first_resultset_as_dicts(cursor)
        return rows[0] if rows else None

def update_uom(
    uom_code: str,
    name: str,
    uom_type: str | None,
    description: str | None,
) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            EXEC dbo.sp_UpdateUOM
                @UOMCode=%s,
                @Name=%s,
                @UOMType=%s,
                @Description=%s
            """,
            [uom_code, name, uom_type, description],
        )
        rows = _fetch_first_resultset_as_dicts(cursor)
        return rows[0] if rows else None
