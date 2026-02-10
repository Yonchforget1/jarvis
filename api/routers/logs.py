"""Client error logging endpoint.

Receives batched error logs from the frontend and writes them
to the server log so they are visible in production monitoring.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.deps import get_current_user
from api.models import UserInfo

log = logging.getLogger("jarvis.api.client_errors")

router = APIRouter()
_limiter = Limiter(key_func=get_remote_address)


class ClientErrorEntry(BaseModel):
    level: str = Field(pattern="^(error|warn|info)$")
    message: str = Field(max_length=2000)
    component: str = Field(default="unknown", max_length=100)
    pathname: str = Field(default="", max_length=500)
    stack_trace: str | None = Field(default=None, max_length=5000)
    timestamp: str = Field(default="")


class ClientErrorBatch(BaseModel):
    entries: list[ClientErrorEntry] = Field(max_length=25)


@router.post("/logs/client-errors", status_code=202)
@_limiter.limit("10/minute")
async def submit_client_errors(
    request: Request,
    batch: ClientErrorBatch,
    user: UserInfo = Depends(get_current_user),
):
    """Receive batched client-side error logs."""
    for entry in batch.entries:
        log_fn = log.warning if entry.level == "error" else log.info
        log_fn(
            "CLIENT_%s user=%s component=%s path=%s: %s",
            entry.level.upper(),
            user.id,
            entry.component,
            entry.pathname,
            entry.message,
        )
        if entry.stack_trace:
            log.debug("  Stack: %s", entry.stack_trace[:500])
    return {"received": len(batch.entries)}
