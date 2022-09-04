from sre_parse import SPECIAL_CHARS
from flask import request, render_template, session, abort, redirect, url_for, flash
from flask_socketio import join_room, close_room, emit

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

SERVER_MESSAGES = {
    "EMAIL_EXISTS": "E-Mail you've entered has already been signed up. Did you forget your password?",
    "INVALID_SIGNUP": f"Something went wrong. Be sure to enter a name between 4 to 29 characters and password with a letter, number and a special character: ({SPECIAL_CHARS}).",
}

app = setup_flask_app()
sio = setup_socketio_app(app)

que = Queue()
rooms = dict()


def enqueue_user(user: Person) -> None:
    que.enqueue(user)
    room_name = "room#" + str(user.sid)
    join_room(room_name)
    user.set_room(room_name)
    rooms[room_name] = [user, ]


@app.route("/")
def index():
    user = session.get("user")
    return render_template("index.html", user = user)


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
@signed_out_only
def signin():
    if request.method == "GET":
        return render_template("signin.html")

    db = Database()

    email = request.form["email"]
    password = request.form["password"]

    if not validate_email(email) or not validate_password(password):
        flash("Unvalid email or password!") # TODO: constant
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


# serves information about a user
@app.route("/user/<user_id>", methods=["GET"])
def user_info(user_id):
    return "user_id"


@app.route("/signout")
def signout():
    session.pop("user", None)
    flash("You've been signed out!")  # TODO: constant
    return redirect(url_for("index"))

@app.route("/queue")
@signed_in_only
def queue():
    return render_template("queue.html")


@sio.on("connect")
def connect():
    if not session.get("user"):
        return redirect(url_for("signin"))


    user = session["user"]
    user.set_sid(request.sid)

    print("[SERVER LOG]", f"{user.name} has connected to socketio")

    if que.is_empty() or que.peek().compare_roles(user):
        enqueue_user(user)

        emit("enqueued", {"message": "You have been enequeued"}, to=user.room)
        print(f"[SERVER LOG] {user.name} has been enqueued as {user.role}")

    # if there's opposite role in the front of the queue, pair them and start the chat
    else:
        room_name = None

        while not que.is_empty():
            paired_user = que.dequeue()
            room_name = paired_user.room

            if rooms.get(room_name):
                break

        else:
            # enqueue the user in case he needs to wait for other opposite role user to connect
            enqueue_user(user)

            emit("enqueued", {"message": "You have been enequeued"}, to=user.room)
            print(f"[SERVER LOG] {user.name} has been enqueued as {user.role}")
            return


        join_room(room_name) 
        rooms[room_name].append(user)
        print(f"[SERVER LOG] {user.name} has joined the {room_name} chat")
        emit("enqueued", {"message": f"{user.name} has joined the chat"}, to=user.room)
        return


@sio.on("disconnect")
def disconnect():
    user = session.get("user")

    if not user:
        return

    print("[SERVER LOG]", user.name, "has disconnected")

    room_name = user.room
    room = rooms.get(room_name)

    if not room:
        return None

    if len(rooms[room_name]) == 0:
        close_room(room_name)
        rooms.pop(room_name)

    else:
        rooms[room_name].pop(rooms[room_name].index(user))
        emit("message", {
            "data": f"{user.name} has left the chat!",
            "type": "server_message"
            }, to=room_name)



@sio.on("message")
def message(data):
    print(data)
        

    




if __name__ == "__main__":
    sio.run(app)
