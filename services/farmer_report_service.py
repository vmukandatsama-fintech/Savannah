from django.db import connection


def _fetch_all_as_dict(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def get_farmer_reports(grower_number=None, farmer_name=None, department_code=None, date_from=None, date_to=None):
    sql = """
    SELECT
        GrowerNumber,
        FarmerName,
    SUM(ISNULL(QuantityRequested, 0)) AS TotalRequested,
    SUM(ISNULL(QuantityIssued, 0)) AS TotalIssued,
    SUM(ISNULL(QuantityReserved, 0)) AS TotalReserved,
    SUM(ISNULL(BalanceRemaining, 0)) AS BalanceRemaining,
    COUNT(DISTINCT RequestNumber) AS RequestCount,
    MAX(TransactionDate) AS LastTransactionDate
    FROM dbo.vw_FarmerAccountStatement
    WHERE 1 = 1
    """
    params = []

    if grower_number:
        sql += " AND GrowerNumber LIKE %s"
        params.append(f"%{grower_number}%")

    if farmer_name:
        sql += " AND FarmerName LIKE %s"
        params.append(f"%{farmer_name}%")

    if department_code:
        sql += " AND DepartmentCode = %s"
        params.append(department_code)

    if date_from:
        sql += " AND CAST(TransactionDate AS DATE) >= %s"
        params.append(date_from)

    if date_to:
        sql += " AND CAST(TransactionDate AS DATE) <= %s"
        params.append(date_to)

    sql += """
    GROUP BY GrowerNumber, FarmerName
    ORDER BY FarmerName, GrowerNumber
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return _fetch_all_as_dict(cursor)

def get_farmer_account_statement(grower_number, date_from=None, date_to=None):
    sql = """
    SELECT
        TransactionDate,
        RequestNumber,
    RequestedBy,
    DepartmentCode,
    DepartmentName,
    GrowerNumber,
    FarmerName,
    LineNumber,
    ItemCode,
    ItemName,
    UOMCode,
    UOMName,
    QuantityRequested,
    QuantityIssued,
    QuantityReserved,
    BalanceRemaining,
    StatusName,
        StockStatus
    FROM dbo.vw_FarmerAccountStatement
    WHERE GrowerNumber = %s
    """
    params = [grower_number]

    if date_from:
        sql += " AND CAST(TransactionDate AS DATE) >= %s"
        params.append(date_from)

    if date_to:
        sql += " AND CAST(TransactionDate AS DATE) <= %s"
        params.append(date_to)

    sql += " ORDER BY TransactionDate DESC, RequestNumber DESC, LineNumber ASC"

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return _fetch_all_as_dict(cursor)

def get_farmer_collection_statement(grower_number, date_from=None, date_to=None):
    sql = """
    SELECT
        TransactionDate,
        CollectionNumber,
    RequestNumber,
    RequestedBy,
    DepartmentCode,
    DepartmentName,
    GrowerNumber,
    FarmerName,
    LineNumber,
    ItemCode,
    ItemName,
    UOM,
    QuantityRequested,
    ThisIssueQty,
    TotalIssuedToDate,
    RemainingAfterIssue,
    StatusName
    FROM dbo.vw_FarmerCollectionStatement
    WHERE GrowerNumber = %s
    """
    params = [grower_number]

    if date_from:
        sql += " AND CAST(TransactionDate AS DATE) >= %s"
        params.append(date_from)

    if date_to:
        sql += " AND CAST(TransactionDate AS DATE) <= %s"
        params.append(date_to)

    sql += " ORDER BY TransactionDate DESC, CollectionNumber DESC, LineNumber ASC"

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return _fetch_all_as_dict(cursor)

def get_farmer_summary(grower_number, date_from=None, date_to=None):
    sql = """
    SELECT TOP 1
        GrowerNumber,
        FarmerName
    FROM dbo.vw_FarmerAccountStatement
    WHERE GrowerNumber = %s
    """
    params = [grower_number]

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = _fetch_all_as_dict(cursor)
        identity = rows[0] if rows else {"GrowerNumber": grower_number, "FarmerName": ""}

    summary_sql = """
    SELECT
        SUM(ISNULL(QuantityRequested, 0)) AS TotalRequested,
    SUM(ISNULL(QuantityIssued, 0)) AS TotalIssued,
    SUM(ISNULL(QuantityReserved, 0)) AS TotalReserved,
    SUM(ISNULL(BalanceRemaining, 0)) AS BalanceRemaining,
        COUNT(DISTINCT RequestNumber) AS RequestCount,
        MAX(TransactionDate) AS LastTransactionDate
    FROM dbo.vw_FarmerAccountStatement
    WHERE GrowerNumber = %s
    """
    summary_params = [grower_number]

    if date_from:
        summary_sql += " AND CAST(TransactionDate AS DATE) >= %s"
        summary_params.append(date_from)

    if date_to:
        summary_sql += " AND CAST(TransactionDate AS DATE) <= %s"
        summary_params.append(date_to)

    with connection.cursor() as cursor:
        cursor.execute(summary_sql, summary_params)
        rows = _fetch_all_as_dict(cursor)
        totals = rows[0] if rows else {}

    result = {}
    result.update(identity)
    result.update(totals or {})
    return result


def get_farmer_departments():
    sql = """
    SELECT DISTINCT
        DepartmentCode,
        DepartmentName
    FROM dbo.vw_FarmerAccountStatement
    WHERE DepartmentCode IS NOT NULL
    ORDER BY DepartmentName
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return _fetch_all_as_dict(cursor)
from django.db import connection


def _fetch_all_as_dict(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_farmer_reports(grower_number=None, farmer_name=None, department_code=None, date_from=None, date_to=None):
    sql = """
    SELECT
        GrowerNumber,
        FarmerName,
        SUM(ISNULL(QuantityRequested, 0)) AS TotalRequested,
        SUM(ISNULL(QuantityIssued, 0)) AS TotalIssued,
        SUM(ISNULL(QuantityReserved, 0)) AS TotalReserved,
        SUM(ISNULL(BalanceRemaining, 0)) AS BalanceRemaining,
        COUNT(DISTINCT RequestNumber) AS RequestCount,
        MAX(TransactionDate) AS LastTransactionDate
    FROM dbo.vw_FarmerAccountStatement
    WHERE 1 = 1
    """
    params = []

    if grower_number:
        sql += " AND GrowerNumber LIKE %s"
        params.append(f"%{grower_number}%")

    if farmer_name:
        sql += " AND FarmerName LIKE %s"
        params.append(f"%{farmer_name}%")

    if department_code:
        sql += " AND DepartmentCode = %s"
        params.append(department_code)

    if date_from:
        sql += " AND CAST(TransactionDate AS DATE) >= %s"
        params.append(date_from)

    if date_to:
        sql += " AND CAST(TransactionDate AS DATE) <= %s"
        params.append(date_to)

    sql += """
    GROUP BY GrowerNumber, FarmerName
    ORDER BY FarmerName, GrowerNumber
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return _fetch_all_as_dict(cursor)


def get_farmer_account_statement(grower_number, date_from=None, date_to=None):
    sql = """
    SELECT
        TransactionDate,
        RequestNumber,
        RequestedBy,
        DepartmentCode,
        DepartmentName,
        GrowerNumber,
        FarmerName,
        LineNumber,
        ItemCode,
        ItemName,
        UOMCode,
        UOMName,
        QuantityRequested,
        QuantityIssued,
        QuantityReserved,
        BalanceRemaining,
        StatusName,
        StockStatus
    FROM dbo.vw_FarmerAccountStatement
    WHERE GrowerNumber = %s
    """
    params = [grower_number]

    if date_from:
        sql += " AND CAST(TransactionDate AS DATE) >= %s"
        params.append(date_from)

    if date_to:
        sql += " AND CAST(TransactionDate AS DATE) <= %s"
        params.append(date_to)

    sql += " ORDER BY TransactionDate DESC, RequestNumber DESC, LineNumber ASC"

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return _fetch_all_as_dict(cursor)


def get_farmer_collection_statement(grower_number, date_from=None, date_to=None):
    sql = """
    SELECT
        TransactionDate,
        CollectionNumber,
        RequestNumber,
        RequestedBy,
        DepartmentCode,
        DepartmentName,
        GrowerNumber,
        FarmerName,
        LineNumber,
        ItemCode,
        ItemName,
        UOM,
        QuantityRequested,
        ThisIssueQty,
        TotalIssuedToDate,
        RemainingAfterIssue,
        StatusName
    FROM dbo.vw_FarmerCollectionStatement
    WHERE GrowerNumber = %s
    """
    params = [grower_number]

    if date_from:
        sql += " AND CAST(TransactionDate AS DATE) >= %s"
        params.append(date_from)

    if date_to:
        sql += " AND CAST(TransactionDate AS DATE) <= %s"
        params.append(date_to)

    sql += " ORDER BY TransactionDate DESC, CollectionNumber DESC, LineNumber ASC"

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return _fetch_all_as_dict(cursor)


def get_farmer_summary(grower_number, date_from=None, date_to=None):
    sql = """
    SELECT
        TOP 1
        GrowerNumber,
        FarmerName
    FROM dbo.vw_FarmerAccountStatement
    WHERE GrowerNumber = %s
    """
    params = [grower_number]

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = _fetch_all_as_dict(cursor)
        identity = rows[0] if rows else {"GrowerNumber": grower_number, "FarmerName": ""}

    summary_sql = """
    SELECT
        SUM(ISNULL(QuantityRequested, 0)) AS TotalRequested,
        SUM(ISNULL(QuantityIssued, 0)) AS TotalIssued,
        SUM(ISNULL(QuantityReserved, 0)) AS TotalReserved,
        SUM(ISNULL(BalanceRemaining, 0)) AS BalanceRemaining,
        COUNT(DISTINCT RequestNumber) AS RequestCount,
        MAX(TransactionDate) AS LastTransactionDate
    FROM dbo.vw_FarmerAccountStatement
    WHERE GrowerNumber = %s
    """
    summary_params = [grower_number]

    if date_from:
        summary_sql += " AND CAST(TransactionDate AS DATE) >= %s"
        summary_params.append(date_from)

    if date_to:
        summary_sql += " AND CAST(TransactionDate AS DATE) <= %s"
        summary_params.append(date_to)

    with connection.cursor() as cursor:
        cursor.execute(summary_sql, summary_params)
        rows = _fetch_all_as_dict(cursor)
        totals = rows[0] if rows else {}

    result = {}
    result.update(identity)
    result.update(totals or {})
    return result


def get_farmer_departments():
    sql = """
    SELECT DISTINCT
        DepartmentCode,
        DepartmentName
    FROM dbo.vw_FarmerAccountStatement
    WHERE DepartmentCode IS NOT NULL
    ORDER BY DepartmentName
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return _fetch_all_as_dict(cursor)
