import json
from typing import Any
from django.db import connection

def _fetch_all(cursor) -> list[dict[str, Any]]:
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]

def _fetch_one(cursor) -> dict[str, Any] | None:
    columns = [col[0] for col in cursor.description]
    row = cursor.fetchone()
    if not row:
        return None
    return dict(zip(columns, row))

def get_pending_collections(
    search: str = "",
    department_code: str | None = None,
) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        sql = """
            SELECT
                r.RequestNumber,
                r.RequestDate,
                r.RequiredDate,
                r.RequestorEmail,
                u.Name AS RequestorName,
                r.DepartmentCode,
                d.DepartmentName,
                r.GrowerNumber,
                r.CollectorName,
                r.TruckRegistration,
                r.TrailerRegistration,
                r.StatusName
            FROM dbo.Requests r
            LEFT JOIN dbo.Users u
                ON u.Email = r.RequestorEmail
            LEFT JOIN dbo.Departments d
                ON d.DepartmentCode = r.DepartmentCode
            WHERE r.StatusName = 'Pending Collection'
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
                    OR r.CollectorName LIKE %s
                    OR u.Name LIKE %s
                )
            """
            like_value = f"%{search}%"
            params.extend([like_value, like_value, like_value, like_value])

        sql += " ORDER BY r.RequestDate DESC"

        cursor.execute(sql, params)
        return _fetch_all(cursor)

def get_collection_detail(request_number: str) -> dict[str, Any] | None:
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
                d.DepartmentName,
                r.GrowerNumber,
                r.CollectorName,
                r.CollectorNationalID,
                r.TruckRegistration,
                r.TrailerRegistration,
                r.Justification,
                r.StatusName
            FROM dbo.Requests r
            LEFT JOIN dbo.Users u
                ON u.Email = r.RequestorEmail
            LEFT JOIN dbo.Departments d
                ON d.DepartmentCode = r.DepartmentCode
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
                ri.QuantityRequested,
                ri.QuantityReserved,
                ri.QuantityIssued,
                ri.UOMCode,
                uom.UOMName,
                ri.LineStatus,
                ISNULL(sb.AvailableStock, 0) AS AvailableStock
            FROM dbo.RequestedItems ri
            LEFT JOIN dbo.Items i
                ON i.ItemCode = ri.ItemCode
            LEFT JOIN dbo.UOM uom
                ON uom.UOMCode = ri.UOMCode
            LEFT JOIN dbo.vw_StockBalance sb
                ON sb.ItemCode = ri.ItemCode
            WHERE ri.RequestNumber = %s
            ORDER BY ri.LineNumber
            """,
            [request_number],
        )
        lines = _fetch_all(cursor)

    return {
        "header": header,
        "lines": lines,
    }

def disburse_request(
    request_number: str,
    disbursed_by: str,
    issue_lines: list[dict[str, Any]],
) -> dict[str, Any] | None:
    items_json = json.dumps(issue_lines)

    with connection.cursor() as cursor:
        cursor.execute(
            """
            EXEC dbo.sp_DisburseRequest
                @RequestNumber=%s,
                @DisbursedBy=%s,
                @ItemsJson=%s
            """,
            [request_number, disbursed_by, items_json],
        )

        if cursor.description:
            return _fetch_one(cursor)

    return None
import json
from typing import Any
from django.db import connection

def _fetch_all(cursor) -> list[dict[str, Any]]:
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]

def _fetch_one(cursor) -> dict[str, Any] | None:
    columns = [col[0] for col in cursor.description]
    row = cursor.fetchone()
    if not row:
        return None
    return dict(zip(columns, row))

def get_pending_collections(
    search: str = "",
    department_code: str | None = None,
) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        sql = """
            SELECT
                r.RequestNumber,
                r.RequestDate,
                r.RequiredDate,
                r.RequestorEmail,
                u.Name AS RequestorName,
                r.DepartmentCode,
                d.DepartmentName,
                r.GrowerNumber,
                r.CollectorName,
                r.TruckRegistration,
                r.TrailerRegistration,
                r.StatusName
            FROM dbo.Requests r
            LEFT JOIN dbo.Users u
                ON u.Email = r.RequestorEmail
            LEFT JOIN dbo.Departments d
                ON d.DepartmentCode = r.DepartmentCode
            WHERE r.StatusName = 'Pending Collection'
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
                    OR r.CollectorName LIKE %s
                    OR u.Name LIKE %s
                )
            """
            like_value = f"%{search}%"
            params.extend([like_value, like_value, like_value, like_value])

        sql += " ORDER BY r.RequestDate DESC"

        cursor.execute(sql, params)
        return _fetch_all(cursor)

def get_collection_detail(request_number: str) -> dict[str, Any] | None:
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
                d.DepartmentName,
                r.GrowerNumber,
                r.CollectorName,
                r.CollectorNationalID,
                r.TruckRegistration,
                r.TrailerRegistration,
                r.Justification,
                r.StatusName
            FROM dbo.Requests r
            LEFT JOIN dbo.Users u
                ON u.Email = r.RequestorEmail
            LEFT JOIN dbo.Departments d
                ON d.DepartmentCode = r.DepartmentCode
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
                ri.QuantityRequested,
                ri.QuantityReserved,
                ri.QuantityIssued,
                ri.UOMCode,
                uom.UOMName,
                ri.LineStatus,
                ISNULL(sb.AvailableStock, 0) AS AvailableStock
            FROM dbo.RequestedItems ri
            LEFT JOIN dbo.Items i
                ON i.ItemCode = ri.ItemCode
            LEFT JOIN dbo.UOM uom
                ON uom.UOMCode = ri.UOMCode
            LEFT JOIN dbo.vw_StockBalance sb
                ON sb.ItemCode = ri.ItemCode
            WHERE ri.RequestNumber = %s
            ORDER BY ri.LineNumber
            """,
            [request_number],
        )
        lines = _fetch_all(cursor)

    return {
        "header": header,
        "lines": lines,
    }

def disburse_request(request_number: str, disbursed_by: str, issue_lines: list[dict[str, Any]]) -> None:
    items_json = json.dumps(issue_lines)

    with connection.cursor() as cursor:
        cursor.execute(
            """
            EXEC dbo.sp_DisburseRequest
                @RequestNumber=%s,
                @DisbursedBy=%s,
                @ItemsJson=%s
            """,
            [request_number, disbursed_by, items_json],
        )
