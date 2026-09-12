# sample_repo/routes.py
# A small API routes file — third investigation target for the demo agent.

from auth import authenticate, verify_token
from db import get_user, create_user, init_db


def handle_login(user_id: str, password: str, db) -> dict:
    """
    POST /login handler.
    Validates credentials and returns a JWT on success.
    """
    token = authenticate(user_id, password, db)
    if token is None:
        return {"error": "Invalid credentials", "status": 401}
    return {"token": token, "status": 200}


def handle_profile(token: str) -> dict:
    """
    GET /profile handler.
    Verifies the JWT and returns the user profile.
    """
    payload = verify_token(token)
    if payload is None:
        return {"error": "Unauthorized — invalid or expired token", "status": 401}

    user_id = payload.get("sub")
    # In a real app, we'd fetch from DB here
    return {"user_id": user_id, "status": 200}


def handle_register(user_id: str, email: str, password: str) -> dict:
    """
    POST /register handler.
    Hashes the password and stores the new user.
    """
    from auth import hash_password
    password_hash, salt = hash_password(password)
    success = create_user(user_id, email, password_hash, salt)
    if not success:
        return {"error": "Email already registered", "status": 409}
    return {"message": "User created successfully", "status": 201}
