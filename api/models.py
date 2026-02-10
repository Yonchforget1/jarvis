"""Pydantic request/response schemas for the Jarvis API."""

import re

from pydantic import BaseModel, Field, field_validator

MAX_MESSAGE_LENGTH = 50_000  # Characters

# Patterns that could indicate script injection in chat messages
_SCRIPT_PATTERNS = re.compile(
    r"<script[^>]*>|</script>|javascript:|on\w+\s*=\s*[\"']",
    re.IGNORECASE,
)

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")


# --- Auth ---

class AuthRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=128)
    email: str = ""

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not _USERNAME_RE.match(v):
            raise ValueError("Username may only contain letters, numbers, underscores, hyphens, and periods.")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if v and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Invalid email address.")
        return v


class UserInfo(BaseModel):
    id: str
    username: str
    email: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo


# --- Chat ---

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = Field(default=None, max_length=64)

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("session_id may only contain letters, numbers, underscores, and hyphens.")
        return v

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if len(v) > MAX_MESSAGE_LENGTH:
            raise ValueError(f"Message too long ({len(v)} chars, max {MAX_MESSAGE_LENGTH}).")
        if not v.strip():
            raise ValueError("Message cannot be empty.")
        # Strip null bytes that could cause issues downstream
        v = v.replace("\x00", "")
        # Strip dangerous HTML tags that could cause XSS when rendered
        # Script tags, event handlers on HTML elements
        v = re.sub(r"<script[^>]*>.*?</script>", "[script removed]", v, flags=re.IGNORECASE | re.DOTALL)
        v = re.sub(r"<(iframe|object|embed|applet|form)[^>]*>.*?</\1>", "[removed]", v, flags=re.IGNORECASE | re.DOTALL)
        v = re.sub(r"<(iframe|object|embed|applet|form)[^>]*/?>", "[removed]", v, flags=re.IGNORECASE)
        return v


class ToolCallDetail(BaseModel):
    id: str
    name: str
    args: dict
    result: str


class ChatResponse(BaseModel):
    session_id: str
    response: str
    tool_calls: list[ToolCallDetail]
    timestamp: str


# --- Tools ---

class ToolInfo(BaseModel):
    name: str
    description: str
    parameters: dict
    category: str


class ToolsResponse(BaseModel):
    tools: list[ToolInfo]
    count: int


# --- Stats ---

class StatsResponse(BaseModel):
    backend: str
    model: str
    tool_count: int
    learnings_count: int
    active_sessions: int
    uptime_seconds: float
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tool_calls: int = 0
    total_messages: int = 0
    avg_tokens_per_message: float = 0


# --- Learnings ---

class LearningEntry(BaseModel):
    timestamp: str
    category: str
    insight: str
    context: str
    task_description: str


class LearningsResponse(BaseModel):
    learnings: list[LearningEntry]
    count: int
    total: int
    page: int
    page_size: int


# --- Conversation ---

class ClearRequest(BaseModel):
    session_id: str


class BulkDeleteRequest(BaseModel):
    session_ids: list[str] = Field(min_length=1, max_length=50)

    @field_validator("session_ids")
    @classmethod
    def validate_session_ids(cls, v: list[str]) -> list[str]:
        for sid in v:
            if not re.match(r"^[a-zA-Z0-9_-]+$", sid):
                raise ValueError(f"Invalid session_id format: {sid}")
        return v


class SessionInfo(BaseModel):
    session_id: str
    created_at: str
    last_active: str
    message_count: int
