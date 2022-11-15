import hashlib
import os

def hash_password(password: str, salt: bytes = None) -> (bytes, bytes):
    """returns hashed password and a salt -> (password, salt)"""
    salt_to_use = salt or os.urandom(32)
    password_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt_to_use,
        100000
    )

    return (password_hash, salt_to_use)
