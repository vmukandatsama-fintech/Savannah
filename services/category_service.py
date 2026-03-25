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


def get_categories(search: str = "", is_active: bool | None = None) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            "EXEC dbo.sp_GetCategories @Search=%s, @IsActive=%s",
            [search or None, is_active],
        )
        return _fetch_first_resultset_as_dicts(cursor)


def get_categories_master(search: str = "", is_active: bool | None = None) -> list[dict[str, Any]]:
    return get_categories(search=search, is_active=is_active)


def get_category_by_id(category_id: int) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            "EXEC dbo.sp_GetCategoryById @CategoryID=%s",
            [category_id],
        )
        rows = _fetch_first_resultset_as_dicts(cursor)
        return rows[0] if rows else None


def create_category(name: str, is_active: bool = True) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            "EXEC dbo.sp_CreateCategory @Name=%s, @IsActive=%s",
            [name, is_active],
        )
        rows = _fetch_first_resultset_as_dicts(cursor)
        return rows[0] if rows else None


def update_category(
    category_id: int,
    name: str,
    is_active: bool,
) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            "EXEC dbo.sp_UpdateCategory @CategoryID=%s, @Name=%s, @IsActive=%s",
            [category_id, name, is_active],
        )
        rows = _fetch_first_resultset_as_dicts(cursor)
        return rows[0] if rows else None


def toggle_category_active(category_id: int) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            "EXEC dbo.sp_ToggleCategoryActive @CategoryID=%s",
            [category_id],
        )
        rows = _fetch_first_resultset_as_dicts(cursor)
        return rows[0] if rows else None


def toggle_category_status(category_id: int) -> dict[str, Any] | None:
    return toggle_category_active(category_id)