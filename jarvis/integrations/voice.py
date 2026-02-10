"""Voice transcription endpoint for Jarvis.

Accepts audio uploads and returns transcribed text using OpenAI Whisper API
or local whisper model. Falls back gracefully if dependencies unavailable.

Usage:
    from jarvis.integrations.voice import router as voice_router
    app.include_router(voice_router, prefix="/api/voice", tags=["voice"])
"""

import io
import logging
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

log = logging.getLogger("jarvis.voice")

router = APIRouter()

MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 25 MB (Whisper API limit)
ALLOWED_AUDIO_TYPES = {
    "audio/webm", "audio/ogg", "audio/wav", "audio/mp3", "audio/mpeg",
    "audio/mp4", "audio/x-m4a", "audio/flac", "audio/webm;codecs=opus",
}
ALLOWED_EXTENSIONS = {".webm", ".ogg", ".wav", ".mp3", ".m4a", ".flac", ".mp4"}


class TranscriptionResponse(BaseModel):
    text: str
    language: str | None = None
    duration: float | None = None


def _get_whisper_mode() -> str:
    """Determine which Whisper backend to use.

    Priority:
    1. OpenAI Whisper API (if OPENAI_API_KEY set)
    2. Local whisper package (pip install openai-whisper)
    3. Error
    """
    if os.getenv("OPENAI_API_KEY"):
        return "openai_api"
    try:
        import whisper  # noqa: F401
        return "local"
    except ImportError:
        pass
    # Also check for ANTHROPIC_API_KEY + openai key in .env
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("OPENAI_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                if key:
                    os.environ["OPENAI_API_KEY"] = key
                    return "openai_api"
    return "none"


async def _transcribe_openai_api(audio_bytes: bytes, filename: str) -> TranscriptionResponse:
    """Transcribe using OpenAI Whisper API."""
    try:
        from openai import OpenAI
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="OpenAI package not installed. Run: pip install openai",
        )

    client = OpenAI()

    # Write to temp file (API needs file-like object with name)
    suffix = Path(filename).suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as audio_file:
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
            )
        return TranscriptionResponse(
            text=result.text.strip(),
            language=getattr(result, "language", None),
            duration=getattr(result, "duration", None),
        )
    finally:
        os.unlink(tmp_path)


async def _transcribe_local(audio_bytes: bytes, filename: str) -> TranscriptionResponse:
    """Transcribe using local whisper model."""
    try:
        import whisper
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Whisper not installed. Run: pip install openai-whisper",
        )

    suffix = Path(filename).suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        model = whisper.load_model("base")
        result = model.transcribe(tmp_path)
        return TranscriptionResponse(
            text=result["text"].strip(),
            language=result.get("language"),
            duration=result.get("duration"),
        )
    finally:
        os.unlink(tmp_path)


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(..., description="Audio file to transcribe"),
):
    """Transcribe an audio file to text using Whisper.

    Accepts audio in webm, ogg, wav, mp3, m4a, or flac format.
    Maximum file size: 25 MB.

    Returns the transcribed text, detected language, and audio duration.
    """
    # Validate file extension
    filename = audio.filename or "recording.webm"
    ext = Path(filename).suffix.lower()
    if ext and ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {ext}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Read and validate size
    audio_bytes = await audio.read()
    if len(audio_bytes) > MAX_AUDIO_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Audio file too large ({len(audio_bytes) / 1024 / 1024:.1f} MB). Maximum: 25 MB.",
        )

    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")

    log.info("Transcribing audio: %s (%d bytes)", filename, len(audio_bytes))

    # Determine backend and transcribe
    mode = _get_whisper_mode()
    if mode == "openai_api":
        return await _transcribe_openai_api(audio_bytes, filename)
    elif mode == "local":
        return await _transcribe_local(audio_bytes, filename)
    else:
        raise HTTPException(
            status_code=503,
            detail=(
                "No Whisper backend available. Either:\n"
                "1. Set OPENAI_API_KEY in .env for cloud transcription, or\n"
                "2. Install local whisper: pip install openai-whisper"
            ),
        )


@router.get("/status")
async def voice_status():
    """Check voice transcription availability."""
    mode = _get_whisper_mode()
    return {
        "available": mode != "none",
        "backend": mode,
        "max_size_mb": MAX_AUDIO_SIZE / 1024 / 1024,
        "supported_formats": sorted(ALLOWED_EXTENSIONS),
    }
