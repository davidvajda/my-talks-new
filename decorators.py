from flask import session, redirect, url_for

def signed_out_only(func):
    "Decorator, function only accessible when no user is loaded in session"
    def decor(*args, **kvargs):
        if session.get("user"):
            print("already signed up")
            return redirect(url_for("index"))
        return func(*args, **kvargs)
    return decor


def signed_in_only(func):
    def decor(*args, **kvargs):
        if not session.get("user"):
            print("sign in required")
            return redirect(url_for("index"))
        return func(*args, **kvargs)
    return decor