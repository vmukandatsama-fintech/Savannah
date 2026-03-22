from services.user_service import get_user_context


def global_user_context(request):
    user = getattr(request, "user", None)

    if not user or not user.is_authenticated:
        return {}

    user_email = (getattr(user, "email", "") or "").strip()

    if not user_email:
        user_email = (getattr(user, "username", "") or "").strip()

    if not user_email:
        return {}

    try:
        user_context = get_user_context(user_email)
        return {"user_context": user_context} if user_context else {}
    except Exception:
        return {}
