"""Auth endpoints: register, login, me."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.audit import audit_log
from pydantic import BaseModel

from api.auth import authenticate_user, blacklist_token, change_password, create_api_key, create_token, create_user, list_user_api_keys, revoke_api_key
from api.deps import get_current_user
from api.models import AuthRequest, AuthResponse, RegisterRequest, UserInfo

log = logging.getLogger("jarvis.api.auth")
router = APIRouter()
_limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=AuthResponse)
@_limiter.limit("10/hour")
async def register(request: RegisterRequest, req: Request):
    user = create_user(request.username, request.password, request.email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already taken",
        )
    token = create_token(user)
    audit_log(
        user_id=user["id"], username=user["username"], action="register",
        ip=req.client.host if req.client else "",
    )
    return AuthResponse(
        access_token=token,
        user=UserInfo(id=user["id"], username=user["username"], email=user.get("email", "")),
    )


@router.post("/login", response_model=AuthResponse)
@_limiter.limit("5/minute")
async def login(request: AuthRequest, req: Request):
    user = authenticate_user(request.username, request.password)
    if user is None:
        client_ip = req.client.host if req.client else "unknown"
        log.warning("Failed login attempt for user=%s ip=%s", request.username, client_ip)
        audit_log(
            user_id="", username=request.username, action="login_failed",
            ip=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token = create_token(user)
    audit_log(
        user_id=user["id"], username=user["username"], action="login",
        ip=req.client.host if req.client else "",
    )
    return AuthResponse(
        access_token=token,
        user=UserInfo(id=user["id"], username=user["username"], email=user.get("email", "")),
    )


@router.post("/logout")
async def logout(req: Request, user: UserInfo = Depends(get_current_user)):
    """Logout: blacklist the current JWT token so it can't be reused."""
    auth_header = req.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()
    if token:
        blacklist_token(token)
    audit_log(
        user_id=user.id, username=user.username, action="logout",
        ip=req.client.host if req.client else "",
    )
    return {"status": "logged_out"}


@router.get("/me", response_model=UserInfo)
async def me(user: UserInfo = Depends(get_current_user)):
    return user


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.post("/change-password")
@_limiter.limit("5/hour")
async def change_password_endpoint(
    request: Request,
    body: ChangePasswordRequest,
    user: UserInfo = Depends(get_current_user),
):
    """Change the current user's password."""
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    if body.new_password.isdigit() or body.new_password.isalpha():
        raise HTTPException(status_code=400, detail="Password must contain both letters and numbers")
    if body.old_password == body.new_password:
        raise HTTPException(status_code=400, detail="New password must differ from current password")
    success = change_password(user.id, body.old_password, body.new_password)
    if not success:
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    audit_log(
        user_id=user.id, username=user.username, action="change_password",
        ip=request.client.host if request.client else "",
    )
    return {"status": "password_changed"}


# --- API Key Management ---

class ApiKeyCreate(BaseModel):
    label: str = "default"


@router.post("/api-keys")
@_limiter.limit("5/minute")
async def create_key(request: Request, body: ApiKeyCreate, user: UserInfo = Depends(get_current_user)):
    """Create a new API key. The key is only shown once."""
    key = create_api_key(user.id, body.label)
    audit_log(user_id=user.id, username=user.username, action="api_key_created", detail=f"label={body.label}", ip=request.client.host if request.client else None)
    return {"api_key": key}


@router.get("/api-keys")
@_limiter.limit("10/minute")
async def list_keys(request: Request, user: UserInfo = Depends(get_current_user)):
    """List all API keys for the current user (prefixes only)."""
    return {"api_keys": list_user_api_keys(user.id)}


@router.delete("/api-keys/{key_id}")
@_limiter.limit("5/minute")
async def delete_key(request: Request, key_id: str, user: UserInfo = Depends(get_current_user)):
    """Revoke an API key."""
    if not revoke_api_key(user.id, key_id):
        raise HTTPException(status_code=404, detail="API key not found")
    audit_log(user_id=user.id, username=user.username, action="api_key_revoked", detail=f"key_id={key_id}", ip=request.client.host if request.client else None)
    return {"status": "revoked", "key_id": key_id}
