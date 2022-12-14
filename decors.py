from flask import session, redirect, url_for
from functools import wraps

def signed_out_only(func):
    "Decorator, function only accessible when no user is loaded in session"
    @wraps(func)
    def signed_out_check(*args, **kvargs):
        if session.get("user"):
            return redirect(url_for("index")), 403
        return func(*args, **kvargs)
    return signed_out_check


def signed_in_only(func):
    @wraps(func)
    def signed_in_check(*args, **kvargs):
        if not session.get("user"):
            return redirect(url_for("index")), 401
        return func(*args, **kvargs)
    return signed_in_check