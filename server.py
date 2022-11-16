from sre_parse import SPECIAL_CHARS
from flask import request, render_template, session, redirect, url_for, flash
from flask_socketio import join_room, close_room, emit

from collections import namedtuple

from server_setup import setup_flask_app, setup_socketio_app, setup_db_app
from input_validation import (
    validate_username,
    validate_email,
    validate_password,
    validate_role,
)
from decors import signed_in_only, signed_out_only

from q import Queue
from person import Person

from models import hash_password

import datetime

app = setup_flask_app()
sio = setup_socketio_app(app)
sql_db = setup_db_app(app)

que = Queue()  # queue contains Person objects
rooms = dict()  # rooms contains list of two sids

User_ids = namedtuple("User_ids", ["id", "sid"])

# TODO: make models.py separate file
class User(sql_db.Model):
    __tablename__ = "users"
    id = sql_db.Column(sql_db.Integer, primary_key=True)
    name = sql_db.Column(sql_db.String, nullable=False)
    email = sql_db.Column(sql_db.String, nullable=False, unique=True)
    role = sql_db.Column(sql_db.String(8), nullable=False)
    password = sql_db.Column(sql_db.BLOB, nullable=False)
    salt = sql_db.Column(sql_db.BLOB, nullable=False)
    image = sql_db.Column(sql_db.String)

    def jsonify_for_person(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "image": self.image,
        }

    def __repr__(self):
        return f"User(id={self.id}, name={self.name}, role={self.role})"


class Review(sql_db.Model):
    __tablename__ = "reviews"
    id = sql_db.Column(sql_db.Integer, primary_key=True)
    rating = sql_db.Column(sql_db.Integer, nullable=False)
    review = sql_db.Column(sql_db.String(999))
    author_id = sql_db.Column(sql_db.ForeignKey("users.id"))
    user_id = sql_db.Column(sql_db.ForeignKey("users.id"))

    def __repr__(self):
        return f"Review(id={self.id}, rating={self.rating}, review={self.review})"

with app.app_context():
    sql_db.create_all()

def emit_chat_message(
        message_text: str = "",
        message_author: str = "",
        message_type: str = "chat-message",
        room: str = None,
        sid: str = None,
) -> bool:
    """Emit a 'message' socketio event.
    It is possible to emit to a room or specific sid, if specific sid is provided, message is not send to a room."""

    # when session id is provided it has priority over room
    if sid:
        emit(
            "message",
            {
                "message_text": message_text,
                "message_author": message_author,
                "message_type": message_type,
                "date": str(datetime.datetime.now()),
            },
            to=sid,
        )
        return True

    if room and room in rooms:
        emit(
            "message",
            {
                "message_text": message_text,
                "message_author": message_author,
                "message_type": message_type,
                "date": str(datetime.datetime.now()),
            },
            to=room,
        )
        return True
    return False


def enqueue_user() -> None:
    room_name = "room#" + str(session["user"].sid)
    join_room(room_name)

    session["user"].set_room(room_name)
    session["user"].unpair()

    rooms[room_name] = [User_ids(session["user"].id, session["user"].sid)]

    que.enqueue(session["user"])
    return


def disconnect_user(manual_leave: bool = False) -> None:
    room_name = session["user"].room

    # if someone is still in the room, pop the disconnected user and send a message to the remaining users
    if len(rooms[room_name]) > 1:
        rooms[room_name].pop(0 if rooms[room_name][0].id == session["user"].id else 1)

        emit_chat_message(
            message_text=session["user"].name + " has left the chat!"
            if manual_leave
            else session["user"].name + " has disconnected!",
            message_type="server-message",
            room=session["user"].room,
        )

    # if there is none left in the room, close it
    else:
        rooms.pop(room_name)
        close_room(room_name)
    return


@app.route("/")
def index():
    user = session.get("user")

    return render_template("index.html", user=user)


