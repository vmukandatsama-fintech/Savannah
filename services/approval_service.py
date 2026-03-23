from typing import Any
from django.db import connection


def _fetch_first_resultset_as_dicts(cursor) -> list[dict[str, Any]]:
    while True:
        if cursor.description is not None:
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]

        if not cursor.nextset():
            break

    return []


def get_approval_inbox(approver_email: str, mode: str = "Pending") -> list[dict[str, Any]]:
    print("GET_APPROVAL_INBOX EMAIL:", repr(approver_email))
    print("GET_APPROVAL_INBOX MODE:", repr(mode))

    with connection.cursor() as cursor:
        cursor.execute(
            "EXEC dbo.sp_GetApprovalInbox @ApproverEmail=%s, @Mode=%s",
            [approver_email, mode],
        )
        rows = _fetch_first_resultset_as_dicts(cursor)

    print("GET_APPROVAL_INBOX ROW COUNT:", len(rows))
    if rows:
        print("GET_APPROVAL_INBOX FIRST ROW:", rows[0])

    return rows


def get_approval_history(request_number: str) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            "EXEC dbo.sp_GetApprovalHistory @RequestNumber=%s",
            [request_number],
        )
        return _fetch_first_resultset_as_dicts(cursor)


def process_approval(request_number: str, approver_email: str, decision: str, comments: str = ""):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            EXEC dbo.sp_ProcessApproval
                @RequestNumber=%s,
                @ApproverEmail=%s,
                @Decision=%s,
                @Comments=%s
            """,
            [request_number, approver_email, decision, comments],
        )