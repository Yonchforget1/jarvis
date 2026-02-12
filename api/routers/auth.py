"""Auth router – register, login, me."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.auth import authenticate_user, audit_log, create_token, create_user
from api.deps import get_current_user
from api.models import AuthRequest, AuthResponse, RegisterRequest, UserInfo

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, request: Request):
    user = create_user(req.username, req.password, req.email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )
    token = create_token(user)
    audit_log(
        user_id=user["id"],
        username=user["username"],
        action="register",
        ip=request.client.host if request.client else "",
    )
    return AuthResponse(access_token=token, username=user["username"], role=user["role"])


@router.post("/login", response_model=AuthResponse)
async def login(req: AuthRequest, request: Request):
    user = authenticate_user(req.username, req.password)
    if user is None:
        audit_log(
            username=req.username,
            action="login_failed",
            ip=request.client.host if request.client else "",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_token(user, remember_me=req.remember_me)
    audit_log(
        user_id=user["id"],
        username=user["username"],
        action="login",
        ip=request.client.host if request.client else "",
    )
    return AuthResponse(access_token=token, username=user["username"], role=user["role"])


@router.get("/me", response_model=UserInfo)
async def me(user: UserInfo = Depends(get_current_user)):
    return user
