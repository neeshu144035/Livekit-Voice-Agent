from fastapi import APIRouter, HTTPException, Response, Cookie, Depends
from typing import Optional
from backend.constants import AUTH_ADMIN_EMAIL, AUTH_ADMIN_PASSWORD, AUTH_SESSION_COOKIE, AUTH_SECURE_COOKIES, AUTH_SESSION_MAX_AGE
from backend.schemas import LoginRequest
from backend.auth_utils import _create_session_token, _verify_session_token
from backend.logging_config import get_logger, LogContext

logger = get_logger("router_auth")
router = APIRouter(prefix="/api", tags=["auth"])

@router.post("/login")
async def login(payload: LoginRequest, response: Response):
    if not AUTH_ADMIN_PASSWORD:
        logger.error("Authentication not configured")
        raise HTTPException(status_code=503, detail="Authentication is not configured")
    
    email = (payload.email or "").strip().lower()
    logger.info(f"Login attempt for email: {email}")
    
    if not AUTH_ADMIN_EMAIL:
        logger.error("No admin email configured")
        raise HTTPException(status_code=503, detail="Authentication is not configured")
    
    password = payload.password or ""
    
    import hmac
    email_ok = hmac.compare_digest(email, AUTH_ADMIN_EMAIL)
    password_ok = hmac.compare_digest(password, AUTH_ADMIN_PASSWORD)
    
    if not (email_ok and password_ok):
        logger.warning(f"Failed login attempt for email: {email}")
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
    logger.info(f"Login successful for email: {email}")
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
    logger.info("User logged out")
    return {"success": True, "message": "Logged out"}

@router.get("/me")
async def me(session_token: Optional[str] = Cookie(default=None, alias=AUTH_SESSION_COOKIE)):
    user = _verify_session_token(session_token)
    if not user:
        logger.warning("Invalid session token")
        raise HTTPException(status_code=401, detail="Unauthorized")
    logger.info(f"Session validated for user: {user.get('email', 'unknown')}")
    return {"success": True, "user": user}

# Aliases for backward compatibility
@router.post("/login-alias", include_in_schema=False)
async def login_alias(payload: LoginRequest, response: Response):
    return await login(payload, response)

@router.post("/logout-alias", include_in_schema=False)
async def logout_alias(response: Response):
    return await logout(response)

@router.get("/me-alias", include_in_schema=False)
async def me_alias(session_token: Optional[str] = Cookie(default=None, alias=AUTH_SESSION_COOKIE)):
    return await me(session_token)
