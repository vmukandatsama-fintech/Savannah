from django.db import connection


def get_my_requests(user_email, search="", status="", page=1, page_size=10):
    page = max(int(page or 1), 1)
    page_size = max(int(page_size or 10), 1)
    offset = (page - 1) * page_size

    search = (search or "").strip()
    status = (status or "").strip()

    where_clauses = ["r.RequestorEmail = %s"]
    params = [user_email]

    if search:
        where_clauses.append("r.RequestNumber LIKE %s")
        params.append(f"%{search}%")

    if status:
        where_clauses.append("r.StatusName = %s")
        params.append(status)

    where_sql = " AND ".join(where_clauses)

    count_sql = f"""
        SELECT COUNT(1)
        FROM dbo.Requests r
        WHERE {where_sql}
    """

    data_sql = f"""
        SELECT
            r.RequestNumber,
            r.RequestDate,
            r.FarmerName,
            r.DepartmentCode,
            r.StatusName,
            COUNT(ri.LineItemID) AS TotalLines
        FROM dbo.Requests r
        LEFT JOIN dbo.RequestedItems ri
            ON r.RequestNumber = ri.RequestNumber
        WHERE {where_sql}
        GROUP BY
            r.RequestNumber,
            r.RequestDate,
            r.FarmerName,
            r.DepartmentCode,
            r.StatusName
        ORDER BY r.RequestDate DESC
        OFFSET %s ROWS FETCH NEXT %s ROWS ONLY
    """

    with connection.cursor() as cursor:
        cursor.execute(count_sql, params)
        total_count = cursor.fetchone()[0]

        cursor.execute(data_sql, params + [offset, page_size])
        rows = cursor.fetchall()

    requests = [
        {
            "request_number": row[0],
            "request_date": row[1],
            "farmer_name": row[2],
            "department_code": row[3],
            "status_name": row[4],
            "total_lines": row[5],
        }
        for row in rows
    ]

    return {
        "rows": requests,
        "page": page,
        "page_size": page_size,
        "total_count": total_count,
        "has_previous": page > 1,
        "has_next": (offset + page_size) < total_count,
        "previous_page": page - 1,
        "next_page": page + 1,
    }
