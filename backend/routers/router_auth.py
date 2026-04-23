from fastapi import APIRouter, HTTPException, Response, Cookie, Depends
from typing import Optional
from backend.constants import AUTH_ADMIN_EMAIL, AUTH_ADMIN_PASSWORD, AUTH_SESSION_COOKIE, AUTH_SECURE_COOKIES, AUTH_SESSION_MAX_AGE
from backend.schemas import LoginRequest
from backend.auth_utils import _create_session_token, _verify_session_token

router = APIRouter(prefix="/api", tags=["auth"])

@router.post("/login")
async def login(payload: LoginRequest, response: Response):
    if not AUTH_ADMIN_PASSWORD:
        raise HTTPException(status_code=503, detail="Authentication is not configured")
    email = (payload.email or "").strip().lower()
    password = payload.password or ""
    
    import hmac
    email_ok = hmac.compare_digest(email, AUTH_ADMIN_EMAIL)
    password_ok = hmac.compare_digest(password, AUTH_ADMIN_PASSWORD)
    
    if not (email_ok and password_ok):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    session_token = _create_session_token(email)
    response.set_cookie(
        key=AUTH_SESSION_COOKIE,
        value=session_token,
        max_age=AUTH_SESSION_MAX_AGE,
        httponly=True,
        secure=AUTH_SECURE_COOKIES,
        samesite="lax",
        path="/",
    )
    return {
        "success": True,
        "message": "Login successful",
        "user": {"id": 1, "email": email},
        "session_token": session_token,
    }

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key=AUTH_SESSION_COOKIE,
        path="/",
        httponly=True,
        secure=AUTH_SECURE_COOKIES,
        samesite="lax",
    )
    return {"success": True, "message": "Logged out"}

@router.get("/me")
async def me(session_token: Optional[str] = Cookie(default=None, alias=AUTH_SESSION_COOKIE)):
    user = _verify_session_token(session_token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"success": True, "user": user}

# Aliases for backward compatibility
@router.post("/login-alias", include_in_schema=False)
async def login_alias(payload: LoginRequest, response: Response):
    # This is a helper for the main.py redirect logic if needed
    return await login(payload, response)

@router.post("/logout-alias", include_in_schema=False)
async def logout_alias(response: Response):
    return await logout(response)

@router.get("/me-alias", include_in_schema=False)
async def me_alias(session_token: Optional[str] = Cookie(default=None, alias=AUTH_SESSION_COOKIE)):
    return await me(session_token)
