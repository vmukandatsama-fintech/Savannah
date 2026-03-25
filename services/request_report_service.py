from django.db import connection


def _fetch_all_as_dict(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_request_tracker(
    request_number=None,
    status_name=None,
    department_code=None,
    grower_number=None,
    date_from=None,
    date_to=None,
):
    sql = """
    SELECT
        r.RequestNumber,
        r.RequestDate,
        r.RequiredDate,
        r.RequestorEmail AS RequestedBy,
        r.DepartmentCode,
        d.Name AS DepartmentName,
        r.GrowerNumber,
        r.FarmerName,
        r.StatusName,
        ISNULL(SUM(ri.QuantityRequested), 0) AS TotalRequested,
        ISNULL(SUM(ri.QuantityIssued), 0) AS TotalIssued,
        ISNULL(SUM(ri.QuantityReserved), 0) AS TotalReserved,
        ISNULL(SUM(
            CASE
                WHEN ISNULL(ri.QuantityRequested, 0) - ISNULL(ri.QuantityIssued, 0) > 0
                    THEN ISNULL(ri.QuantityRequested, 0) - ISNULL(ri.QuantityIssued, 0)
                ELSE 0
            END
        ), 0) AS BalanceRemaining,
        DATEDIFF(DAY, CAST(r.RequestDate AS DATE), CAST(GETDATE() AS DATE)) AS AgeDays
    FROM dbo.Requests r
    LEFT JOIN dbo.RequestedItems ri
        ON r.RequestNumber = ri.RequestNumber
    LEFT JOIN dbo.Departments d
        ON r.DepartmentCode = d.DepartmentCode
    WHERE 1 = 1
    """
    params = []

    if request_number:
        sql += " AND r.RequestNumber LIKE %s"
        params.append(f"%{request_number}%")

    if status_name:
        sql += " AND r.StatusName = %s"
        params.append(status_name)

    if department_code:
        sql += " AND r.DepartmentCode = %s"
        params.append(department_code)

    if grower_number:
        sql += " AND r.GrowerNumber LIKE %s"
        params.append(f"%{grower_number}%")

    if date_from:
        sql += " AND CAST(r.RequestDate AS DATE) >= %s"
        params.append(date_from)

    if date_to:
        sql += " AND CAST(r.RequestDate AS DATE) <= %s"
        params.append(date_to)

    sql += """
    GROUP BY
        r.RequestNumber,
        r.RequestDate,
        r.RequiredDate,
        r.RequestorEmail,
        r.DepartmentCode,
        d.Name,
        r.GrowerNumber,
        r.FarmerName,
        r.StatusName
    ORDER BY r.RequestDate DESC, r.RequestNumber DESC
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return _fetch_all_as_dict(cursor)


def get_request_statuses():
    sql = """
    SELECT DISTINCT StatusName
    FROM dbo.Requests
    WHERE StatusName IS NOT NULL
    ORDER BY StatusName
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return _fetch_all_as_dict(cursor)


def get_request_departments():
    sql = """
    SELECT DISTINCT
        d.DepartmentCode,
        d.Name AS DepartmentName
    FROM dbo.Requests r
    LEFT JOIN dbo.Departments d
        ON r.DepartmentCode = d.DepartmentCode
    WHERE r.DepartmentCode IS NOT NULL
    ORDER BY d.Name, d.DepartmentCode
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return _fetch_all_as_dict(cursor)


def get_request_exception_summary(age_days=3):
    sql = """
    SELECT
        SUM(CASE WHEN r.StatusName = 'Pending Approval' AND DATEDIFF(DAY, CAST(r.RequestDate AS DATE), CAST(GETDATE() AS DATE)) > %s THEN 1 ELSE 0 END) AS PendingApprovalOverdue,
        SUM(CASE WHEN r.StatusName = 'Pending Authorization' AND DATEDIFF(DAY, CAST(r.RequestDate AS DATE), CAST(GETDATE() AS DATE)) > %s THEN 1 ELSE 0 END) AS PendingAuthorizationOverdue,
        SUM(CASE WHEN r.StatusName = 'Pending Collection' AND DATEDIFF(DAY, CAST(r.RequestDate AS DATE), CAST(GETDATE() AS DATE)) > %s THEN 1 ELSE 0 END) AS PendingCollectionOverdue,
        SUM(CASE WHEN r.StatusName = 'Partially Issued' AND DATEDIFF(DAY, CAST(r.RequestDate AS DATE), CAST(GETDATE() AS DATE)) > %s THEN 1 ELSE 0 END) AS PartiallyIssuedOverdue,
        SUM(CASE WHEN r.StatusName = 'Rejected' THEN 1 ELSE 0 END) AS RejectedRequests,
        SUM(CASE WHEN c.VoucherStatus = 'Error' THEN 1 ELSE 0 END) AS VoucherErrors,
        SUM(CASE WHEN c.VoucherStatus = 'Pending' THEN 1 ELSE 0 END) AS VoucherPending
    FROM dbo.Requests r
    LEFT JOIN (
        SELECT
            RequestNumber,
            MAX(VoucherStatus) AS VoucherStatus
        FROM dbo.Collections
        GROUP BY RequestNumber
    ) c
        ON r.RequestNumber = c.RequestNumber
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [age_days, age_days, age_days, age_days])
        rows = _fetch_all_as_dict(cursor)
        return rows[0] if rows else {}


