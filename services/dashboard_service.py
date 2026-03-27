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
                )
            """,
            [user_email, user_email],
        )
        return _fetch_one(cursor)


def get_dashboard_cards(role_name: str) -> list[str]:
    role_cards = {
        "Requestor": [
            "my_open_requests",
        ],
        "Approver": [
            "my_pending_approvals",
        ],
        "Authorizer": [
            "my_pending_approvals",
        ],
        "Stores Controller": [
            "pending_collections",
            "low_stock_items",
        ],
    }
    return role_cards.get(role_name, [])


def get_recent_activity(user_email: str, role_name: str, top_n: int = 8) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
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
                WHERE EXISTS (
                    SELECT 1
                    FROM dbo.Approvals a
                    WHERE a.RequestNumber = r.RequestNumber
                      AND a.ApproverEmail = %s
                )
                ORDER BY r.RequestDate DESC
                """,
                [user_email],
            )

        elif role_name == "Stores Controller":
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
                WHERE r.StatusName IN ('Pending Collection', 'Partially Issued', 'Fully Issued')
                ORDER BY r.RequestDate DESC
                """
            )

        else:
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

        return _fetch_all(cursor)