import re

COMMON_PASSWORDS = {
    "password", "password123", "12345678", "qwerty123", "admin123",
    "letmein", "welcome", "changeme", "abc123", "11111111",
}


def validate_password(pw: str) -> None:
    """
    Raise ValueError with a helpful message if the password is too weak.
    """
    if not pw or len(pw) < 8:
        raise ValueError("Password must be at least 8 characters.")
    if len(pw) > 128:
        raise ValueError("Password is too long (max 128 characters).")
    if pw.lower() in COMMON_PASSWORDS:
        raise ValueError("Password is too common. Choose something less predictable.")
    if not re.search(r"[A-Za-z]", pw):
        raise ValueError("Password must contain at least one letter.")
    if not re.search(r"[0-9]", pw):
        raise ValueError("Password must contain at least one digit.")
