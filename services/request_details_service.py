from django.db import connection


def _fetch_all_as_dict(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _fetch_one_as_dict(cursor):
    row = cursor.fetchone()
    if not row:
        return None
    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, row))


def get_request_details(request_number, user_email=None):
    header_sql = """
        SELECT TOP 1
            r.RequestNumber,
            r.RequestDate,
            r.RequiredDate,
            r.RequestorEmail,
            r.DepartmentCode,
            d.Name AS DepartmentName,
            r.StatusName,
            r.AuthorizationRequired,
            r.Justification,
            r.CollectorName,
            r.CollectorNationalID,
            r.TruckRegistration,
            r.TrailerRegistration,
            r.GrowerNumber,
            r.FarmerName,
            r.CreatedAt
        FROM dbo.Requests r
        LEFT JOIN dbo.Departments d
            ON r.DepartmentCode = d.DepartmentCode
        WHERE r.RequestNumber = %s
    """

    lines_sql = """
        SELECT
            ri.LineNumber,
            ri.ItemCode,
            i.Name AS ItemName,
            ri.QuantityRequested,
            ri.QuantityIssued,
            ri.QuantityReserved,
            ri.UOMCode,
            ri.StockStatus,
            ri.LineStatus,
            ISNULL(ret.TotalReturnedQty, 0) AS QuantityReturned,
            CASE
                WHEN ISNULL(ri.QuantityIssued, 0) - ISNULL(ret.TotalReturnedQty, 0) > 0
                    THEN ISNULL(ri.QuantityIssued, 0) - ISNULL(ret.TotalReturnedQty, 0)
                ELSE 0
            END AS NetIssued
        FROM dbo.RequestedItems ri
        LEFT JOIN dbo.Inventory i
            ON ri.ItemCode = i.ItemCode
        LEFT JOIN (
            SELECT
                sl.Reference AS RequestNumber,
                sl.LineNumber,
                sl.ItemCode,
                SUM(ABS(ISNULL(sl.Quantity, 0))) AS TotalReturnedQty
            FROM dbo.StockLedger sl
            WHERE sl.TransactionType = 'RETURN_IN'
            GROUP BY
                sl.Reference,
                sl.LineNumber,
                sl.ItemCode
        ) ret
            ON ri.RequestNumber = ret.RequestNumber
           AND ri.LineNumber = ret.LineNumber
           AND ri.ItemCode = ret.ItemCode
        WHERE ri.RequestNumber = %s
        ORDER BY ri.LineNumber
    """

    approvals_sql = """
        SELECT
            ApprovalLevel,
            ApproverEmail,
            ApprovalStatusName,
            ApprovalRole,
            IsCurrent,
            CreatedDate
        FROM dbo.Approvals
        WHERE RequestNumber = %s
        ORDER BY ApprovalLevel, ApproverEmail
    """

    collections_sql = """
        SELECT
            c.CollectionNumber,
            c.CollectionDate,
            c.RequestNumber,
            c.Farmer,
            c.RequestedBy,
            c.DisbursedBy,
            c.DriverName,
            c.DriverID,
            c.TruckRegistration,
            c.TrailerRegistration,
            c.VoucherStatus,
            c.VoucherPath,
            c.DjangoVoucherPath,
            ISNULL(SUM(ci.ThisIssueQty), 0) AS TotalIssueQty,
            COUNT(ci.ID) AS TotalLines
        FROM dbo.Collections c
        LEFT JOIN dbo.CollectionItems ci
            ON c.CollectionNumber = ci.CollectionNumber
        WHERE c.RequestNumber = %s
        GROUP BY
            c.CollectionNumber,
            c.CollectionDate,
            c.RequestNumber,
            c.Farmer,
            c.RequestedBy,
            c.DisbursedBy,
            c.DriverName,
            c.DriverID,
            c.TruckRegistration,
            c.TrailerRegistration,
            c.VoucherStatus,
            c.VoucherPath,
            c.DjangoVoucherPath
        ORDER BY c.CollectionDate DESC, c.CollectionNumber DESC
    """

    returns_history_sql = """
        SELECT
            sl.TransactionDate AS ReturnDate,
            sl.Reference AS RequestNumber,
            sl.LineNumber,
            sl.ItemCode,
            i.Name AS ItemName,
            ABS(ISNULL(sl.Quantity, 0)) AS ReturnedQty,
            sl.PerformedByEmail AS ReturnedBy,
            sl.Notes,
            sl.TransactionType,
            CASE
                WHEN CHARINDEX('Collection ', ISNULL(sl.Notes, '')) > 0
                    THEN LTRIM(RTRIM(
                        SUBSTRING(
                            sl.Notes,
                            CHARINDEX('Collection ', sl.Notes) + 11,
                            50
                        )
                    ))
                ELSE NULL
            END AS ReturnReference
        FROM dbo.StockLedger sl
        LEFT JOIN dbo.Inventory i
            ON sl.ItemCode = i.ItemCode
        WHERE sl.Reference = %s
          AND sl.TransactionType = 'RETURN_IN'
        ORDER BY sl.TransactionDate DESC, sl.LineNumber
    """

    with connection.cursor() as cursor:
        cursor.execute(header_sql, [request_number])
        header = _fetch_one_as_dict(cursor)

        if not header:
            return None

        cursor.execute(lines_sql, [request_number])
        lines = _fetch_all_as_dict(cursor)

        cursor.execute(approvals_sql, [request_number])
        approvals = _fetch_all_as_dict(cursor)

        cursor.execute(collections_sql, [request_number])
        collections = _fetch_all_as_dict(cursor)

        cursor.execute(returns_history_sql, [request_number])
        returns_history = _fetch_all_as_dict(cursor)

    return {
        "header": header,
        "lines": lines,
        "approvals": approvals,
        "collections": collections,
        "returns_history": returns_history,
    }