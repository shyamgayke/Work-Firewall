# sample_repo/auth.py
# A small authentication module — used as the demo codebase for Work Firewall.
# The agent investigates this file repeatedly to demonstrate fact reuse.

import hashlib
import hmac
import time
import jwt  # PyJWT (not installed — just for demo reading, not actually run)

SECRET_KEY = "super-secret-key-do-not-expose"
TOKEN_EXPIRY_SECONDS = 3600


def generate_token(user_id: str) -> str:
    """Generate a signed JWT for a given user_id."""
    payload = {
        "sub": user_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_EXPIRY_SECONDS,
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token


def verify_token(token: str) -> dict | None:
    """
    Verify and decode a JWT token.
    Returns the payload dict on success, None if invalid or expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # token expired
    except jwt.InvalidTokenError:
        return None  # tampered or malformed


def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """Hash a password with PBKDF2-HMAC-SHA256. Returns (hash_hex, salt)."""
    if salt is None:
        import os
        salt = os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return dk.hex(), salt


def check_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verify a plain password against a stored hash."""
    computed, _ = hash_password(password, salt)
    return hmac.compare_digest(computed, stored_hash)


def authenticate(user_id: str, password: str, db) -> str | None:
    """
    Full authentication flow:
    1. Look up user in DB
    2. Verify password
    3. Return JWT if valid, None otherwise
    """
    user = db.get_user(user_id)
    if user is None:
        return None
    if not check_password(password, user["password_hash"], user["salt"]):
        return None
    return generate_token(user_id)