@app.route("/signup", methods=["GET", "POST"])
@signed_out_only
def signup():
    if request.method == "GET":
        return render_template("signup.html")

    username = {
        "value": request.form.get("username", None),
        "error": False,
        "error_message": None,
    }
    password = {
        "value": request.form.get("password"),
        "error": False,
        "error_message": None,
    }
    email = {
        "value": request.form.get("email"),
        "error": False,
        "error_message": None,
    }
    role = {
        "value": request.form.get("role"),
        "error": False,
        "error_message": None,
    }

    if not validate_username(username["value"]):
        username["error"] = True
        username["error_message"] = "Be sure to enter a name between 4 to 29 characters"

    if not validate_email(email["value"]):
        email["error"] = True
        email["error_message"] = "Invalid e-mail"

    if not validate_password(password["value"]):
        password["error"] = True
        password["error_message"] = (
                "Be sure to enter a password with a letter, number and a special character "
                + SPECIAL_CHARS
        )

    if not validate_role(role["value"]):
        role["error"] = True
        role["error_message"] = "Invalid role"

    if not email["error"]:
        does_exist = User.query.filter_by(email=email["value"]).first()

        if does_exist:
            email["error"] = True
            email["error_message"] = "E-Mail you've entered has already been signed up"

    errors = [username["error"], password["error"], email["error"], role["error"]]
    if any(errors):
        password["value"] = None

        payload = {
            "name": username,
            "password": password,
            "email": email,
            "role": role,
        }
        return render_template("signup.html", **payload), 422

    hashed_password, salt = hash_password(password["value"])

    user_from_db = User.query.filter_by(email=email["value"]).first()
    if user_from_db:
        flash("E-mail already registered.")
        return render_template("signup.html"), 422

    user = User(**{
        "name": username["value"],
        "email": email["value"],
        "role": role["value"],
        "password": hashed_password,
        "salt": salt,
        "image": None,
    })

    sql_db.session.add(user)
    sql_db.session.commit()

    session["user"] = Person(**user.jsonify_for_person())
    return redirect(url_for("index"))


# func will serve template with GET method and will accept signin form via POST method
# also it will be possible to GET this page only when signed out
@app.route("/signin", methods=["GET", "POST"])
@signed_out_only
def signin():
    if request.method == "GET":
        return render_template("signin.html")

    email = {
        "value": request.form.get("email", None),
        "error": False,
        "error_message": None,
    }

    password = {
        "value": request.form.get("password", None),
        "error": False,
        "error_message": None,
    }

    if not validate_email(email["value"]):
        email["error"] = True
        email["error_message"] = "This email is invalid."

    if not validate_password(password["value"]):
        password["error"] = True
        password["error_message"] = "The password you've entered is invalid."

    errors = [email["error"], password["error"]]

    if any(errors):
        password["value"] = None
        payload = {
            "email": email,
            "password": password
        }
        return render_template("signin.html", **payload), 422

    def validate_user(user, password) -> bool:
        if not user:
            return False

        hash, _salt = hash_password(password, user.salt)
        return True if hash == user.password else False

    user = User.query.filter_by(email=email["value"]).first()

    if not validate_user(user, password["value"]):
        flash("The email and password combination you've entered does not exist!")
        return render_template("signin.html")

    session["user"] = Person(**user.jsonify_for_person())

    flash("You've been logged in successfully.")
    return redirect(url_for("index"))


@app.route("/review", methods=["GET", "POST"])
@signed_in_only
def review():
    uid_to_review = session.get("uid_to_review")
    author_id = session["user"].id

    if not uid_to_review:
        return redirect(url_for("index"))

    if request.method == "GET":
        user = User.query.get(uid_to_review)

        payload = {
            "name": user.name,
            "role": user.role,
            "image_url": user.image,
            "user": session["user"]
        }

        return render_template("review.html", **payload)

    # POST
    rating = int(request.form.get("rating", -1), 10)
    review = request.form.get("review", None)

    if rating < 0 or rating > 5:
        flash("Unvalid rating.")
        return redirect(url_for(("redirect")))

    if len(review) > 1000:
        review = review[:997] + "..."

    new_review = Review(
        rating=rating,
        review=review,
        author_id=author_id,
        user_id=uid_to_review,
    )
    sql_db.session.add(new_review)
    sql_db.session.commit()

    flash("Your review was saved.")
    return redirect(url_for("index"))


