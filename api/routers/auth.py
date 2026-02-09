"""Auth endpoints: register, login, me."""

from fastapi import APIRouter, Depends, HTTPException, status

from api.auth import authenticate_user, create_token, create_user
from api.deps import get_current_user
from api.models import AuthRequest, AuthResponse, RegisterRequest, UserInfo

router = APIRouter()


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    user = create_user(request.username, request.password, request.email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )
    token = create_token(user)
    return AuthResponse(
        access_token=token,
        user=UserInfo(id=user["id"], username=user["username"], email=user.get("email", "")),
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: AuthRequest):
    user = authenticate_user(request.username, request.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token = create_token(user)
    return AuthResponse(
        access_token=token,
        user=UserInfo(id=user["id"], username=user["username"], email=user.get("email", "")),
    )


@router.get("/me", response_model=UserInfo)
async def me(user: UserInfo = Depends(get_current_user)):
    return user
