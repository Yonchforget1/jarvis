"""Supabase database layer – wraps PostgREST REST API via httpx."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("jarvis.api.db")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    log.warning("SUPABASE_URL or SUPABASE_ANON_KEY not set – database features disabled")


def _headers() -> dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _rest_url(table: str) -> str:
    return f"{SUPABASE_URL}/rest/v1/{table}"


class SupabaseDB:
    """Thin wrapper around Supabase PostgREST API."""

    def __init__(self):
        self._client = httpx.Client(timeout=10.0)
        self.available = bool(SUPABASE_URL and SUPABASE_KEY)

    def insert(self, table: str, data: dict | list[dict]) -> list[dict]:
        """Insert one or more rows. Returns inserted rows."""
        if not self.available:
            return []
        try:
            payload = data if isinstance(data, list) else [data]
            r = self._client.post(_rest_url(table), json=payload, headers=_headers())
            r.raise_for_status()
            return r.json()
        except Exception as e:
            log.error("DB insert %s failed: %s", table, e)
            return []

    def select(
        self,
        table: str,
        columns: str = "*",
        filters: dict[str, Any] | None = None,
        order: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        single: bool = False,
    ) -> list[dict] | dict | None:
        """Select rows from a table."""
        if not self.available:
            return None if single else []
        try:
            params: dict[str, str] = {"select": columns}
            headers = _headers()

            # Build PostgREST filter query string
            url = _rest_url(table)
            filter_parts = []
            if filters:
                for key, value in filters.items():
                    if "." in key:
                        # Already has operator like "id.eq"
                        filter_parts.append(f"{key}={value}")
                    else:
                        filter_parts.append(f"{key}=eq.{value}")

            if order:
                params["order"] = order
            if limit:
                params["limit"] = str(limit)
            if offset:
                params["offset"] = str(offset)
            if single:
                headers["Accept"] = "application/vnd.pgrst.object+json"

            # Build URL with filters
            query_parts = [f"{k}={v}" for k, v in params.items()]
            query_parts.extend(filter_parts)
            full_url = f"{url}?{'&'.join(query_parts)}"

            r = self._client.get(full_url, headers=headers)

            if r.status_code == 406 and single:
                return None  # No rows found for single
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 406:
                return None if single else []
            log.error("DB select %s failed: %s", table, e)
            return None if single else []
        except Exception as e:
            log.error("DB select %s failed: %s", table, e)
            return None if single else []

    def update(self, table: str, filters: dict[str, Any], data: dict) -> list[dict]:
        """Update rows matching filters."""
        if not self.available:
            return []
        try:
            url = _rest_url(table)
            filter_parts = []
            for key, value in filters.items():
                if "." in key:
                    filter_parts.append(f"{key}={value}")
                else:
                    filter_parts.append(f"{key}=eq.{value}")

            full_url = f"{url}?{'&'.join(filter_parts)}"
            r = self._client.patch(full_url, json=data, headers=_headers())
            r.raise_for_status()
            return r.json()
        except Exception as e:
            log.error("DB update %s failed: %s", table, e)
            return []

    def delete(self, table: str, filters: dict[str, Any]) -> bool:
        """Delete rows matching filters."""
        if not self.available:
            return False
        try:
            url = _rest_url(table)
            filter_parts = []
            for key, value in filters.items():
                if "." in key:
                    filter_parts.append(f"{key}={value}")
                else:
                    filter_parts.append(f"{key}=eq.{value}")

            full_url = f"{url}?{'&'.join(filter_parts)}"
            r = self._client.delete(full_url, headers=_headers())
            r.raise_for_status()
            return True
        except Exception as e:
            log.error("DB delete %s failed: %s", table, e)
            return False

    def upsert(self, table: str, data: dict | list[dict], on_conflict: str = "") -> list[dict]:
        """Insert or update rows."""
        if not self.available:
            return []
        try:
            payload = data if isinstance(data, list) else [data]
            headers = _headers()
            headers["Prefer"] = "return=representation,resolution=merge-duplicates"
            url = _rest_url(table)
            if on_conflict:
                url += f"?on_conflict={on_conflict}"
            r = self._client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            log.error("DB upsert %s failed: %s", table, e)
            return []

    def count(self, table: str, filters: dict[str, Any] | None = None) -> int:
        """Count rows in a table."""
        if not self.available:
            return 0
        try:
            headers = _headers()
            headers["Prefer"] = "count=exact"
            headers["Range-Unit"] = "items"
            headers["Range"] = "0-0"

            url = _rest_url(table)
            filter_parts = []
            if filters:
                for key, value in filters.items():
                    if "." in key:
                        filter_parts.append(f"{key}={value}")
                    else:
                        filter_parts.append(f"{key}=eq.{value}")

            if filter_parts:
                url += f"?{'&'.join(filter_parts)}"

            r = self._client.get(url, headers=headers)
            r.raise_for_status()
            # Count is in Content-Range header: "0-0/42"
            content_range = r.headers.get("content-range", "")
            if "/" in content_range:
                return int(content_range.split("/")[1])
            return 0
        except Exception as e:
            log.error("DB count %s failed: %s", table, e)
            return 0

    def rpc(self, function_name: str, params: dict | None = None) -> Any:
        """Call a Supabase RPC function."""
        if not self.available:
            return None
        try:
            url = f"{SUPABASE_URL}/rest/v1/rpc/{function_name}"
            r = self._client.post(url, json=params or {}, headers=_headers())
            r.raise_for_status()
            return r.json()
        except Exception as e:
            log.error("DB rpc %s failed: %s", function_name, e)
            return None

    def health_check(self) -> bool:
        """Check if database is reachable."""
        if not self.available:
            return False
        try:
            r = self._client.get(
                f"{SUPABASE_URL}/rest/v1/",
                headers={"apikey": SUPABASE_KEY},
            )
            return r.status_code == 200
        except Exception:
            return False


# Global instance
db = SupabaseDB()
