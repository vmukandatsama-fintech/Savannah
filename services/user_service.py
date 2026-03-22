from django.db import connection


def get_user_context(email):
    sql = """
        SELECT TOP 1
            u.Email,
            u.Name,
            ur.DepartmentCode,
            d.Name AS DepartmentName,
            d.AuthRequired,
            r.Name AS RoleName,

            CASE WHEN r.Name = 'Stores Controller' THEN 1 ELSE 0 END AS IsStoresController,
            CASE WHEN r.Name = 'Requestor' THEN 1 ELSE 0 END AS IsRequestor,
            CASE WHEN r.Name = 'Approver' THEN 1 ELSE 0 END AS IsApprover,
            CASE WHEN r.Name = 'Authorizer' THEN 1 ELSE 0 END AS IsAuthorizer,

            CASE 
                WHEN r.Name = 'Stores Controller' THEN 'STORES'
                WHEN r.Name = 'Requestor' THEN 'REQUEST'
                ELSE 'NO_ACCESS'
            END AS AppTarget,

            CASE 
                WHEN r.Name = 'Stores Controller' THEN 1
                WHEN r.Name = 'Requestor' THEN 2
                ELSE 0
            END AS AppTargetCode,

            (
                SELECT STRING_AGG(u2.Email, ';')
                FROM dbo.Users u2
                INNER JOIN dbo.UserDepartmentRoles ur2 ON u2.Email = ur2.UserEmail
                INNER JOIN dbo.Roles r2 ON ur2.RoleID = r2.RoleID
                WHERE ur2.DepartmentCode = ur.DepartmentCode
                  AND r2.Name = 'Approver'
            ) AS ApproverEmails,

            (
                SELECT STRING_AGG(u2.Name, ';')
                FROM dbo.Users u2
                INNER JOIN dbo.UserDepartmentRoles ur2 ON u2.Email = ur2.UserEmail
                INNER JOIN dbo.Roles r2 ON ur2.RoleID = r2.RoleID
                WHERE ur2.DepartmentCode = ur.DepartmentCode
                  AND r2.Name = 'Approver'
            ) AS ApproverNames,

            (
                SELECT STRING_AGG(u3.Email, ';')
                FROM dbo.Users u3
                INNER JOIN dbo.UserDepartmentRoles ur3 ON u3.Email = ur3.UserEmail
                INNER JOIN dbo.Roles r3 ON ur3.RoleID = r3.RoleID
                WHERE ur3.DepartmentCode = ur.DepartmentCode
                  AND r3.Name = 'Authorizer'
            ) AS AuthorizerEmails,

            (
                SELECT STRING_AGG(u3.Name, ';')
                FROM dbo.Users u3
                INNER JOIN dbo.UserDepartmentRoles ur3 ON u3.Email = ur3.UserEmail
                INNER JOIN dbo.Roles r3 ON ur3.RoleID = r3.RoleID
                WHERE ur3.DepartmentCode = ur.DepartmentCode
                  AND r3.Name = 'Authorizer'
            ) AS AuthorizerNames
        FROM dbo.Users u
        LEFT JOIN dbo.UserDepartmentRoles ur
            ON u.Email = ur.UserEmail
        LEFT JOIN dbo.Departments d
            ON ur.DepartmentCode = d.DepartmentCode
        LEFT JOIN dbo.Roles r
            ON ur.RoleID = r.RoleID
        WHERE LOWER(LTRIM(RTRIM(u.Email))) = LOWER(LTRIM(RTRIM(%s)))
          AND u.IsActive = 1
        ORDER BY
            CASE
                WHEN r.Name = 'Requestor' THEN 1
                WHEN r.Name = 'Stores Controller' THEN 2
                WHEN r.Name = 'Approver' THEN 3
                WHEN r.Name = 'Authorizer' THEN 4
                ELSE 99
            END
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, [email])
        row = cursor.fetchone()

        if not row:
            return None

        columns = [col[0] for col in cursor.description]
        result = dict(zip(columns, row))

    result["AuthRequired"] = bool(result.get("AuthRequired") or 0)
    result["IsStoresController"] = bool(result.get("IsStoresController") or 0)
    result["IsRequestor"] = bool(result.get("IsRequestor") or 0)
    result["IsApprover"] = bool(result.get("IsApprover") or 0)
    result["IsAuthorizer"] = bool(result.get("IsAuthorizer") or 0)

    return result
