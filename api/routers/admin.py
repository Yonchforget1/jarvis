"""Admin router – user management, audit logs, system stats."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from api.auth import get_all_users, get_audit_log as _get_audit_log, get_user_by_id
from api.db import db
from api.deps import get_current_user
from api.models import UserInfo

router = APIRouter(prefix="/api/admin", tags=["admin"])
log = logging.getLogger("jarvis.api.admin")


def _require_admin(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    """Dependency that requires admin role."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


class UpdateUserRequest(BaseModel):
    role: str | None = None


# ---- Users ----

@router.get("/users")
async def list_users(admin: UserInfo = Depends(_require_admin)):
    users = get_all_users()
    return [
        {
            "id": u["id"],
            "username": u["username"],
            "email": u.get("email", ""),
            "role": u.get("role", "user"),
            "created_at": u.get("created_at", ""),
        }
        for u in users
    ]


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    req: UpdateUserRequest,
    admin: UserInfo = Depends(_require_admin),
):
    target = get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    changed = {}
    if req.role is not None:
        if req.role not in ("admin", "user"):
            raise HTTPException(status_code=400, detail="Role must be 'admin' or 'user'")
        # Prevent removing the last admin
        if target["role"] == "admin" and req.role != "admin":
            users = get_all_users()
            admin_count = sum(1 for u in users if u.get("role") == "admin")
            if admin_count <= 1:
                raise HTTPException(status_code=400, detail="Cannot remove the last admin")
        db.update("users", {"id.eq": user_id}, {"role": req.role})
        changed["role"] = req.role

    log.info("Admin %s updated user %s: %s", admin.username, target["username"], changed)
    return {"status": "updated", "changed": changed}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin: UserInfo = Depends(_require_admin),
):
    target = get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent self-deletion
    if target["id"] == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    # Prevent deleting the last admin
    if target.get("role") == "admin":
        users = get_all_users()
        admin_count = sum(1 for u in users if u.get("role") == "admin")
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the last admin")

    db.delete("users", {"id.eq": user_id})
    log.info("Admin %s deleted user %s", admin.username, target["username"])
    return {"status": "deleted", "username": target["username"]}


# ---- Audit ----

@router.get("/audit")
async def get_audit_log(
    admin: UserInfo = Depends(_require_admin),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    entries = _get_audit_log(limit=limit, offset=offset)
    total = db.count("audit_log")
    return {"entries": entries, "total": total}


# ---- System Stats ----

@router.get("/stats")
async def admin_stats(admin: UserInfo = Depends(_require_admin)):
    from api.main import session_mgr, task_runner

    users = get_all_users()
    tasks = list(task_runner.tasks.values())

    return {
        "total_users": len(users),
        "admin_users": sum(1 for u in users if u.get("role") == "admin"),
        "active_sessions": session_mgr.active_session_count,
        "uptime_seconds": round(session_mgr.uptime_seconds, 1),
        "total_tasks": len(tasks),
        "running_tasks": sum(1 for t in tasks if t.status.value == "running"),
        "completed_tasks": sum(1 for t in tasks if t.status.value == "completed"),
        "failed_tasks": sum(1 for t in tasks if t.status.value == "failed"),
    }
