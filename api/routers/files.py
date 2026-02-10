"""File upload endpoint: accept files for processing."""

import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.deps import get_current_user
from api.models import UserInfo

log = logging.getLogger("jarvis.api.files")

router = APIRouter()
_limiter = Limiter(key_func=get_remote_address)


# MIME types that are allowed (validated against content_type header)
ALLOWED_MIME_PREFIXES = {
    "text/", "application/json", "application/xml", "application/pdf",
    "application/zip", "application/gzip", "application/x-tar",
    "application/vnd.openxmlformats-officedocument",
    "image/png", "image/jpeg", "image/gif", "image/svg+xml",
}

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

# Cross-validation: MIME types that are incompatible with certain extensions
_EXT_MIME_MAP: dict[str, set[str]] = {
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".gif": {"image/gif"},
    ".svg": {"image/svg+xml"},
    ".pdf": {"application/pdf"},
    ".json": {"application/json", "text/json"},
    ".xml": {"application/xml", "text/xml"},
    ".zip": {"application/zip", "application/x-zip-compressed"},
}


@router.post("/upload")
@_limiter.limit("30/hour")
async def upload_file(
    request: Request,
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

    # Validate MIME type if provided
    if file.content_type:
        mime_ok = any(file.content_type.startswith(prefix) for prefix in ALLOWED_MIME_PREFIXES)
        if not mime_ok and file.content_type != "application/octet-stream":
            raise HTTPException(
                status_code=400,
                detail=f"Content type '{file.content_type}' not allowed",
            )
        # Cross-validate MIME against extension for known binary types
        expected_mimes = _EXT_MIME_MAP.get(ext.lower())
        if expected_mimes and file.content_type != "application/octet-stream":
            if file.content_type not in expected_mimes:
                raise HTTPException(
                    status_code=400,
                    detail=f"MIME type '{file.content_type}' does not match extension '{ext}'",
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
    file_path = os.path.normpath(os.path.join(user_dir, safe_name))

    # Final path traversal guard: ensure resolved path stays inside user_dir
    if not file_path.startswith(os.path.normpath(user_dir) + os.sep):
        raise HTTPException(status_code=400, detail="Invalid filename")

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
    try:
        for name in sorted(os.listdir(user_dir)):
            full_path = os.path.join(user_dir, name)
            try:
                stat = os.stat(full_path)
                files.append({
                    "filename": name,
                    "size": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                })
            except OSError:
                continue  # Skip files that can't be stat'd
    except OSError:
        log.exception("Failed to list uploads for user %s", user.id)
        raise HTTPException(status_code=500, detail="Failed to list uploaded files")

    return {"files": files, "count": len(files)}


@router.delete("/uploads/{filename}")
async def delete_upload(
    filename: str,
    user: UserInfo = Depends(get_current_user),
):
    """Delete an uploaded file."""
    # Validate filename (prevent path traversal)
    safe_name = os.path.basename(filename)
    if not safe_name or safe_name != filename or safe_name.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")

    user_dir = os.path.join(UPLOAD_DIR, user.id)
    file_path = os.path.normpath(os.path.join(user_dir, safe_name))

    # Path traversal guard
    if not file_path.startswith(os.path.normpath(user_dir) + os.sep):
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        os.remove(file_path)
    except OSError:
        log.exception("Failed to delete file %s for user %s", filename, user.id)
        raise HTTPException(status_code=500, detail="Failed to delete file")

    log.info("User %s deleted file %s", user.id, filename)
    return {"status": "deleted", "filename": filename}
