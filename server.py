from sre_parse import SPECIAL_CHARS
from flask import request, render_template, session, redirect, url_for, flash, abort
from flask_socketio import join_room, close_room, emit

import datetime
import json

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

SERVER_MESSAGES = {
    "EMAIL_EXISTS": "E-Mail you've entered has already been signed up. Did you forget your password?",
    "INVALID_SIGNUP": f"Something went wrong. Be sure to enter a name between 4 to 29 characters and password with a letter, number and a special character: ({SPECIAL_CHARS}).",
}

app = setup_flask_app()
sio = setup_socketio_app(app)

que = Queue()
rooms = dict()


def emit_chat_message(
    message_text: str = "",
    message_author: str = "",
    message_type: str = "chat-message",
    room: str = "",
) -> None:
    if not room:
        print("[ERROR] emit_chat_message called without room value")
        raise ValueError(
            "Function emit_chat_message must have specified room to emit message to."
        )

    if room not in rooms:
        print("[ERROR] called room not in the availible rooms")
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

def disconnect_user():
    room_name = session["user"].room
    
    # if someone is still in the toom, pop the disconnected user and send a message to the remaining users
    if len(rooms[room_name]) > 1:
        uid = rooms[room_name].index(session["user"].id)
        rooms[room_name].pop(uid)

        emit_chat_message(
            message_text= session["user"].name + " has disconnected!",
            message_type="server-messasge",
            room=session["user"].room,
        )

    # if there is noone left in the room, close it
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
@signed_out_only
def signin():
    if request.method == "GET":
        return render_template("signin.html")

    db = Database()

    email = request.form["email"]
    password = request.form["password"]

    if not validate_email(email) or not validate_password(password):
        flash("Unvalid email or password!")  # TODO: constant
        return redirect("signin")

    user = db.get_user(email, password)

    if not user:
        db.connection_close()
        flash("Unvalid email or password!")  # constatn
        return redirect(url_for("signin"))

    id_, name_, email_, role_ = user[:4]
    session["user"] = Person(id_, name_, email_, role_)
    flash("You've been loged in successfully!")
    db.connection_close()
    return redirect(url_for("index"))


@app.route("/review", methods=["GET", "POST"])
@signed_in_only
def review():
    if request.method == "GET":
        return render_template("review.html", user = None)

    # on post create review

# serves information about a user
@app.route("/user/<id>", methods=["GET"])
def user_info(id: int = -1):
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


@app.route("/signout")
def signout():
    session.pop("user", None)
    flash("You've been signed out!")  # TODO: constant
    return redirect(url_for("index"))


@app.route("/chat")
@signed_in_only
def chat():
    return render_template("chat.html")


@sio.on("connect")
@signed_in_only
def connect():
    # if set false, socket-io app is not able to make changes to session
    # not sure why it's not set to true automatically, perhaps because I change only dict values
    session.modified = True

    session["user"].set_sid(request.sid)

    # in case user refreshed browser they're assigned new sid
    # i'm sending soom name to the server so they can connect to the same room again
    old_room_name = session["user"].room 

    if old_room_name and old_room_name in rooms:
        rooms[old_room_name].append(session["user"].id)
        join_room(old_room_name)

        emit_chat_message(
            message_text=session["user"].name + " has reconnected.",
            message_type="server-messasge",
            room=session["user"].room,
        )
        return

    if que.is_empty() or que.peek().compare_roles(session["user"]):
        enqueue_user()

        emit_chat_message(
            message_text="You have been enqueued, please wait for someone to connect.",
            message_type="server-messasge",
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
                message_type="server-messasge",
                room=session["user"].room,
            )

            return

        join_room(room_name)
        session["user"].set_room(room_name)
        session["user"].pair_person(paired_user.id)
        paired_user.pair_person(session["user"].id)
        rooms[room_name].append(session["user"].id)


        emit_chat_message(
            message_text= session["user"].name + " has joined the chat, say hello.",
            message_type="server-messasge",
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
    message_text = data.get("text") if data.get("text") else ""
    message_author = session["user"].name
    room = session["user"].room

    emit_chat_message(
        message_text=message_text, message_author=message_author, room=room
    )

    # TODO: save other user id into session under user_to_review key after other user sends a message


if __name__ == "__main__":
    sio.run(app, debug=True)
