"""Auth endpoints: register, login, me."""

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.audit import audit_log
from pydantic import BaseModel

from api.auth import authenticate_user, create_api_key, create_token, create_user, list_user_api_keys, revoke_api_key
from api.deps import get_current_user
from api.models import AuthRequest, AuthResponse, RegisterRequest, UserInfo

router = APIRouter()


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest, req: Request):
    user = create_user(request.username, request.password, request.email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
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
async def login(request: AuthRequest, req: Request):
    user = authenticate_user(request.username, request.password)
    if user is None:
        audit_log(
            user_id="", username=request.username, action="login_failed",
            ip=req.client.host if req.client else "",
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


@router.get("/me", response_model=UserInfo)
async def me(user: UserInfo = Depends(get_current_user)):
    return user


# --- API Key Management ---

class ApiKeyCreate(BaseModel):
    label: str = "default"


@router.post("/api-keys")
async def create_key(body: ApiKeyCreate, user: UserInfo = Depends(get_current_user)):
    """Create a new API key. The key is only shown once."""
    key = create_api_key(user.id, body.label)
    return {"api_key": key}


@router.get("/api-keys")
async def list_keys(user: UserInfo = Depends(get_current_user)):
    """List all API keys for the current user (prefixes only)."""
    return {"api_keys": list_user_api_keys(user.id)}


@router.delete("/api-keys/{key_id}")
async def delete_key(key_id: str, user: UserInfo = Depends(get_current_user)):
    """Revoke an API key."""
    if not revoke_api_key(user.id, key_id):
        raise HTTPException(status_code=404, detail="API key not found")
    return {"status": "revoked", "key_id": key_id}