def get_request_exceptions(age_days=3):
    sql = """
    SELECT
        'Pending Approval Overdue' AS ExceptionType,
        r.RequestNumber,
        r.RequestDate,
        r.RequiredDate,
        r.RequestorEmail AS RequestedBy,
        r.DepartmentCode,
        d.Name AS DepartmentName,
        r.GrowerNumber,
        r.FarmerName,
        r.StatusName,
        DATEDIFF(DAY, CAST(r.RequestDate AS DATE), CAST(GETDATE() AS DATE)) AS AgeDays,
        NULL AS VoucherStatus,
        NULL AS VoucherPath,
        NULL AS VoucherError
    FROM dbo.Requests r
    LEFT JOIN dbo.Departments d
        ON r.DepartmentCode = d.DepartmentCode
    WHERE r.StatusName = 'Pending Approval'
      AND DATEDIFF(DAY, CAST(r.RequestDate AS DATE), CAST(GETDATE() AS DATE)) > %s

    UNION ALL

    SELECT
        'Pending Authorization Overdue' AS ExceptionType,
        r.RequestNumber,
        r.RequestDate,
        r.RequiredDate,
        r.RequestorEmail AS RequestedBy,
        r.DepartmentCode,
        d.Name AS DepartmentName,
        r.GrowerNumber,
        r.FarmerName,
        r.StatusName,
        DATEDIFF(DAY, CAST(r.RequestDate AS DATE), CAST(GETDATE() AS DATE)) AS AgeDays,
        NULL AS VoucherStatus,
        NULL AS VoucherPath,
        NULL AS VoucherError
    FROM dbo.Requests r
    LEFT JOIN dbo.Departments d
        ON r.DepartmentCode = d.DepartmentCode
    WHERE r.StatusName = 'Pending Authorization'
      AND DATEDIFF(DAY, CAST(r.RequestDate AS DATE), CAST(GETDATE() AS DATE)) > %s

    UNION ALL

    SELECT
        'Pending Collection Overdue' AS ExceptionType,
        r.RequestNumber,
        r.RequestDate,
        r.RequiredDate,
        r.RequestorEmail AS RequestedBy,
        r.DepartmentCode,
        d.Name AS DepartmentName,
        r.GrowerNumber,
        r.FarmerName,
        r.StatusName,
        DATEDIFF(DAY, CAST(r.RequestDate AS DATE), CAST(GETDATE() AS DATE)) AS AgeDays,
        NULL AS VoucherStatus,
        NULL AS VoucherPath,
        NULL AS VoucherError
    FROM dbo.Requests r
    LEFT JOIN dbo.Departments d
        ON r.DepartmentCode = d.DepartmentCode
    WHERE r.StatusName = 'Pending Collection'
      AND DATEDIFF(DAY, CAST(r.RequestDate AS DATE), CAST(GETDATE() AS DATE)) > %s

    UNION ALL

    SELECT
        'Partially Issued Overdue' AS ExceptionType,
        r.RequestNumber,
        r.RequestDate,
        r.RequiredDate,
        r.RequestorEmail AS RequestedBy,
        r.DepartmentCode,
        d.Name AS DepartmentName,
        r.GrowerNumber,
        r.FarmerName,
        r.StatusName,
        DATEDIFF(DAY, CAST(r.RequestDate AS DATE), CAST(GETDATE() AS DATE)) AS AgeDays,
        NULL AS VoucherStatus,
        NULL AS VoucherPath,
        NULL AS VoucherError
    FROM dbo.Requests r
    LEFT JOIN dbo.Departments d
        ON r.DepartmentCode = d.DepartmentCode
    WHERE r.StatusName = 'Partially Issued'
      AND DATEDIFF(DAY, CAST(r.RequestDate AS DATE), CAST(GETDATE() AS DATE)) > %s

    UNION ALL

    SELECT
        'Voucher Error' AS ExceptionType,
        c.RequestNumber,
        r.RequestDate,
        r.RequiredDate,
        r.RequestorEmail AS RequestedBy,
        r.DepartmentCode,
        d.Name AS DepartmentName,
        r.GrowerNumber,
        r.FarmerName,
        r.StatusName,
        DATEDIFF(DAY, CAST(r.RequestDate AS DATE), CAST(GETDATE() AS DATE)) AS AgeDays,
        c.VoucherStatus,
        c.VoucherPath,
        c.VoucherError
    FROM dbo.Collections c
    INNER JOIN dbo.Requests r
        ON c.RequestNumber = r.RequestNumber
    LEFT JOIN dbo.Departments d
        ON r.DepartmentCode = d.DepartmentCode
    WHERE c.VoucherStatus = 'Error'

    UNION ALL

    SELECT
        'Voucher Pending' AS ExceptionType,
        c.RequestNumber,
        r.RequestDate,
        r.RequiredDate,
        r.RequestorEmail AS RequestedBy,
        r.DepartmentCode,
        d.Name AS DepartmentName,
        r.GrowerNumber,
        r.FarmerName,
        r.StatusName,
        DATEDIFF(DAY, CAST(r.RequestDate AS DATE), CAST(GETDATE() AS DATE)) AS AgeDays,
        c.VoucherStatus,
        c.VoucherPath,
        c.VoucherError
    FROM dbo.Collections c
    INNER JOIN dbo.Requests r
        ON c.RequestNumber = r.RequestNumber
    LEFT JOIN dbo.Departments d
        ON r.DepartmentCode = d.DepartmentCode
    WHERE c.VoucherStatus = 'Pending'

    ORDER BY AgeDays DESC, RequestDate DESC, RequestNumber DESC
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [age_days, age_days, age_days, age_days])
        return _fetch_all_as_dict(cursor)
