"""Shared conversations router – public read-only links."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.deps import UserInfo, get_current_user

log = logging.getLogger("jarvis.api.share")
router = APIRouter(tags=["share"])

_SHARES_DIR = Path(__file__).parent.parent / "data" / "shares"


class CreateShareReq(BaseModel):
    session_id: str
    expires_hours: int | None = Field(None, ge=1, le=720)  # Max 30 days


def _load_shares() -> dict[str, dict]:
    """Load all share records."""
    shares = {}
    _SHARES_DIR.mkdir(parents=True, exist_ok=True)
    for f in _SHARES_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            shares[data["share_id"]] = data
        except Exception:
            pass
    return shares


def _save_share(share: dict) -> None:
    _SHARES_DIR.mkdir(parents=True, exist_ok=True)
    path = _SHARES_DIR / f"{share['share_id']}.json"
    path.write_text(json.dumps(share, indent=2))


def _delete_share(share_id: str) -> None:
    path = _SHARES_DIR / f"{share_id}.json"
    if path.exists():
        path.unlink()


@router.post("/api/share")
async def create_share(
    req: CreateShareReq,
    user: UserInfo = Depends(get_current_user),
):
    """Create a public share link for a conversation."""
    from api.main import session_mgr

    session = session_mgr.get_session(req.session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(404, "Session not found")

    share_id = uuid.uuid4().hex[:16]
    expires_at = None
    if req.expires_hours:
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=req.expires_hours)).isoformat()

    messages = session_mgr.get_session_messages(req.session_id) or []
    title = session.custom_name or session.auto_title or "Shared Conversation"

    share = {
        "share_id": share_id,
        "session_id": req.session_id,
        "user_id": user.id,
        "username": user.username,
        "title": title,
        "messages": messages,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires_at,
        "view_count": 0,
    }
    _save_share(share)

    log.info("Share %s created for session %s by %s", share_id, req.session_id, user.username)
    return {
        "share_id": share_id,
        "url": f"/shared/{share_id}",
        "expires_at": expires_at,
    }


@router.get("/api/share")
async def list_shares(user: UserInfo = Depends(get_current_user)):
    """List all shares created by the current user."""
    shares = _load_shares()
    user_shares = [s for s in shares.values() if s["user_id"] == user.id]
    user_shares.sort(key=lambda s: s["created_at"], reverse=True)
    return [
        {
            "share_id": s["share_id"],
            "title": s["title"],
            "created_at": s["created_at"],
            "expires_at": s.get("expires_at"),
            "view_count": s.get("view_count", 0),
        }
        for s in user_shares
    ]


@router.delete("/api/share/{share_id}")
async def delete_share(
    share_id: str,
    user: UserInfo = Depends(get_current_user),
):
    """Delete a share link."""
    shares = _load_shares()
    share = shares.get(share_id)
    if not share or share["user_id"] != user.id:
        raise HTTPException(404, "Share not found")
    _delete_share(share_id)
    return {"status": "deleted"}


@router.get("/api/shared/{share_id}")
async def view_shared(share_id: str):
    """View a shared conversation (public, no auth required)."""
    path = _SHARES_DIR / f"{share_id}.json"
    if not path.exists():
        raise HTTPException(404, "Share not found or expired")

    share = json.loads(path.read_text())

    # Check expiration
    if share.get("expires_at"):
        expires = datetime.fromisoformat(share["expires_at"])
        if datetime.now(timezone.utc) > expires:
            _delete_share(share_id)
            raise HTTPException(404, "Share has expired")

    # Increment view count
    share["view_count"] = share.get("view_count", 0) + 1
    _save_share(share)

    return {
        "title": share["title"],
        "username": share["username"],
        "messages": share["messages"],
        "created_at": share["created_at"],
        "view_count": share["view_count"],
    }
