"""API keys router – create, list, and revoke API keys."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.deps import get_current_user
from api.models import UserInfo

router = APIRouter(prefix="/api/keys", tags=["keys"])


class CreateKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100, description="Key name/description")


@router.post("", status_code=201)
async def create_key(
    req: CreateKeyRequest,
    user: UserInfo = Depends(get_current_user),
):
    from api.main import key_mgr

    # Limit keys per user
    existing = key_mgr.get_user_keys(user.id)
    if len(existing) >= 5:
        raise HTTPException(status_code=400, detail="Maximum 5 API keys per user")

    api_key, raw_key = key_mgr.create_key(user.id, req.name)
    return {
        **api_key.to_dict(),
        "key": raw_key,  # Only returned once!
        "warning": "Save this key now — it cannot be retrieved again.",
    }


@router.get("")
async def list_keys(user: UserInfo = Depends(get_current_user)):
    from api.main import key_mgr

    keys = key_mgr.get_user_keys(user.id)
    return [k.to_dict() for k in keys]


@router.delete("/{key_id}")
async def revoke_key(
    key_id: str,
    user: UserInfo = Depends(get_current_user),
):
    from api.main import key_mgr

    # Verify ownership
    key = key_mgr.keys.get(key_id)
    if not key or key.user_id != user.id:
        raise HTTPException(status_code=404, detail="Key not found")

    key_mgr.revoke_key(key_id)
    return {"status": "revoked", "key_id": key_id}
