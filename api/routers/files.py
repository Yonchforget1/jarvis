"""File upload endpoint: accept files for processing."""

import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from api.deps import get_current_user
from api.models import UserInfo

log = logging.getLogger("jarvis.api.files")

router = APIRouter()

_session_manager = None

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "uploads")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
    ".csv", ".xml", ".html", ".css", ".sql", ".sh", ".bat",
    ".pdf", ".docx", ".xlsx", ".pptx",
    ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".zip", ".tar", ".gz",
    ".log", ".env", ".cfg", ".ini", ".toml",
}


def set_session_manager(sm):
    global _session_manager
    _session_manager = sm


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user: UserInfo = Depends(get_current_user),
):
    """Upload a file for processing by Jarvis.

    Files are stored in a user-specific directory and can be referenced
    in subsequent chat messages.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Check extension
    _, ext = os.path.splitext(file.filename)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Read file with size limit
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(contents)} bytes, max {MAX_FILE_SIZE})",
        )

    # Save to user-specific directory
    user_dir = os.path.join(UPLOAD_DIR, user.id)
    os.makedirs(user_dir, exist_ok=True)

    # Sanitize filename to prevent path traversal
    base_name = os.path.basename(file.filename)
    if not base_name or base_name.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")
    file_id = str(uuid.uuid4())[:8]
    safe_name = f"{file_id}_{base_name}"
    file_path = os.path.join(user_dir, safe_name)

    try:
        with open(file_path, "wb") as f:
            f.write(contents)
    except OSError as e:
        log.exception("Failed to save uploaded file %s for user %s", file.filename, user.id)
        raise HTTPException(status_code=500, detail="Failed to save file")

    log.info("User %s uploaded %s (%d bytes)", user.id, file.filename, len(contents))
    return {
        "status": "uploaded",
        "filename": file.filename,
        "saved_as": safe_name,
        "size": len(contents),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/uploads")
async def list_uploads(user: UserInfo = Depends(get_current_user)):
    """List all uploaded files for the current user."""
    user_dir = os.path.join(UPLOAD_DIR, user.id)
    if not os.path.isdir(user_dir):
        return {"files": [], "count": 0}

    files = []
    for name in sorted(os.listdir(user_dir)):
        full_path = os.path.join(user_dir, name)
        stat = os.stat(full_path)
        files.append({
            "filename": name,
            "size": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        })

    return {"files": files, "count": len(files)}
