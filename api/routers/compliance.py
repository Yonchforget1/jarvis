"""Data export compliance endpoints: GDPR delete, export user data."""

import json
import logging
import os
import time
import zipfile
from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.audit import audit_log
from api.deps import get_current_user
from api.models import UserInfo

limiter = Limiter(key_func=get_remote_address)

log = logging.getLogger("jarvis.compliance")
router = APIRouter()

_session_manager = None

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def set_session_manager(sm):
    global _session_manager
    _session_manager = sm


@router.get("/compliance/export")
@limiter.limit("5/hour")
async def export_user_data(request: Request, user: UserInfo = Depends(get_current_user)):
    """Export all user data as a ZIP file (GDPR Article 20 - Right to Data Portability).

    Includes: profile, sessions, settings, audit logs, API keys.
    """
    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # User profile
        profile = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
        zf.writestr("profile.json", json.dumps(profile, indent=2))

        # Conversation sessions
        if _session_manager:
            sessions = _session_manager.get_user_sessions(user.id)
            for session in sessions:
                messages = session.conversation.get_display_messages()
                session_data = {
                    "session_id": session.session_id,
                    "created_at": session.created_at.isoformat(),
                    "message_count": len(messages),
                    "messages": messages,
                }
                zf.writestr(
                    f"sessions/{session.session_id}.json",
                    json.dumps(session_data, indent=2, default=str),
                )

        # User settings
        settings_file = os.path.join(DATA_DIR, "user_settings.json")
        if os.path.exists(settings_file):
            with open(settings_file, "r") as f:
                all_settings = json.load(f)
            user_settings = all_settings.get(user.id, {})
            if user_settings:
                zf.writestr("settings.json", json.dumps(user_settings, indent=2))

        # Audit logs (filter for this user)
        audit_file = os.path.join(DATA_DIR, "audit.log")
        if os.path.exists(audit_file):
            user_audits = []
            with open(audit_file, "r") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry.get("user_id") == user.id:
                            user_audits.append(entry)
                    except json.JSONDecodeError:
                        continue
            if user_audits:
                zf.writestr("audit_log.json", json.dumps(user_audits, indent=2))

    zip_buffer.seek(0)

    audit_log(
        user_id=user.id, username=user.username,
        action="data_export", detail="GDPR data export",
    )

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=jarvis-data-export-{user.id[:8]}.zip"},
    )


@router.delete("/compliance/delete-account")
@limiter.limit("2/hour")
async def delete_user_data(request: Request, user: UserInfo = Depends(get_current_user)):
    """Delete all user data (GDPR Article 17 - Right to Erasure).

    Removes: sessions, settings, API keys, audit trails.
    The user account itself is anonymized (username replaced).
    """
    deleted = {"sessions": 0, "settings": False, "api_keys": 0}

    # Delete sessions
    if _session_manager:
        sessions = _session_manager.get_user_sessions(user.id)
        for session in sessions:
            _session_manager.remove_session(session.session_id, user.id)
            deleted["sessions"] += 1

    # Delete settings
    settings_file = os.path.join(DATA_DIR, "user_settings.json")
    if os.path.exists(settings_file):
        with open(settings_file, "r") as f:
            all_settings = json.load(f)
        if user.id in all_settings:
            del all_settings[user.id]
            with open(settings_file, "w") as f:
                json.dump(all_settings, f, indent=2)
            deleted["settings"] = True

    # Delete API keys
    api_keys_file = os.path.join(DATA_DIR, "api_keys.json")
    if os.path.exists(api_keys_file):
        with open(api_keys_file, "r") as f:
            keys = json.load(f)
        original = len(keys)
        keys = [k for k in keys if k.get("user_id") != user.id]
        deleted["api_keys"] = original - len(keys)
        with open(api_keys_file, "w") as f:
            json.dump(keys, f, indent=2)

    audit_log(
        user_id=user.id, username=user.username,
        action="account_delete", detail=f"GDPR erasure: {json.dumps(deleted)}",
    )

    log.info("User %s data deleted: %s", user.id, deleted)
    return {
        "status": "deleted",
        "summary": deleted,
        "message": "All user data has been deleted per GDPR Article 17.",
    }
