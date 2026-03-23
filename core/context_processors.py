
from core.models import RoleFeature, Roles


def user_context(request):

    role_name = request.session.get("role_name")
    features = {}
    if role_name:
        try:
            role = Roles.objects.get(name=role_name)
            rf = RoleFeature.objects.get(role=role)
            features = {
                "dashboard": rf.dashboard,
                "create_request": rf.create_request,
                "my_requests": rf.my_requests,
                "approvals": rf.approvals,
                "collections": rf.collections,
                "reports": rf.reports,
                "admin": rf.admin,
            }
        except (Roles.DoesNotExist, RoleFeature.DoesNotExist):
            features = {}

    return {
        "session_user_email": request.session.get("user_email"),
        "session_user_name": request.session.get("user_name"),
        "session_role_name": role_name,
        "session_department_code": request.session.get("department_code"),
        "session_department_name": request.session.get("department_name"),
        "session_features": features,
    }
