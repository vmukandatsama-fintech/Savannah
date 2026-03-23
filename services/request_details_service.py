from django.db import connection


def get_request_details(request_number, user_email):
    header_sql = """
        SELECT TOP 1
            r.RequestNumber,
            r.RequestDate,
            r.RequiredDate,
            r.RequestorEmail,
            r.DepartmentCode,
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
        WHERE r.RequestNumber = %s
          AND (
                r.RequestorEmail = %s
                OR EXISTS (
                    SELECT 1
                    FROM dbo.Approvals a
                    WHERE a.RequestNumber = r.RequestNumber
                      AND a.ApproverEmail = %s
                )
              )
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
            ri.LineStatus
        FROM dbo.RequestedItems ri
        LEFT JOIN dbo.Inventory i
            ON ri.ItemCode = i.ItemCode
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

    with connection.cursor() as cursor:
        cursor.execute(header_sql, [request_number, user_email, user_email])
        header_row = cursor.fetchone()

        if not header_row:
            return None

        header_columns = [col[0] for col in cursor.description]
        header = dict(zip(header_columns, header_row))

        cursor.execute(lines_sql, [request_number])
        line_rows = cursor.fetchall()
        line_columns = [col[0] for col in cursor.description]
        lines = [dict(zip(line_columns, row)) for row in line_rows]

        cursor.execute(approvals_sql, [request_number])
        approval_rows = cursor.fetchall()
        approval_columns = [col[0] for col in cursor.description]
        approvals = [dict(zip(approval_columns, row)) for row in approval_rows]

    return {
        "header": header,
        "lines": lines,
        "approvals": approvals,
    }