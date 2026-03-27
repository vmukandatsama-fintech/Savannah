from typing import Any
from django.db import connection


def _fetch_one(cursor) -> dict[str, Any]:
    columns = [col[0] for col in cursor.description]
    row = cursor.fetchone()
    if not row:
        return {}
    return dict(zip(columns, row))


def _fetch_all(cursor) -> list[dict[str, Any]]:
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]


def get_dashboard_metrics(user_email: str, role_name: str) -> dict[str, Any]:
    role_name = (role_name or "").strip()
    user_email = (user_email or "").strip()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                MyOpenRequests = (
                    SELECT COUNT(1)
                    FROM dbo.Requests r
                    WHERE r.RequestorEmail = %s
                      AND r.StatusName IN (
                          'Pending Approval',
                          'Approved',
                          'Pending Collection',
                          'Partially Issued'
                      )
                ),
                MyPendingApprovals = (
                    SELECT COUNT(1)
                    FROM dbo.Approvals a
                    WHERE a.ApproverEmail = %s
                      AND a.IsCurrent = 1
                      AND a.ApprovalStatusName = 'Pending'
                ),
                PendingCollections = (
                    SELECT COUNT(1)
                    FROM dbo.Requests r
                    WHERE r.StatusName = 'Pending Collection'
                ),
                LowStockItems = (
                    SELECT COUNT(1)
                    FROM dbo.vw_StockBalance sb
                    INNER JOIN dbo.Inventory i
                        ON i.ItemCode = sb.ItemCode
                    WHERE ISNULL(sb.AvailableStock, 0) <= ISNULL(i.ReorderLevel, 0)
                      AND i.IsActive = 1
                ),
                RejectedRequests = (
                    SELECT COUNT(1)
                    FROM dbo.Requests r
                    WHERE r.StatusName IN ('Rejected', 'Cancelled')
                ),
                FullyIssuedToday = (
                    SELECT COUNT(1)
                    FROM dbo.Requests r
                    WHERE r.StatusName IN ('Fully Issued', 'Collected')
                      AND CAST(ISNULL(r.IssueDate, r.CreatedAt) AS date) = CAST(GETDATE() AS date)
                ),
                ActiveInventoryItems = (
                    SELECT COUNT(1)
                    FROM dbo.Inventory i
                    WHERE i.IsActive = 1
                )
            """,
            [user_email, user_email],
        )
        metrics = _fetch_one(cursor)

    with connection.cursor() as cursor:
        if role_name == "Requestor":
            cursor.execute(
                """
                SELECT COUNT(1) AS PartiallyIssued
                FROM dbo.Requests r
                WHERE r.RequestorEmail = %s
                  AND r.StatusName = 'Partially Issued'
                """,
                [user_email],
            )
        else:
            cursor.execute(
                """
                SELECT COUNT(1) AS PartiallyIssued
                FROM dbo.Requests r
                WHERE r.StatusName = 'Partially Issued'
                """
            )

        partial_row = _fetch_one(cursor)

    metrics["PartiallyIssued"] = partial_row.get("PartiallyIssued", 0)
    return metrics


def get_dashboard_cards(role_name: str) -> list[str]:
    role_name = (role_name or "").strip()

    role_cards = {
        "Requestor": ["my_open_requests"],
        "Approver": ["my_pending_approvals"],
        "Authorizer": ["my_pending_approvals"],
        "Stores Controller": ["pending_collections", "low_stock_items"],
    }
    return role_cards.get(role_name, [])


def get_recent_activity(user_email: str, role_name: str, top_n: int = 8) -> list[dict[str, Any]]:
    role_name = (role_name or "").strip()
    user_email = (user_email or "").strip()

    with connection.cursor() as cursor:
        if role_name == "Requestor":
            cursor.execute(
                f"""
                SELECT TOP {top_n}
                    r.RequestNumber,
                    r.RequestDate,
                    r.DepartmentCode,
                    d.Name AS DepartmentName,
                    r.RequestorEmail,
                    r.RequestorEmail AS RequestorName,
                    r.StatusName,
                    r.FarmerName,
                    ISNULL(ri.ItemCount, 0) AS ItemCount
                FROM dbo.Requests r
                LEFT JOIN dbo.Departments d
                    ON d.DepartmentCode = r.DepartmentCode
                LEFT JOIN (
                    SELECT RequestNumber, COUNT(1) AS ItemCount
                    FROM dbo.RequestedItems
                    GROUP BY RequestNumber
                ) ri
                    ON ri.RequestNumber = r.RequestNumber
                WHERE r.RequestorEmail = %s
                ORDER BY r.RequestDate DESC
                """,
                [user_email],
            )
            rows = _fetch_all(cursor)
            if rows:
                return rows

        if role_name in ["Approver", "Authorizer"]:
            cursor.execute(
                f"""
                SELECT TOP {top_n}
                    r.RequestNumber,
                    r.RequestDate,
                    r.DepartmentCode,
                    d.Name AS DepartmentName,
                    r.RequestorEmail,
                    r.RequestorEmail AS RequestorName,
                    r.StatusName,
                    r.FarmerName,
                    ISNULL(ri.ItemCount, 0) AS ItemCount
                FROM dbo.Requests r
                LEFT JOIN dbo.Departments d
                    ON d.DepartmentCode = r.DepartmentCode
                LEFT JOIN (
                    SELECT RequestNumber, COUNT(1) AS ItemCount
                    FROM dbo.RequestedItems
                    GROUP BY RequestNumber
                ) ri
                    ON ri.RequestNumber = r.RequestNumber
                WHERE r.ApproverEmail = %s
                   OR r.AuthorizerEmail = %s
                ORDER BY r.RequestDate DESC
                """,
                [user_email, user_email],
            )
            rows = _fetch_all(cursor)
            if rows:
                return rows

        if role_name == "Stores Controller":
            cursor.execute(
                f"""
                SELECT TOP {top_n}
                    r.RequestNumber,
                    r.RequestDate,
                    r.DepartmentCode,
                    d.Name AS DepartmentName,
                    r.RequestorEmail,
                    r.RequestorEmail AS RequestorName,
                    r.StatusName,
                    r.FarmerName,
                    ISNULL(ri.ItemCount, 0) AS ItemCount
                FROM dbo.Requests r
                LEFT JOIN dbo.Departments d
                    ON d.DepartmentCode = r.DepartmentCode
                LEFT JOIN (
                    SELECT RequestNumber, COUNT(1) AS ItemCount
                    FROM dbo.RequestedItems
                    GROUP BY RequestNumber
                ) ri
                    ON ri.RequestNumber = r.RequestNumber
                WHERE r.StatusName IN (
                    'Pending Collection',
                    'Partially Issued',
                    'Fully Issued',
                    'Collected'
                )
                ORDER BY r.RequestDate DESC
                """
            )
            rows = _fetch_all(cursor)
            if rows:
                return rows

        cursor.execute(
            f"""
            SELECT TOP {top_n}
                r.RequestNumber,
                r.RequestDate,
                r.DepartmentCode,
                d.Name AS DepartmentName,
                r.RequestorEmail,
                r.RequestorEmail AS RequestorName,
                r.StatusName,
                r.FarmerName,
                ISNULL(ri.ItemCount, 0) AS ItemCount
            FROM dbo.Requests r
            LEFT JOIN dbo.Departments d
                ON d.DepartmentCode = r.DepartmentCode
            LEFT JOIN (
                SELECT RequestNumber, COUNT(1) AS ItemCount
                FROM dbo.RequestedItems
                GROUP BY RequestNumber
            ) ri
                ON ri.RequestNumber = r.RequestNumber
            ORDER BY r.RequestDate DESC
            """
        )
        return _fetch_all(cursor)


def get_dashboard_alerts(user_email: str, role_name: str) -> list[dict[str, Any]]:
    role_name = (role_name or "").strip()
    alerts: list[dict[str, Any]] = []

    metrics = get_dashboard_metrics(user_email, role_name)

    my_pending_approvals = int(metrics.get("MyPendingApprovals", 0) or 0)
    pending_collections = int(metrics.get("PendingCollections", 0) or 0)
    low_stock_items = int(metrics.get("LowStockItems", 0) or 0)
    rejected_requests = int(metrics.get("RejectedRequests", 0) or 0)
    partially_issued = int(metrics.get("PartiallyIssued", 0) or 0)

    if role_name in ["Approver", "Authorizer"] and my_pending_approvals > 0:
        alerts.append({
            "level": "warning",
            "title": "Pending approvals",
            "message": f"{my_pending_approvals} waiting for action",
            "url": "/requests/approvals/",
            "url_text": "Open",
        })

    if role_name == "Stores Controller" and pending_collections > 0:
        alerts.append({
            "level": "info",
            "title": "Pending collections",
            "message": f"{pending_collections} ready for collection",
            "url": "/requests/collections/",
            "url_text": "Open",
        })

    if role_name == "Stores Controller" and low_stock_items > 0:
        alerts.append({
            "level": "error",
            "title": "Low stock",
            "message": f"{low_stock_items} at or below reorder level",
            "url": None,
            "url_text": "",
        })

    if partially_issued > 0:
        alerts.append({
            "level": "info",
            "title": "Partially issued",
            "message": f"{partially_issued} still in progress",
            "url": None,
            "url_text": "",
        })

    if rejected_requests > 0:
        alerts.append({
            "level": "warning",
            "title": "Rejected / cancelled",
            "message": f"{rejected_requests} found",
            "url": None,
            "url_text": "",
        })

    if not alerts:
        alerts.append({
            "level": "success",
            "title": "All clear",
            "message": "No urgent items right now",
            "url": None,
            "url_text": "",
        })

    return alerts