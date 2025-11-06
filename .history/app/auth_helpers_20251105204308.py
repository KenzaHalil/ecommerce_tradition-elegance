from functools import wraps
from flask import session, redirect, url_for, request, flash

def login_required(redirect_next=True):
    def deco(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if session.get("user_id") is None:
                flash("Connectez‑vous pour accéder à cette page.", "warning")
                if redirect_next:
                    return redirect(url_for("auth.login", next=request.url))
                return redirect(url_for("auth.login"))
            return func(*args, **kwargs)
        return wrapper
    return deco