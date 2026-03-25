from django.db import connection

def _fetch_all_as_dict(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def get_reversal_reports(item_code=None, reference=None, date_from=None, date_to=None):
    sql = """
    SELECT
        TransactionDate,
        ItemCode,
        Reference,
        LineNumber,
        Quantity,
        Direction,
        TransactionType,
        CASE
            WHEN TransactionType = 'RETURN_IN' THEN 'Stock Return'
            WHEN TransactionType = 'RESERVATION_RELEASE_REJECT' THEN 'Reservation Release (Rejected)'
            WHEN TransactionType = 'RESERVATION_RELEASE_CANCEL' THEN 'Reservation Release (Cancelled)'
            WHEN TransactionType = 'RESERVATION_REVERSAL' THEN 'Reservation Reversal'
            ELSE TransactionType
        END AS TransactionTypeDisplay,
        ResponsibleDepartment,
        PerformedByEmail,
        Notes
    FROM dbo.StockLedger
    WHERE TransactionType IN (
        'RETURN_IN',
        'RESERVATION_RELEASE_REJECT',
        'RESERVATION_RELEASE_CANCEL',
        'RESERVATION_REVERSAL'
    )
    """
    params = []
    if item_code:
        sql += " AND ItemCode LIKE %s"
        params.append(f"%{item_code}%")
    if reference:
        sql += " AND Reference LIKE %s"
        params.append(f"%{reference}%")
    if date_from:
        sql += " AND CAST(TransactionDate AS DATE) >= %s"
        params.append(date_from)
    if date_to:
        sql += " AND CAST(TransactionDate AS DATE) <= %s"
        params.append(date_to)
    sql += " ORDER BY TransactionDate DESC, Reference DESC, LineNumber ASC"
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return _fetch_all_as_dict(cursor)
