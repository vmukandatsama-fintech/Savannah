from typing import Any
from django.db import connection

def _fetch_one(cursor) -> dict[str, Any] | None:
    columns = [col[0] for col in cursor.description]
    row = cursor.fetchone()
    if not row:
        return None
    return dict(zip(columns, row))

def regenerate_collection_voucher(collection_number: str) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            EXEC dbo.sp_RegenerateVoucher
                @CollectionNumber=%s
            """,
            [collection_number],
        )

        if cursor.description:
            return _fetch_one(cursor)

    return None
