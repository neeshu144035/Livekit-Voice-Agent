import hmac
import hashlib
import time
import secrets
from typing import Optional, Dict, Any
from backend.constants import AUTH_SESSION_SECRET, AUTH_SESSION_MAX_AGE

def _create_session_token(email: str) -> str:
    now = int(time.time())
    nonce = secrets.token_urlsafe(12)
    payload = f"{email}:{now}:{nonce}"
    signature = hmac.new(
        AUTH_SESSION_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}:{signature}"

def _verify_session_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    parts = token.split(":")
    if len(parts) != 4:
        return None
    email, issued_at_raw, nonce, signature = parts
    payload = f"{email}:{issued_at_raw}:{nonce}"
    expected_signature = hmac.new(
        AUTH_SESSION_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        return None
    try:
        issued_at = int(issued_at_raw)
    except ValueError:
        return None
    age_seconds = int(time.time()) - issued_at
    if age_seconds < 0 or age_seconds > AUTH_SESSION_MAX_AGE:
        return None
    return {"id": 1, "email": email}
