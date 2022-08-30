from sre_parse import SPECIAL_CHARS, DIGITS, ASCIILETTERS

def validate_username(username: str) -> bool:
    if isinstance(username, str):
        length = len(username)
        if length > 3 and length < 30:
            return True
    return False


def validate_password(password: str) -> bool:
    special_char = digit = asci = False

    if isinstance(password, str):
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


def validate_email(email: str) -> bool:
    if isinstance(email, str) and "@" in email and "." in email:
        return True
    return False


def validate_role(role: str) -> bool:
    if role == "talkie" or role == "listener":
        return True
    return False
