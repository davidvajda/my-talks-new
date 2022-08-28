from sre_parse import SPECIAL_CHARS, DIGITS, ASCIILETTERS
from flask import Flask, request, render_template, session, abort, redirect, url_for
from flask_socketio import SocketIO
from flask_session import Session

from db_client import Database
from q import Queue

app = Flask(__name__)
app.config["SESSION_TYPE"] = "filesystem"
app.config.from_object(__name__)
Session(app)
sio = SocketIO(app)


def validate_username(username):
    length = len(username)
    if length > 3 and length < 30:
        return True
    return False


def validate_password(password):
    special_char = digit = asci = False

    for char in password:
        if char in SPECIAL_CHARS:
            special_char = True
        if char in DIGITS:
            digit = True
        if char in ASCIILETTERS:
            asci = True

    if all([special_char, digit, asci]):
        return True
    return False


def validate_email(email):
    if "@" in email and "." in email:
        return True
    return False


def validate_role(role):
    if role == "talkie" or role == "listener":
        return True
    return False


@app.route("/")
def index():
    return render_template("index.html")


# func will serve template with GET method and will accept signup form via POST method
# also it will be possible to GET this page only when signed out
@app.route("/signup", methods=["GET", "POST"])
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
        return redirect(url_for("signup")) # redirect with some messsage, like unvalid input, be sure to have password with bla bla bla

    db = Database()

    if db.check_email_exists(email):
        return redirect(url_for("signup")) # again some message, email already registered, did you forget your password?
        
    if db.create_user(username, email, password, role):
        return redirect(url_for("index"))

    return "bla" # in case when user couldn't be created, make some custom OOPS page, with contact form to developers


# func will serve template with GET method and will accept signin form via POST method
# also it will be possible to GET this page only when signed out
@app.route("/signin", methods=["GET", "POST"])
def signin():
    return render_template("signin.html")


# serves information about a user
@app.route("/info/<username>", methods=["GET"])
def user_info(username):
    return "pass"


# get reviews (user_id)
# create review (....)


if __name__ == "__main__":
    sio.run(app, debug=True)
