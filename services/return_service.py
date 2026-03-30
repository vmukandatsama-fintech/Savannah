import json
from django.db import connection


def _fetch_all_as_dict(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


# ================================
# COLLECTION LIST
# ================================
def get_returnable_collections(collection_number=None, request_number=None, grower_number=None, date_from=None, date_to=None):
    sql = """
    SELECT
        c.CollectionNumber,
        c.CollectionDate,
        c.RequestNumber,
        r.GrowerNumber,
        r.FarmerName,
        r.DepartmentCode,
        d.Name AS DepartmentName,
        c.DisbursedBy,
        COUNT(ci.LineNumber) AS LineCount,
        SUM(ISNULL(ci.ThisIssueQty, 0)) AS TotalIssuedQty
    FROM dbo.Collections c
    INNER JOIN dbo.CollectionItems ci
        ON c.CollectionNumber = ci.CollectionNumber
    INNER JOIN dbo.Requests r
        ON c.RequestNumber = r.RequestNumber
    LEFT JOIN dbo.Departments d
        ON r.DepartmentCode = d.DepartmentCode
    WHERE 1 = 1
    """

    params = []

    if collection_number:
        sql += " AND c.CollectionNumber LIKE %s"
        params.append(f"%{collection_number}%")

    if request_number:
        sql += " AND c.RequestNumber LIKE %s"
        params.append(f"%{request_number}%")

    if grower_number:
        sql += " AND r.GrowerNumber LIKE %s"
        params.append(f"%{grower_number}%")

    if date_from:
        sql += " AND CAST(c.CollectionDate AS DATE) >= %s"
        params.append(date_from)

    if date_to:
        sql += " AND CAST(c.CollectionDate AS DATE) <= %s"
        params.append(date_to)

    sql += """
    GROUP BY
        c.CollectionNumber,
        c.CollectionDate,
        c.RequestNumber,
        r.GrowerNumber,
        r.FarmerName,
        r.DepartmentCode,
        d.Name,
        c.DisbursedBy
    ORDER BY c.CollectionDate DESC, c.CollectionNumber DESC
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return _fetch_all_as_dict(cursor)


# ================================
# COLLECTION DETAIL
# ================================
def get_collection_return_detail(collection_number):
    header_sql = """
    SELECT TOP 1
        c.CollectionNumber,
        c.CollectionDate,
        c.RequestNumber,
        r.RequestDate,
        r.RequiredDate,
        r.GrowerNumber,
        r.FarmerName,
        r.DepartmentCode,
        d.Name AS DepartmentName,
        c.DisbursedBy,
        r.StatusName
    FROM dbo.Collections c
    INNER JOIN dbo.Requests r
        ON c.RequestNumber = r.RequestNumber
    LEFT JOIN dbo.Departments d
        ON r.DepartmentCode = d.DepartmentCode
    WHERE c.CollectionNumber = %s
    """

    lines_sql = """
    SELECT
        ci.CollectionNumber,
        ci.LineNumber,
        ci.ItemCode,
        ci.ItemName,
        ci.UOM,
        ISNULL(ci.QuantityRequested, 0) AS QuantityRequested,
        ISNULL(ci.ThisIssueQty, 0) AS ThisIssueQty,
        ISNULL(ci.TotalIssuedToDate, 0) AS TotalIssuedToDate,
        ISNULL(ci.RemainingAfterIssue, 0) AS RemainingAfterIssue
    FROM dbo.CollectionItems ci
    WHERE ci.CollectionNumber = %s
    ORDER BY ci.LineNumber
    """

    with connection.cursor() as cursor:
        cursor.execute(header_sql, [collection_number])
        header_rows = _fetch_all_as_dict(cursor)
        header = header_rows[0] if header_rows else None

    with connection.cursor() as cursor:
        cursor.execute(lines_sql, [collection_number])
        lines = _fetch_all_as_dict(cursor)

    return {
        "header": header,
        "lines": lines,
    }


# ================================
# POST RETURN (FIXED)
# ================================
def post_return_stock(collection_number, returned_by, reason, line_items):
    payload = json.dumps(line_items)

    print("=== DEBUG RETURN ===")
    print("Collection:", collection_number)
    print("User:", returned_by)
    print("JSON:", payload)
    print("Reason:", reason)

    with connection.cursor() as cursor:
        cursor.execute(
            """
            EXEC dbo.sp_ReturnIssuedStock
                @CollectionNumber=%s,
                @ReturnedBy=%s,
                @ReturnJson=%s,
                @Reason=%s
            """,
            [collection_number, returned_by, payload, reason],
        )

        if cursor.description:
            rows = _fetch_all_as_dict(cursor)
            return rows[0] if rows else None

    return None


# ================================
# CANCEL BALANCE
# ================================
def cancel_remaining_balance(request_number, cancelled_by, reason):
    with connection.cursor() as cursor:
        cursor.execute(
            "EXEC dbo.sp_CancelRemainingReservation @RequestNumber=%s, @CancelledBy=%s, @Reason=%s",
            [request_number, cancelled_by, reason],
        )

        if cursor.description:
            rows = _fetch_all_as_dict(cursor)
            return rows[0] if rows else None

    return None