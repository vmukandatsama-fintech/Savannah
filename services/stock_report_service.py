from django.db import connection


def _fetch_all_as_dict(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_stock_balance_report(item_code=None, item_name=None, category_code=None, low_stock_only=False):
    sql = """
    SELECT
        sb.ItemCode,
        i.Name AS ItemName,
        i.CategoryCode,
        c.Name AS CategoryName,
        i.UOMCode,
        u.Name AS UOMName,
        ISNULL(sb.PhysicalStock, 0) AS PhysicalStock,
        ISNULL(sb.ReservedQty, 0) AS ReservedQty,
        ISNULL(sb.AvailableStock, 0) AS AvailableStock,
        ISNULL(i.MinStockLevel, 0) AS MinStockLevel,
        ISNULL(i.ReorderLevel, 0) AS ReorderLevel,
        ISNULL(i.MaxStockLevel, 0) AS MaxStockLevel,
        CASE
            WHEN ISNULL(sb.AvailableStock, 0) <= ISNULL(i.MinStockLevel, 0) THEN 1
            ELSE 0
        END AS IsLowStock
    FROM dbo.vw_StockBalance sb
    LEFT JOIN dbo.Inventory i
        ON sb.ItemCode = i.ItemCode
    LEFT JOIN dbo.Categories c
        ON i.CategoryCode = c.CategoryCode
    LEFT JOIN dbo.UOM u
        ON i.UOMCode = u.UOMCode
    WHERE 1 = 1
    """
    params = []

    if item_code:
        sql += " AND sb.ItemCode LIKE %s"
        params.append(f"%{item_code}%")

    if item_name:
        sql += " AND i.Name LIKE %s"
        params.append(f"%{item_name}%")

    if category_code:
        sql += " AND i.CategoryCode = %s"
        params.append(category_code)

    if low_stock_only:
        sql += " AND ISNULL(sb.AvailableStock, 0) <= ISNULL(i.MinStockLevel, 0)"

    sql += " ORDER BY i.Name, sb.ItemCode"

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return _fetch_all_as_dict(cursor)


def get_low_stock_report(item_code=None, item_name=None, category_code=None):
    return get_stock_balance_report(
        item_code=item_code,
        item_name=item_name,
        category_code=category_code,
        low_stock_only=True,
    )


def get_stock_card(item_code, date_from=None, date_to=None):
    sql = """
    SELECT
        TransactionDate,
        ItemCode,
        ItemName,
        CategoryCode,
        TransactionType,
        Direction,
        SignedQuantity
    FROM dbo.vw_StockMovement
    WHERE ItemCode = %s
    """
    params = [item_code]

    if date_from:
        sql += " AND CAST(TransactionDate AS DATE) >= %s"
        params.append(date_from)

    if date_to:
        sql += " AND CAST(TransactionDate AS DATE) <= %s"
        params.append(date_to)

    sql += " ORDER BY TransactionDate DESC, LedgerID DESC"

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return _fetch_all_as_dict(cursor)


def get_stock_item_summary(item_code):
    sql = """
    SELECT TOP 1
        sb.ItemCode,
        i.Name AS ItemName,
        i.CategoryCode,
        c.Name AS CategoryName,
        i.UOMCode,
        u.Name AS UOMName,
        ISNULL(sb.PhysicalStock, 0) AS PhysicalStock,
        ISNULL(sb.ReservedQty, 0) AS ReservedQty,
        ISNULL(sb.AvailableStock, 0) AS AvailableStock,
        ISNULL(i.MinStockLevel, 0) AS MinStockLevel,
        ISNULL(i.ReorderLevel, 0) AS ReorderLevel,
        ISNULL(i.MaxStockLevel, 0) AS MaxStockLevel
    FROM dbo.vw_StockBalance sb
    LEFT JOIN dbo.Inventory i
        ON sb.ItemCode = i.ItemCode
    LEFT JOIN dbo.Categories c
        ON i.CategoryCode = c.CategoryCode
    LEFT JOIN dbo.UOM u
        ON i.UOMCode = u.UOMCode
    WHERE sb.ItemCode = %s
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [item_code])
        rows = _fetch_all_as_dict(cursor)
        return rows[0] if rows else None


def get_stock_categories():
    sql = """
    SELECT DISTINCT
        i.CategoryCode,
        c.Name AS CategoryName
    FROM dbo.Inventory i
    LEFT JOIN dbo.Categories c
        ON i.CategoryCode = c.CategoryCode
    WHERE i.CategoryCode IS NOT NULL
    ORDER BY c.Name, i.CategoryCode
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return _fetch_all_as_dict(cursor)
