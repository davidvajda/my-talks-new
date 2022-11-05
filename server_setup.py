from flask import Flask
from flask_socketio import SocketIO
from flask_session import Session

def setup_flask_app() -> Flask:
    app = Flask(__name__)
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_PERMANENT"] = False
    app.config.from_object(__name__)
    app.secret_key = "ec9252351c9bc212f833cb53cf621df6d675385f819f3769c59cfe69f04babf5"
    Session(app)
    return app


def setup_socketio_app(app) -> SocketIO:
    sio = SocketIO(app, manage_session=False)
    return sio
