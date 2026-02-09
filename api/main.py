"""Jarvis AI Agent API Server."""

import sys
import os

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.session_manager import SessionManager
from api.routers import auth, chat, tools, stats, learnings, conversation

session_manager = SessionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    session_manager.initialize()

    # Inject session manager into routers that need it
    chat.set_session_manager(session_manager)
    tools.set_session_manager(session_manager)
    stats.set_session_manager(session_manager)
    learnings.set_session_manager(session_manager)
    conversation.set_session_manager(session_manager)

    yield
    session_manager.shutdown()


app = FastAPI(
    title="Jarvis AI Agent API",
    description="API for the Jarvis AI Agent Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(tools.router, prefix="/api", tags=["tools"])
app.include_router(stats.router, prefix="/api", tags=["stats"])
app.include_router(learnings.router, prefix="/api", tags=["learnings"])
app.include_router(conversation.router, prefix="/api/conversation", tags=["conversation"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "jarvis-api"}
