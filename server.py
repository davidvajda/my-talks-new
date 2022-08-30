from sre_parse import SPECIAL_CHARS
from flask import request, render_template, session, abort, redirect, url_for, flash
from functools import wraps

from setup_app import setup_flask_app, setup_socketio_app
from helper_functions import (
    validate_username,
    validate_email,
    validate_password,
    validate_role,
)
from decorators import signed_in_only, signed_out_only

from db_client import Database
from q import Queue
from person import Person

SERVER_MESSAGES = {
    "EMAIL_EXISTS": "E-Mail you've entered has already been signed up. Did you forget your password?",
    "INVALID_SIGNUP": f"Something went wrong. Be sure to enter a name between 4 to 29 characters and password with a letter, number and a special character: ({SPECIAL_CHARS}).",
}

app = setup_flask_app()
sio = setup_socketio_app(app)


@app.route("/")
def index():
    return render_template("index.html")


# func will serve template with GET method and will accept signup form via POST method
# also it will be possible to GET this page only when signed out


@app.route("/signup", methods=["GET", "POST"])
@signed_out_only
def signup():
    if request.method == "GET":
        return render_template("signup.html")

    username = request.form["username"]
    password = request.form["password"]
    email = request.form["email"]
    role = request.form["role"]

    if (
        not validate_username(username)
        or not validate_password(password)
        or not validate_email(email)
        or not validate_role(role)
    ):
        flash(SERVER_MESSAGES["INVALID_SIGNUP"])
        return redirect(url_for("signup"))

    db = Database()

    if db.check_email_exists(email):
        flash(SERVER_MESSAGES["EMAIL_EXISTS"])
        db.connection_close()  # TODO: make decorator to close connection automatically
        return redirect(url_for("signup"))

    user_id = db.create_user(username, email, password, role)
    if user_id == -1:
        flash("something went wrong")  # TODO: custom message in constant
        redirect(url_for("index"))

    session["user"] = Person(user_id, username, email, role)
    db.connection_close()  # TODO: make decorator to close connection automatically
    return redirect(url_for("index"))


# func will serve template with GET method and will accept signin form via POST method
# also it will be possible to GET this page only when signed out
@app.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "GET":
        return render_template("signin.html")

    db = Database()

    email = request.form["email"]
    password = request.form["password"]

    user = db.get_user(email, password)

    if not user:
        db.connection_close()
        flash("Unvalid email or password!")  # constatn
        return redirect(url_for("signin"))

    id_, name_, email_, role_ = user
    session["user"] = Person(id_, name_, email_, role_)
    flash("You've been loged in successfully!")
    db.connection_close()
    return redirect(url_for("index"))


# serves information about a user
@app.route("/info/<username>", methods=["GET"])
def user_info(username):
    print(str(session["user"]))
    return str(session["user"])


@app.route("/signout")
def signout():
    session.pop("user", None)
    flash("You've been signed out!")  # TODO: constant
    return redirect(url_for("index"))


# get reviews (user_id)
# create review (....)


if __name__ == "__main__":
    sio.run(app, debug=True)
