from typing import Any
import json
from django.db import connection



    return dict(zip(columns, row))
                d.DepartmentCode,
        sql = """
        cursor.execute(

                @IssueJson=%s
        sql += " ORDER BY c.CollectionDate DESC"
from typing import Any
import json
from django.db import connection


            """,
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]


            [collection_number],
    columns = [col[0] for col in cursor.description]
    row = cursor.fetchone()
    if not row:
        return None
    return dict(zip(columns, row))


        )
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT DISTINCT
                d.DepartmentCode,
                d.Name AS DepartmentName
            FROM dbo.Requests r
            INNER JOIN dbo.Departments d
                ON d.DepartmentCode = r.DepartmentCode
            WHERE r.StatusName IN ('Pending Collection', 'Partially Issued')
            ORDER BY d.Name
            """
        )
        return _fetch_all(cursor)


        lines = _fetch_all(cursor)
    with connection.cursor() as cursor:
        sql = """
            SELECT
                r.RequestNumber,
                r.RequestDate,
                r.RequiredDate,
                r.RequestorEmail,
                u.Name AS RequestorName,
                r.DepartmentCode,
                d.Name AS DepartmentName,
                r.GrowerNumber,
                f.Name AS FarmerName,
                r.CollectorName,
                r.TruckRegistration,
                r.StatusName
            FROM dbo.Requests r
            LEFT JOIN dbo.Users u
                ON u.Email = r.RequestorEmail
            LEFT JOIN dbo.Departments d
                ON d.DepartmentCode = r.DepartmentCode
            LEFT JOIN dbo.Farmers f
                ON f.GrowerNumber = r.GrowerNumber
            WHERE r.StatusName IN ('Pending Collection', 'Partially Issued')
        """
        params: list[Any] = []

        if department_code:
            sql += " AND r.DepartmentCode = %s"
            params.append(department_code)

        if search:
            sql += """
                AND (
                    r.RequestNumber LIKE %s
                    OR r.GrowerNumber LIKE %s
                    OR f.Name LIKE %s
                    OR r.CollectorName LIKE %s
                    OR u.Name LIKE %s
                )
            """
            like_value = f"%{search}%"
            params.extend([like_value, like_value, like_value, like_value, like_value])

        sql += " ORDER BY r.RequestDate DESC"

        cursor.execute(sql, params)
        return _fetch_all(cursor)



    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT TOP 1
                r.RequestNumber,
                r.RequestDate,
                r.RequiredDate,
                r.RequestorEmail,
                u.Name AS RequestorName,
                r.DepartmentCode,
                d.Name AS DepartmentName,
                r.GrowerNumber,
                f.Name AS FarmerName,
                r.CollectorName,
                r.CollectorNationalID,
                r.TruckRegistration,
                r.TrailerRegistration,
                r.StatusName
            FROM dbo.Requests r
            LEFT JOIN dbo.Users u
                ON u.Email = r.RequestorEmail
            LEFT JOIN dbo.Departments d
                ON d.DepartmentCode = r.DepartmentCode
            LEFT JOIN dbo.Farmers f
                ON f.GrowerNumber = r.GrowerNumber
            WHERE r.RequestNumber = %s
            """,
            [request_number],
        )
        header = _fetch_one(cursor)

    if not header:
        return None

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                ri.LineNumber,
                ri.ItemCode,
                i.Name AS ItemName,
                ri.UOMCode,
                u.Name AS UOMName,
                ri.QuantityRequested,
                ri.QuantityIssued,
                ri.QuantityReserved,
                (ISNULL(ri.QuantityRequested, 0) - ISNULL(ri.QuantityIssued, 0)) AS QuantityRemaining,
                ri.LineStatus,
                ri.StockStatus
            FROM dbo.RequestedItems ri
            LEFT JOIN dbo.Inventory i
                ON i.ItemCode = ri.ItemCode
            LEFT JOIN dbo.UOM u
                ON u.UOMCode = ri.UOMCode
            WHERE ri.RequestNumber = %s
              AND (ISNULL(ri.QuantityRequested, 0) - ISNULL(ri.QuantityIssued, 0)) > 0
            ORDER BY ri.LineNumber
            """,
            [request_number],
        )
        lines = _fetch_all(cursor)

    return {"header": header, "lines": lines}


    return {
    payload = json.dumps(issue_lines)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            EXEC dbo.sp_DisburseRequest
                @RequestNumber=%s,
                @DisbursedBy=%s,
                @IssueJson=%s
            """,
            [request_number, disbursed_by, payload],
        )


        "header": header,
    search: str = "",
    collection_number: str = "",
    request_number: str = "",
    department_code_filter: str = "",
    date_from: str = "",
    date_to: str = "",
) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        sql = """
            SELECT
                c.CollectionNumber,
                c.CollectionDate,
                c.RequestNumber,
                c.DisbursedBy,
                r.DepartmentCode,
                d.Name AS DepartmentName,
                f.Name AS FarmerName,
                r.CollectorName,
                u.Name AS DisbursedByName
            FROM dbo.Collections c
            LEFT JOIN dbo.Requests r
                ON r.RequestNumber = c.RequestNumber
            LEFT JOIN dbo.Departments d
                ON d.DepartmentCode = r.DepartmentCode
            LEFT JOIN dbo.Users u
                ON u.Email = c.DisbursedBy
            LEFT JOIN dbo.Farmers f
                ON f.GrowerNumber = r.GrowerNumber
            WHERE 1 = 1
        """
        params: list[Any] = []

        if collection_number:
            sql += " AND c.CollectionNumber LIKE %s"
            params.append(f"%{collection_number}%")

        if request_number:
            sql += " AND c.RequestNumber LIKE %s"
            params.append(f"%{request_number}%")

        if department_code_filter:
            sql += " AND r.DepartmentCode = %s"
            params.append(department_code_filter)

        if date_from:
            sql += " AND CAST(c.CollectionDate AS date) >= %s"
            params.append(date_from)

        if date_to:
            sql += " AND CAST(c.CollectionDate AS date) <= %s"
            params.append(date_to)

        if search:
            sql += """
                AND (
                    c.CollectionNumber LIKE %s
                    OR c.RequestNumber LIKE %s
                    OR r.GrowerNumber LIKE %s
                    OR r.CollectorName LIKE %s
                    OR u.Name LIKE %s
                    OR c.DisbursedBy LIKE %s
                )
            """
            like_value = f"%{search}%"
            params.extend([like_value, like_value, like_value, like_value, like_value, like_value])

        sql += " ORDER BY c.CollectionDate DESC"

        cursor.execute(sql, params)
        return _fetch_all(cursor)


        "lines": lines,
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT TOP 1
                c.CollectionNumber,
                c.CollectionDate,
                c.RequestNumber,
                c.DisbursedBy,
                c.VoucherPath,
                c.VoucherStatus,
                c.VoucherError,
                u.Name AS DisbursedByName,
                r.DepartmentCode,
                d.Name AS DepartmentName,
                f.Name AS FarmerName,
                r.CollectorName,
                r.CollectorNationalID,
                r.TruckRegistration,
                r.TrailerRegistration,
                r.StatusName
            FROM dbo.Collections c
            LEFT JOIN dbo.Requests r
                ON r.RequestNumber = c.RequestNumber
            LEFT JOIN dbo.Departments d
                ON d.DepartmentCode = r.DepartmentCode
            LEFT JOIN dbo.Users u
                ON u.Email = c.DisbursedBy
            LEFT JOIN dbo.Farmers f
                ON f.GrowerNumber = r.GrowerNumber
            WHERE c.CollectionNumber = %s
            """,
            [collection_number],
        )
        header = _fetch_one(cursor)

    if not header:
        return None

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                ci.ID,
                ci.CollectionNumber,
                ci.LineNumber,
                ci.ItemName,
                ci.ItemCode,
                ci.UOM,
                ci.QuantityRequested,
                ci.ThisIssueQty,
                ci.TotalIssuedToDate,
                ci.RemainingAfterIssue,
                ci.CreatedDate
            FROM dbo.CollectionItems ci
            WHERE ci.CollectionNumber = %s
            ORDER BY ci.LineNumber
            """,
            [collection_number],
        )
        lines = _fetch_all(cursor)

    return {"header": header, "lines": lines}
    }