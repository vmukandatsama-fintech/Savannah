from django.db import connection


def get_item_categories():
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


def get_item_uoms():
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


def get_requestable_items(
    search_text="",
    category_code="",
    stock_filter="",
    uom_code="",
    page=1,
    page_size=10,
):
    page = max(int(page or 1), 1)
    page_size = max(int(page_size or 10), 1)
    offset = (page - 1) * page_size

    search_text = (search_text or "").strip()
    category_code = (category_code or "").strip()
    stock_filter = (stock_filter or "").strip()
    uom_code = (uom_code or "").strip()

    where_clauses = ["i.IsActive = 1"]
    params = []

    if search_text:
        where_clauses.append("(i.ItemCode LIKE %s OR i.Name LIKE %s)")
        like_value = f"%{search_text}%"
        params.extend([like_value, like_value])

    if category_code:
        where_clauses.append("i.CategoryCode = %s")
        params.append(category_code)

    if uom_code:
        where_clauses.append("i.UOMCode = %s")
        params.append(uom_code)

    if stock_filter == "in_stock":
        where_clauses.append("ISNULL(b.AvailableStock, 0) > 0")
    elif stock_filter == "low_stock":
        where_clauses.append("ISNULL(b.AvailableStock, 0) > 0 AND ISNULL(b.AvailableStock, 0) < 20")
    elif stock_filter == "out_of_stock":
        where_clauses.append("ISNULL(b.AvailableStock, 0) = 0")

    where_sql = " AND ".join(where_clauses)

    count_sql = f"""
        SELECT COUNT(1)
        FROM dbo.Inventory i
        LEFT JOIN dbo.vw_StockBalance b
            ON i.ItemCode = b.ItemCode
        WHERE {where_sql}
    """

    sql = """
        SELECT
            i.ItemCode,
            i.Name,
            i.CategoryCode,
            i.UOMCode,
            CAST(ISNULL(b.AvailableStock, 0) AS DECIMAL(18,2)) AS AvailableStock
        FROM dbo.Inventory i
        LEFT JOIN dbo.vw_StockBalance b
            ON i.ItemCode = b.ItemCode
        WHERE {where_sql}
        ORDER BY i.Name
        OFFSET %s ROWS FETCH NEXT %s ROWS ONLY
    """

    with connection.cursor() as cursor:
        cursor.execute(count_sql, params)
        total_count = cursor.fetchone()[0]

        cursor.execute(sql.format(where_sql=where_sql), params + [offset, page_size])
        rows = cursor.fetchall()

    items = [
        {
            "code": row[0],
            "name": row[1],
            "category": row[2],
            "uom": row[3],
            "available": float(row[4] or 0),
        }
        for row in rows
    ]

    has_next = (offset + page_size) < total_count
    has_previous = page > 1

    return {
        "items": items,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "has_next": has_next,
        "has_previous": has_previous,
        "next_page": page + 1,
        "previous_page": page - 1,
    }
