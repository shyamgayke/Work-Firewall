# sample_repo/middleware.py
"""
Rate limiting and request validation middleware.
Sits between incoming HTTP requests and the route handlers.
"""

import time
import hashlib
from functools import wraps
from typing import Callable, Optional

# In-memory rate limit store: {client_id: [timestamps]}
_request_log: dict[str, list[float]] = {}

RATE_LIMIT_REQUESTS = 100    # max requests per window
RATE_LIMIT_WINDOW_S = 60     # window in seconds


def rate_limit(client_id: str) -> bool:
    """
    Check if a client has exceeded the rate limit.
    Returns True if allowed, False if rate-limited.
    """
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW_S

    # Clean old entries
    _request_log[client_id] = [
        ts for ts in _request_log.get(client_id, []) if ts > window_start
    ]

    if len(_request_log[client_id]) >= RATE_LIMIT_REQUESTS:
        return False  # rate limited

    _request_log[client_id].append(now)
    return True


def require_api_key(f: Callable) -> Callable:
    """
    Decorator: validates X-API-Key header against a known set.
    Hashes keys before comparison (constant-time).
    """
    VALID_KEY_HASHES = {
        hashlib.sha256(b"sk-dev-test-key-12345").hexdigest(),
        hashlib.sha256(b"sk-prod-key-abcde").hexdigest(),
    }

    @wraps(f)
    def wrapper(*args, api_key: Optional[str] = None, **kwargs):
        if not api_key:
            return {"error": "Missing X-API-Key header", "status": 401}
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        if key_hash not in VALID_KEY_HASHES:
            return {"error": "Invalid API key", "status": 403}
        return f(*args, **kwargs)

    return wrapper


def sanitize_input(data: dict) -> dict:
    """
    Strip dangerous characters from string values in a dict.
    Prevents basic injection attacks.
    """
    clean = {}
    for k, v in data.items():
        if isinstance(v, str):
            # Remove null bytes and control chars
            clean[k] = "".join(c for c in v if ord(c) >= 32)
        else:
            clean[k] = v
    return clean


def log_request(client_id: str, endpoint: str, method: str = "GET"):
    """Structured request logging."""
    print(f"[{time.strftime('%H:%M:%S')}] {method} {endpoint} from {client_id}")
