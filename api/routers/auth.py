"""Auth endpoints: register, login, me."""

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.audit import audit_log
from api.auth import authenticate_user, create_token, create_user
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
