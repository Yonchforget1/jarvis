"""Shared conversations router – public read-only links – backed by Supabase."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.db import db
from api.deps import UserInfo, get_current_user

log = logging.getLogger("jarvis.api.share")
router = APIRouter(tags=["share"])


class CreateShareReq(BaseModel):
    session_id: str
    expires_hours: int | None = Field(None, ge=1, le=720)  # Max 30 days


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

    db.insert("shares", {
        "share_id": share_id,
        "session_id": req.session_id,
        "user_id": user.id,
        "username": user.username,
        "title": title,
        "messages": messages,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires_at,
    })

    log.info("Share %s created for session %s by %s", share_id, req.session_id, user.username)
    return {
        "share_id": share_id,
        "url": f"/shared/{share_id}",
        "expires_at": expires_at,
    }


@router.get("/api/share")
async def list_shares(user: UserInfo = Depends(get_current_user)):
    """List all shares created by the current user."""
    rows = db.select(
        "shares",
        filters={"user_id": user.id},
        order="created_at.desc",
    )
    return [
        {
            "share_id": s["share_id"],
            "title": s["title"],
            "created_at": s["created_at"],
            "expires_at": s.get("expires_at"),
            "view_count": s.get("view_count", 0),
        }
        for s in (rows or [])
    ]


@router.delete("/api/share/{share_id}")
async def delete_share(
    share_id: str,
    user: UserInfo = Depends(get_current_user),
):
    """Delete a share link."""
    share = db.select("shares", filters={"share_id": share_id}, single=True)
    if not share or share["user_id"] != user.id:
        raise HTTPException(404, "Share not found")
    db.delete("shares", {"share_id": share_id})
    return {"status": "deleted"}


@router.get("/api/shared/{share_id}")
async def view_shared(share_id: str):
    """View a shared conversation (public, no auth required)."""
    share = db.select("shares", filters={"share_id": share_id}, single=True)
    if not share:
        raise HTTPException(404, "Share not found or expired")

    # Check expiration
    if share.get("expires_at"):
        expires = datetime.fromisoformat(share["expires_at"])
        if datetime.now(timezone.utc) > expires:
            db.delete("shares", {"share_id": share_id})
            raise HTTPException(404, "Share has expired")

    # Increment view count
    new_count = share.get("view_count", 0) + 1
    db.update("shares", {"share_id": share_id}, {"view_count": new_count})

    return {
        "title": share["title"],
        "username": share["username"],
        "messages": share["messages"],
        "created_at": share["created_at"],
        "view_count": new_count,
    }
