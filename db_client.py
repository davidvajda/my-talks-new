import sqlite3
import hashlib
import os


class Database:
    def __init__(
        self,
        path: str = "./database/my-talks-database.db"
    ):
        self.connection = sqlite3.connect(path)

        # create users table if it doesn't exist yet
        self.connection.execute("""
        CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL,
        role TEXT NOT NULL,
        password TEXT NOT NULL,
        salt BLOB NOT NULL
        );
        """)

        # create reviews table if it doesn't exist yet
        self.connection.execute("""
        CREATE TABLE IF NOT EXISTS reviews(
        id INTEGER PRIMARY KEY,
        author_id INTEGER NOT NULL,
        target_user_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        review TEXT NULL,
        FOREIGN KEY(author_id) REFERENCES users(id),
        FOREIGN KEY(target_user_id) REFERENCES users(id)
        );
        """)

        self.connection.commit()

    def create_user(self, name: str, email: str, password: str, role: str):
        salt = os.urandom(32)

        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000
        )

        self.connection.execute(
            "INSERT INTO users (name, email, password, salt, role) VALUES(?, ?, ?, ?, ?);",
            (name, email, password_hash, salt, role, )
        )
        self.connection.commit()

    def check_user(self, name: str, password: str) -> bool:
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE name = ?;",
            (name, )
        )

        users = cursor.fetchall()

        # if no user with provided name was found, return false
        if not users:
            return False

        user = users[0]

        user_password_hash = user[4]
        user_salt = user[5]

        # do the same hashing function as when user was created
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            user_salt,
            100000
        )

        if user_password_hash == password_hash:
            return True
        return False

    def create_review(self, autor_id: int, target_id: int, rating: int, review: str):
        pass

    def connection_close(self):
        self.connection.close()


if __name__ == "__main__":
    db = Database()

    db.create_user("David Vajda", "my-email@gmail.com", "password", "Talkie")
    print(db.check_user("David Vajda", "password"))
    print(db.check_user("David", "password"))
    db.connection_close()
