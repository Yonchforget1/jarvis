"""Pydantic request/response schemas for the Jarvis API."""

from pydantic import BaseModel


# --- Auth ---

class AuthRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str = ""


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
    session_id: str | None = None


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


# --- Conversation ---

class ClearRequest(BaseModel):
    session_id: str


class SessionInfo(BaseModel):
    session_id: str
    created_at: str
    last_active: str
    message_count: int
