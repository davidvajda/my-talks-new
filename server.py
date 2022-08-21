from flask import Flask

from db_client import Database

app = Flask(__name__)

@app.route("/")
def hello_world():
    db = Database()

    db.connection_close()

if __name__ == "__main__":
    app.run(debug=True)