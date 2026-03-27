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


def get_approval_inbox(
    approver_email: str | None = None,
    mode: str = "Pending",
    show_all: bool = False,
) -> list[dict[str, Any]]:
    mode = (mode or "Pending").strip()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            EXEC dbo.sp_GetApprovalInbox
                @ApproverEmail=%s,
                @Mode=%s,
                @ShowAll=%s
            """,
            [approver_email, mode, 1 if show_all else 0],
        )
        return _fetch_first_resultset_as_dicts(cursor)


def get_approval_history(request_number: str) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            "EXEC dbo.sp_GetApprovalHistory @RequestNumber=%s",
            [request_number],
        )
        return _fetch_first_resultset_as_dicts(cursor)


def process_approval(
    request_number: str,
    approver_email: str,
    decision: str,
    comments: str = "",
) -> None:
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