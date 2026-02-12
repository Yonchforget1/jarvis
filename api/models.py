"""Pydantic models for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    email: str = ""


class AuthRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = False


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str = "user"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    session_id: str | None = None
    model: str | None = None  # Override model for this conversation


class ChatResponse(BaseModel):
    session_id: str
    response: str
    tool_calls: list[dict] = []


class UserInfo(BaseModel):
    id: str
    username: str
    role: str


class SessionInfo(BaseModel):
    session_id: str
    title: str
    message_count: int
    created_at: str
    last_active: str


class RenameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class SettingsResponse(BaseModel):
    backend: str
    model: str
    max_tokens: int
    system_prompt: str
    available_backends: list[str]


class SettingsUpdateRequest(BaseModel):
    backend: str | None = None
    model: str | None = None
    max_tokens: int | None = None
    system_prompt: str | None = None
    api_key: str | None = None
