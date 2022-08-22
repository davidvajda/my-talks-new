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
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
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

    def create_user(self, name: str, email: str, password: str, role: str) -> bool:
        salt = os.urandom(32)

        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000
        )

        try:
            self.connection.execute(
                "INSERT INTO users (name, email, password, salt, role) VALUES(?, ?, ?, ?, ?);",
                (name, email, password_hash, salt, role, )
            )
            self.connection.commit()
            return True

        except Exception as e:
            print("[ERROR create_user]", e)
            return False
      

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

    def check_email_exists(self, email: str) -> bool:
        cursor = self.connection.cursor()

        cursor.execute("SELECT * FROM users WHERE email = ?", (email, ))
        users = cursor.fetchall()

        if not users:
            return False
        return True

    def create_review(self, author_id: int, target_id: int, rating: int, review: str) -> bool:
        try:
            self.connection.execute(
                "INSERT INTO reviews (author_id, target_user_id, rating, review) VALUES(?, ?, ?, ?);",
                (author_id, target_id, rating, review,)
            )
            self.connection.commit()
        
        except Exception as e:
            print("[ERROR create_review]", e)

    def get_reviews(self, target_user_id: int) -> list:
        cursor = self.connection.cursor()

        cursor.execute("SELECT rating, review FROM reviews WHERE target_user_id = ?", (target_user_id, ))
        reviews = cursor.fetchall()

        return reviews

    def connection_close(self):
        self.connection.close()
