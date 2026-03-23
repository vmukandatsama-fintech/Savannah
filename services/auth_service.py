from django.db import connection


def login_sql_user(email: str, password: str):
    with connection.cursor() as cursor:
        cursor.execute(
            "EXEC dbo.spUserLoginProfile @Email=%s, @Password=%s",
            [email, password],
        )

        while True:
            if cursor.description is not None:
                row = cursor.fetchone()
                if row:
                    columns = [col[0] for col in cursor.description]
                    result = dict(zip(columns, row))

                    auth_value = result.get("IsAuthenticated", 0)
                    try:
                        auth_value = int(auth_value or 0)
                    except Exception:
                        auth_value = 0

                    if auth_value != 1:
                        return None

                    return {
                        "IsAuthenticated": auth_value,
                        "Email": (result.get("Email") or "").strip(),
                        "Name": (result.get("Name") or "").strip(),
                        "DepartmentCode": (result.get("DepartmentCode") or "").strip(),
                        "DepartmentName": (result.get("DepartmentName") or "").strip(),
                        "RoleName": (result.get("RoleName") or "").strip(),
                        "AuthRequired": result.get("AuthRequired", 0),
                        "IsStoresController": result.get("IsStoresController", 0),
                        "IsRequestor": result.get("IsRequestor", 0),
                        "IsApprover": result.get("IsApprover", 0),
                        "IsAuthorizer": result.get("IsAuthorizer", 0),
                        "AppTarget": (result.get("AppTarget") or "").strip(),
                        "AppTargetCode": result.get("AppTargetCode", 0),
                        "ApproverEmails": (result.get("ApproverEmails") or "").strip(),
                        "ApproverNames": (result.get("ApproverNames") or "").strip(),
                        "AuthorizerEmails": (result.get("AuthorizerEmails") or "").strip(),
                        "AuthorizerNames": (result.get("AuthorizerNames") or "").strip(),
                    }

            if not cursor.nextset():
                break

        return None
