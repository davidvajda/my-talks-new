from sre_parse import SPECIAL_CHARS
from flask import request, render_template, session, redirect, url_for, flash, abort
from flask_socketio import join_room, close_room, emit

import datetime

from server_setup import setup_flask_app, setup_socketio_app
from helper_functions import (
    validate_username,
    validate_email,
    validate_password,
    validate_role,
)
from decors import signed_in_only, signed_out_only

from db_client import Database
from q import Queue
from person import Person

import datetime

app = setup_flask_app()
sio = setup_socketio_app(app)

que = Queue()
rooms = dict()


def emit_chat_message(
    message_text: str = "",
    message_author: str = "",
    message_type: str = "chat-message",
    room: str = None,
    sid: str = None,
) -> None:
    """Emit a 'message' socketio event. 
    It is possible to emit to a room or specific sid, if specific sid is provided, message is not send to a room."""

    if not room or not sid:
        raise ValueError(
            "Function emit_chat_message must have specified room or sid to emit message to."
        )

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
        return

    if room not in rooms:
        raise ValueError(
            "Function emit_chat_message tried to send a message to unvalid room."
        )

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


def enqueue_user():
    room_name = "room#" + str(session["user"].sid)
    join_room(room_name)

    session["user"].set_room(room_name)
    session["user"].unpair()
    rooms[room_name] = [session["user"].id]

    que.enqueue(session["user"])


def disconnect_user(manual_leave: bool = False):
    room_name = session["user"].room

    # if someone is still in the toom, pop the disconnected user and send a message to the remaining users
    if len(rooms[room_name]) > 1:
        uid = rooms[room_name].index(session["user"].id)
        rooms[room_name].pop(uid)

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


@app.route("/")
def index():
    user = session.get("user")
    return render_template("index.html", user=user)


@app.route("/signup", methods=["GET", "POST"])
@signed_out_only
def signup():
    if request.method == "GET":
        return render_template("signup.html")

    username = request.form["username"]
    password = request.form["password"]
    email = request.form["email"]
    role = request.form["role"]

    unvalid = False

    if not validate_username(username):
        flash("Be sure to enter a name between 4 to 29 characters!")

    if not validate_email(email):
        flash("The email you've entered is invalid!")
        unvalid = True

    if not validate_password(password):
        flash("The password you've entered is invalid!")
        flash("Be sure to enter a password with a letter, number and a special character " + SPECIAL_CHARS)
        unvalid = True

    if not validate_role(role):
        flash("unvalid role!")

    if unvalid:
        return redirect(url_for("signup"))

    db = Database()

    if db.check_email_exists(email):
        flash(
            "E-Mail you've entered has already been signed up."
        )
        db.connection_close()
        return redirect(url_for("signin")), 400

    user_id = db.create_user(username, email, password, role)
    if user_id == -1:
        flash("Oops, something went wrong. Registration attempt was not successfull!")
        redirect(url_for("index"))

    session["user"] = Person(user_id, username, email, role)
    db.connection_close()
    return redirect(url_for("index")), 200


# func will serve template with GET method and will accept signin form via POST method
# also it will be possible to GET this page only when signed out
@app.route("/signin", methods=["GET", "POST"])
@signed_out_only
def signin():
    if request.method == "GET":
        return render_template("signin.html")

    db = Database()

    email = request.form["email"]
    password = request.form["password"]

    unvalid = False

    if not validate_email(email):
        flash("The email you've entered is invalid!")
        unvalid = True

    if not validate_password(password):
        flash("The password you've entered is invalid!")
        unvalid = True

    if unvalid:
        return redirect("signin")

    user = db.get_user(email, password)

    if not user:
        db.connection_close()
        flash("The email and password combination you've entered does not exist!")
        return redirect(url_for("signin"))

    id_, name_, email_, role_ = user[:4]
    session["user"] = Person(id_, name_, email_, role_)
    db.connection_close()

    flash("You've been loged in successfully!")
    return redirect(url_for("index"))


@app.route("/review", methods=["GET", "POST"])
@signed_in_only
def review():
    uid_to_review = session.get("uid_to_review")
    author_id = session["user"].id

    if not uid_to_review:
        return redirect(url_for("index"))

    if request.method == "GET":
        db = Database()
        id, name, role, image_url, email = db.get_user_by_id(uid_to_review)
        db.connection_close()

        return render_template(
            "review.html",
            name=name,
            role=role,
            image_url=image_url,
            user=session["user"],
        )

    # POST
    rating = int(request.form["rating"], 10)
    review = request.form["review"]

    # TODO: validate input

    if rating < 0 or rating > 5:
        raise ValueError(
            f"Unvalid rating value of {rating}, valid range is (int) 0 to 5 inclusive"
        )

    if len(review) > 1000:
        review = review[:997] + "..."

    db = Database()
    db.create_review(author_id, uid_to_review, rating, review)
    db.connection_close()

    flash("Your review was saved.")
    return redirect(url_for("index"))


# serves information about a user
@app.route("/user/<id>", methods=["GET"])
@signed_in_only
def user_info(id: int):
    if not session.get("user"):
        abort(404)

    if id == -1:
        return str(session.get("user"))

    db = Database()
    user = db.get_user_by_id(id)
    db.connection_close()

    if not user:
        abort(404)

    return str(user)


@app.route("/profile", methods=["GET"])
@signed_in_only
def profile():
    db = Database()

    reviewers = []
    reviews = db.get_reviews(session["user"].id)

    for review in reviews:
        id_, name_, role_, image_, email_ = db.get_user_by_id(review[2])
        reviewer = Person(id_, name_, email_, role_, image_)
        reviewers.append(reviewer)

    db.connection_close()

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

    sio.emit("username", {"username": session["user"].name}, to=session["user"].sid)

    # in case user refreshed browser they're assigned new sid
    # i'm sending soom name to the server so they can connect to the same room again
    old_room_name = session["user"].room

    if old_room_name and old_room_name in rooms:
        rooms[old_room_name].append(session["user"].id)
        join_room(old_room_name)

        emit_chat_message(
            message_text=session["user"].name + " has reconnected.",
            message_type="server-message",
            room=session["user"].room,
        )
        return

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
        rooms[room_name].append(session["user"].id)

        # TODO: get other user sid and send individual message to him
        # use /user/<id> for it
        emit_chat_message(
            message_text=session["user"].name + " has joined the chat, say hello.",
            message_type="server-message",
            room=session["user"].room,
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
        session["uid_to_review"] = room[0] if room[0] != session["user"].id else room[1]


if __name__ == "__main__":
    sio.run(app, debug=True)

    # TODO: write tests
