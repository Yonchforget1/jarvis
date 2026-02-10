"""FastAPI dependencies for authentication and session management."""

import logging

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.auth import decode_token, get_user_by_id, validate_api_key
from api.models import UserInfo

log = logging.getLogger("jarvis.api.auth")
security = HTTPBearer()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserInfo:
    """Extract and validate JWT token or API key, return current user.

    Supports two authentication methods:
    - JWT bearer token (from /api/auth/login)
    - API key (prefix: jrv_) passed as bearer token
    """
    token = credentials.credentials
    client_ip = request.client.host if request.client else "unknown"

    # Check if it's an API key (starts with jrv_)
    if token.startswith("jrv_"):
        user = validate_api_key(token)
        if user is None:
            log.warning("Invalid API key attempt from ip=%s prefix=%s", client_ip, token[:8])
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )
        return UserInfo(id=user["id"], username=user["username"], email=user.get("email", ""))

    # Otherwise treat as JWT
    payload = decode_token(token)
    if payload is None:
        log.warning("Invalid/expired JWT from ip=%s", client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user = get_user_by_id(payload["sub"])
    if user is None:
        log.warning("JWT valid but user not found: sub=%s ip=%s", payload.get("sub"), client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return UserInfo(id=user["id"], username=user["username"], email=user.get("email", ""))