@app.route("/profile", methods=["GET"])
@signed_in_only
def profile():
    reviewers = []
    reviews = Review.query.filter_by(user_id=session["user"].id).all()

    for review in reviews:
        reviewer = User.query.get(review.id)
        reviewers.append(reviewer)

    return render_template(
        "profile.html", user=session["user"], reviews=reviews, reviewers=reviewers
    )

@app.route("/signout")
def signout():
    session.pop("user", None)
    flash("You've been signed out!")
    return redirect(url_for("index"))


@app.route("/chat")
@signed_in_only
def chat():
    return render_template("chat.html", user=session["user"], chat=True)


@app.route("/session")
def session_test():
    "Returns contents of session for test purposes"
    return dict(session), 200


@sio.on("connect")
@signed_in_only
def connect():
    # if set false, socket-io app is not able to make changes to session
    # not sure why it's not set to true automatically, perhaps because I change only dict values
    session.modified = True

    session["user"].set_sid(request.sid)
    session[
        "uid_to_review"
    ] = None  # setting this to none, so i can avoid rewriting it on every message

    # sending username to the frontend, messages are differentiated by author of the message
    sio.emit("username", {"username": session["user"].name}, to=session["user"].sid)

    # in case there exists room assigned to the user and it's still alive, restore the connection
    old_room_name = session["user"].room

    if old_room_name and old_room_name in rooms:
        other_user_sid = rooms[old_room_name][0].sid
        rooms[old_room_name].append(User_ids(session["user"].id, session["user"].sid))
        join_room(old_room_name)

        emit_chat_message(
            message_text=session["user"].name + " has reconnected.",
            message_type="server-message",
            sid=other_user_sid,
        )

        emit_chat_message(
            message_text="You have reconnected!",
            message_type="server-message",
            sid=session["user"].sid,
        )
        return

    # in case there is nobody to connect to
    if que.is_empty() or que.peek().compare_roles(session["user"]):
        enqueue_user()

        emit_chat_message(
            message_text="You have been enqueued, please wait for someone to connect.",
            message_type="server-message",
            room=session["user"].room,
        )

        return

    # if there's opposite role in the front of the queue, pair them and start the chat
    else:
        while not que.is_empty():
            paired_user = que.dequeue()
            room_name = paired_user.room

            if rooms.get(room_name):
                break

        else:
            # enqueue the user in case he needs to wait for other opposite role user to connect
            enqueue_user()

            emit_chat_message(
                message_text="You have been enqueued, please wait for someone to connect.",
                message_type="server-message",
                room=session["user"].room,
            )

            return

        join_room(room_name)
        session["user"].set_room(room_name)
        rooms[room_name].append(User_ids(session["user"].id, session["user"].sid))

        emit_chat_message(
            message_text=session["user"].name + " has joined the chat, say hello.",
            message_type="server-message",
            sid=paired_user.sid,
        )

        emit_chat_message(
            message_text="You are talking to " + paired_user.name + ", say hello!",
            message_type="server-message",
            sid=session["user"].sid,
        )
        return


@sio.on("disconnect")
@signed_in_only
def disconnect():
    if session["user"].room not in rooms:
        return

    disconnect_user()


@sio.on("leave")
@signed_in_only
def leave():
    if session["user"].room not in rooms:
        return

    disconnect_user()
    session["user"].room = None


@sio.on("message")
@signed_in_only
def message(data):
    message_text = data.get("text")
    message_author = session["user"].name
    room_name = session["user"].room
    room = rooms.get(room_name)

    if not message_text:
        return

    emit_chat_message(
        message_text=message_text, message_author=message_author, room=room_name
    )

    # saving other user's ID into session to review it later
    if not session.get("uid_to_review") and room and len(room) > 1:
        session["uid_to_review"] = (
            room[0].id if room[0].id != session["user"].id else room[1].id
        )


if __name__ == "__main__":
    sio.run(app, debug=True)
    # sio.run(app, host="0.0.0.0", port=8080)

    # TODO: use logger
