from typing import Any
from django.db import connection


def _fetch_all(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _fetch_first_resultset(cursor):
    while True:
        if cursor.description:
            return _fetch_all(cursor)
        if not cursor.nextset():
            break
    return []


def get_suppliers(search="", is_active=None):
    with connection.cursor() as cursor:
        cursor.execute(
            "EXEC dbo.sp_GetSuppliers @Search=%s, @IsActive=%s",
            [search or None, is_active],
        )
        return _fetch_first_resultset(cursor)


def get_supplier_by_id(supplier_id):
    with connection.cursor() as cursor:
        cursor.execute(
            "EXEC dbo.sp_GetSupplierById @SupplierID=%s",
            [supplier_id],
        )
        rows = _fetch_first_resultset(cursor)
        return rows[0] if rows else None


def create_supplier(name, vat, email, phone, is_active=True):
    with connection.cursor() as cursor:
        cursor.execute(
            "EXEC dbo.sp_CreateSupplier @Name=%s, @VatNumber=%s, @ContactEmail=%s, @ContactPhone=%s, @IsActive=%s",
            [name, vat, email, phone, is_active],
        )
        rows = _fetch_first_resultset(cursor)
        return rows[0] if rows else None


def update_supplier(supplier_id, name, vat, email, phone, is_active):
    with connection.cursor() as cursor:
        cursor.execute(
            "EXEC dbo.sp_UpdateSupplier @SupplierID=%s, @Name=%s, @VatNumber=%s, @ContactEmail=%s, @ContactPhone=%s, @IsActive=%s",
            [supplier_id, name, vat, email, phone, is_active],
        )
        rows = _fetch_first_resultset(cursor)
        return rows[0] if rows else None


def toggle_supplier_status(supplier_id):
    with connection.cursor() as cursor:
        cursor.execute(
            "EXEC dbo.sp_ToggleSupplierActive @SupplierID=%s",
            [supplier_id],
        )
        rows = _fetch_first_resultset(cursor)
        return rows[0] if rows else None
