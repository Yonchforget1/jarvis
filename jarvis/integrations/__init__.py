"""Jarvis integrations package.

Provides integration routers that can be mounted on the FastAPI app.
"""

from fastapi import FastAPI


def register_integration_routes(app: FastAPI) -> None:
    """Register all integration routes on the given FastAPI app.

    Call this from api/main.py:
        from jarvis.integrations import register_integration_routes
        register_integration_routes(app)
    """
    from jarvis.integrations.voice import router as voice_router
    app.include_router(voice_router, prefix="/api/voice", tags=["voice"])
