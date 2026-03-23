ROLE_FEATURES = {
    "Requestor": {
        "dashboard": True,
        "create_request": True,
        "my_requests": True,
        "approvals": False,
        "collections": False,
        "reports": False,
        "admin": False,
    },
    "Approver": {
        "dashboard": True,
        "create_request": True,
        "my_requests": True,
        "approvals": True,
        "collections": False,
        "reports": False,
        "admin": False,
    },
    "Authorizer": {
        "dashboard": True,
        "create_request": False,
        "my_requests": True,
        "approvals": True,
        "collections": False,
        "reports": False,
        "admin": False,
    },
    "Stores Controller": {
        "dashboard": True,
        "create_request": False,
        "my_requests": False,
        "approvals": False,
        "collections": True,
        "reports": True,
        "admin": False,
    },
}


def get_role_features(role_name: str | None) -> dict:
    if not role_name:
        return {}

    return ROLE_FEATURES.get(role_name, {})
