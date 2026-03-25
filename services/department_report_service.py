from django.db import connection


def _fetch_all_as_dict(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_department_list():
    sql = """
    SELECT DISTINCT
        d.DepartmentCode,
        d.Name AS DepartmentName
    FROM dbo.Departments d
    ORDER BY d.Name, d.DepartmentCode
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return _fetch_all_as_dict(cursor)


def get_department_consumption_summary(department_code=None, date_from=None, date_to=None):
    sql = """
    SELECT
        r.DepartmentCode,
        d.Name AS DepartmentName,
        COUNT(DISTINCT r.RequestNumber) AS RequestCount,
        COUNT(DISTINCT c.CollectionNumber) AS CollectionCount,
        COUNT(DISTINCT r.GrowerNumber) AS FarmerCount,
        ISNULL(SUM(ci.ThisIssueQty), 0) AS TotalIssuedQty,
        MAX(c.CollectionDate) AS LastIssueDate
    FROM dbo.Requests r
    LEFT JOIN dbo.Collections c
        ON r.RequestNumber = c.RequestNumber
    LEFT JOIN dbo.CollectionItems ci
        ON c.CollectionNumber = ci.CollectionNumber
    LEFT JOIN dbo.Departments d
        ON r.DepartmentCode = d.DepartmentCode
    WHERE 1 = 1
    """
    params = []

    if department_code:
        sql += " AND r.DepartmentCode = %s"
        params.append(department_code)

    if date_from:
        sql += " AND CAST(ISNULL(c.CollectionDate, r.RequestDate) AS DATE) >= %s"
        params.append(date_from)

    if date_to:
        sql += " AND CAST(ISNULL(c.CollectionDate, r.RequestDate) AS DATE) <= %s"
        params.append(date_to)

    sql += """
    GROUP BY
        r.DepartmentCode,
        d.Name
    ORDER BY
        d.Name,
        r.DepartmentCode
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return _fetch_all_as_dict(cursor)


def get_department_consumption_detail(department_code, date_from=None, date_to=None):
    sql = """
    SELECT
        r.DepartmentCode,
        d.Name AS DepartmentName,
        ci.ItemCode,
        ci.ItemName,
        ci.UOM,
        COUNT(DISTINCT r.RequestNumber) AS RequestCount,
        COUNT(DISTINCT c.CollectionNumber) AS CollectionCount,
        COUNT(DISTINCT r.GrowerNumber) AS FarmerCount,
        ISNULL(SUM(ci.ThisIssueQty), 0) AS TotalIssuedQty,
        MAX(c.CollectionDate) AS LastIssueDate
    FROM dbo.Requests r
    INNER JOIN dbo.Collections c
        ON r.RequestNumber = c.RequestNumber
    INNER JOIN dbo.CollectionItems ci
        ON c.CollectionNumber = ci.CollectionNumber
    LEFT JOIN dbo.Departments d
        ON r.DepartmentCode = d.DepartmentCode
    WHERE r.DepartmentCode = %s
    """
    params = [department_code]

    if date_from:
        sql += " AND CAST(c.CollectionDate AS DATE) >= %s"
        params.append(date_from)

    if date_to:
        sql += " AND CAST(c.CollectionDate AS DATE) <= %s"
        params.append(date_to)

    sql += """
    GROUP BY
        r.DepartmentCode,
        d.Name,
        ci.ItemCode,
        ci.ItemName,
        ci.UOM
    ORDER BY
        ci.ItemName,
        ci.ItemCode
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return _fetch_all_as_dict(cursor)


def get_department_summary_card(department_code, date_from=None, date_to=None):
    sql = """
    SELECT TOP 1
        r.DepartmentCode,
        d.Name AS DepartmentName,
        COUNT(DISTINCT r.RequestNumber) AS RequestCount,
        COUNT(DISTINCT c.CollectionNumber) AS CollectionCount,
        COUNT(DISTINCT r.GrowerNumber) AS FarmerCount,
        ISNULL(SUM(ci.ThisIssueQty), 0) AS TotalIssuedQty,
        MAX(c.CollectionDate) AS LastIssueDate
    FROM dbo.Requests r
    LEFT JOIN dbo.Collections c
        ON r.RequestNumber = c.RequestNumber
    LEFT JOIN dbo.CollectionItems ci
        ON c.CollectionNumber = ci.CollectionNumber
    LEFT JOIN dbo.Departments d
        ON r.DepartmentCode = d.DepartmentCode
    WHERE r.DepartmentCode = %s
    """
    params = [department_code]

    if date_from:
        sql += " AND CAST(ISNULL(c.CollectionDate, r.RequestDate) AS DATE) >= %s"
        params.append(date_from)

    if date_to:
        sql += " AND CAST(ISNULL(c.CollectionDate, r.RequestDate) <= %s"
        params.append(date_to)

    sql += """
    GROUP BY
        r.DepartmentCode,
        d.Name
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = _fetch_all_as_dict(cursor)
        return rows[0] if rows else None


def get_department_trends(department_code=None, date_from=None, date_to=None):
    sql = """
    SELECT
        CONVERT(VARCHAR(7), c.CollectionDate, 120) AS PeriodMonth,
        r.DepartmentCode,
        d.Name AS DepartmentName,
        COUNT(DISTINCT c.CollectionNumber) AS CollectionCount,
        COUNT(DISTINCT r.RequestNumber) AS RequestCount,
        ISNULL(SUM(ci.ThisIssueQty), 0) AS TotalIssuedQty
    FROM dbo.Requests r
    INNER JOIN dbo.Collections c
        ON r.RequestNumber = c.RequestNumber
    INNER JOIN dbo.CollectionItems ci
        ON c.CollectionNumber = ci.CollectionNumber
    LEFT JOIN dbo.Departments d
        ON r.DepartmentCode = d.DepartmentCode
    WHERE 1 = 1
    """
    params = []

    if department_code:
        sql += " AND r.DepartmentCode = %s"
        params.append(department_code)

    if date_from:
        sql += " AND CAST(c.CollectionDate AS DATE) >= %s"
        params.append(date_from)

    if date_to:
        sql += " AND CAST(c.CollectionDate AS DATE) <= %s"
        params.append(date_to)

    sql += """
    GROUP BY
        CONVERT(VARCHAR(7), c.CollectionDate, 120),
        r.DepartmentCode,
        d.Name
    ORDER BY
        PeriodMonth DESC,
        d.Name,
        r.DepartmentCode
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return _fetch_all_as_dict(cursor)
