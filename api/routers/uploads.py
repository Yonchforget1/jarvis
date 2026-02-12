"""File upload router – handle file uploads for chat context."""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from api.deps import UserInfo, get_current_user

log = logging.getLogger("jarvis.api.uploads")
router = APIRouter(prefix="/api/uploads", tags=["uploads"])

UPLOAD_DIR = Path(__file__).parent.parent / "data" / "uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
    ".csv", ".html", ".css", ".xml", ".toml", ".ini", ".cfg",
    ".sh", ".bash", ".ps1", ".bat", ".cmd",
    ".c", ".cpp", ".h", ".java", ".go", ".rs", ".rb", ".php",
    ".sql", ".log", ".env", ".gitignore", ".dockerfile",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp",
    ".pdf", ".doc", ".docx",
}


@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    user: UserInfo = Depends(get_current_user),
):
    """Upload a file for use in chat context."""
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type '{ext}' not allowed")

    # Read and check size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, f"File too large (max {MAX_FILE_SIZE // 1024 // 1024}MB)")

    # Store file
    user_dir = UPLOAD_DIR / user.id
    user_dir.mkdir(parents=True, exist_ok=True)

    file_id = uuid.uuid4().hex[:12]
    safe_name = f"{file_id}_{file.filename}"
    file_path = user_dir / safe_name
    file_path.write_bytes(content)

    log.info("File uploaded: %s (%d bytes) by %s", file.filename, len(content), user.username)

    return {
        "file_id": file_id,
        "filename": file.filename,
        "size": len(content),
        "content_type": file.content_type,
    }


@router.get("")
async def list_uploads(user: UserInfo = Depends(get_current_user)):
    """List uploaded files for the current user."""
    user_dir = UPLOAD_DIR / user.id
    if not user_dir.exists():
        return []

    files = []
    for f in sorted(user_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if f.is_file():
            # Extract original name from "{file_id}_{original}"
            parts = f.name.split("_", 1)
            file_id = parts[0]
            original_name = parts[1] if len(parts) > 1 else f.name
            files.append({
                "file_id": file_id,
                "filename": original_name,
                "size": f.stat().st_size,
            })

    return files


@router.delete("/{file_id}")
async def delete_upload(
    file_id: str,
    user: UserInfo = Depends(get_current_user),
):
    """Delete an uploaded file."""
    user_dir = UPLOAD_DIR / user.id
    if not user_dir.exists():
        raise HTTPException(404, "File not found")

    for f in user_dir.iterdir():
        if f.name.startswith(file_id):
            f.unlink()
            return {"status": "deleted"}

    raise HTTPException(404, "File not found")


@router.get("/{file_id}/content")
async def get_file_content(
    file_id: str,
    user: UserInfo = Depends(get_current_user),
):
    """Get the text content of an uploaded file (for chat context injection)."""
    user_dir = UPLOAD_DIR / user.id
    if not user_dir.exists():
        raise HTTPException(404, "File not found")

    for f in user_dir.iterdir():
        if f.name.startswith(file_id):
            ext = f.suffix.lower()
            # Only return text content for text files
            text_exts = {
                ".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
                ".csv", ".html", ".css", ".xml", ".toml", ".ini", ".cfg",
                ".sh", ".bash", ".ps1", ".bat", ".cmd", ".sql", ".log",
                ".c", ".cpp", ".h", ".java", ".go", ".rs", ".rb", ".php",
                ".env", ".gitignore", ".dockerfile",
            }
            if ext not in text_exts:
                raise HTTPException(400, "Cannot read binary file as text")

            try:
                content = f.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                raise HTTPException(500, f"Failed to read file: {e}")

            # Truncate very large files
            if len(content) > 100_000:
                content = content[:100_000] + "\n\n[... truncated at 100K chars ...]"

            return {
                "file_id": file_id,
                "filename": f.name.split("_", 1)[1] if "_" in f.name else f.name,
                "content": content,
                "size": f.stat().st_size,
            }

    raise HTTPException(404, "File not found")
