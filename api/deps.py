"""FastAPI dependencies (auth, rate limiting)."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.auth import get_user_by_id, verify_token
from api.models import UserInfo

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> UserInfo:
    """Extract and validate user from JWT Bearer token or API key."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token = credentials.credentials

    # Try API key first (prefixed with jrv_)
    if token.startswith("jrv_"):
        from api.main import key_mgr
        api_key = key_mgr.verify_key(token)
        if api_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )
        user = get_user_by_id(api_key.user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key owner not found",
            )
        return UserInfo(
            id=user["id"],
            username=user["username"],
            role=user.get("role", "user"),
        )

    # Fall back to JWT
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return UserInfo(
        id=payload["sub"],
        username=payload["username"],
        role=payload.get("role", "user"),
    )
