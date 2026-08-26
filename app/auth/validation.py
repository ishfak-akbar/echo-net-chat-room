import re

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")


def validate_username(username: str) -> str | None:
    """Returns an error message, or None if valid."""
    if not username:
        return "Username is required."
    if not USERNAME_PATTERN.match(username):
        return "Username must be 3–20 characters: letters, numbers, underscores only."
    return None


def validate_password(password: str) -> str | None:
    """Returns an error message, or None if valid."""
    if not password:
        return "Password is required."
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"[0-9]", password):
        return "Password must contain both letters and numbers."
    return None