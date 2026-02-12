"""Mock database for testing – in-memory implementation of SupabaseDB interface."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


class MockDB:
    """In-memory mock of api.db.SupabaseDB for testing."""

    def __init__(self):
        self.available = True
        self.tables: dict[str, list[dict]] = {}

    def reset(self):
        self.tables.clear()

    def _matches(self, row: dict, filters: dict) -> bool:
        for key, value in filters.items():
            if ".eq" in key:
                col = key.replace(".eq", "")
                if str(row.get(col, "")) != str(value):
                    return False
            elif "." not in key:
                if str(row.get(key, "")) != str(value):
                    return False
        return True

    def insert(self, table: str, data: dict | list[dict]) -> list[dict]:
        if table not in self.tables:
            self.tables[table] = []
        payload = data if isinstance(data, list) else [data]
        results = []
        for row in payload:
            row = dict(row)  # copy
            if "id" not in row:
                row["id"] = str(uuid.uuid4())
            if "created_at" not in row:
                row["created_at"] = datetime.now(timezone.utc).isoformat()
            self.tables[table].append(row)
            results.append(row)
        return results

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
        rows = list(self.tables.get(table, []))
        if filters:
            rows = [r for r in rows if self._matches(r, filters)]
        if order:
            field = order.split(".")[0]
            reverse = "desc" in order
            rows.sort(key=lambda r: str(r.get(field, "")), reverse=reverse)
        if offset:
            rows = rows[offset:]
        if limit:
            rows = rows[:limit]
        if single:
            return rows[0] if rows else None
        return rows

    def update(self, table: str, filters: dict[str, Any], data: dict) -> list[dict]:
        updated = []
        for row in self.tables.get(table, []):
            if self._matches(row, filters):
                row.update(data)
                updated.append(row)
        return updated

    def delete(self, table: str, filters: dict[str, Any]) -> bool:
        if table not in self.tables:
            return False
        before = len(self.tables[table])
        self.tables[table] = [r for r in self.tables[table] if not self._matches(r, filters)]
        return len(self.tables[table]) < before

    def upsert(self, table: str, data: dict | list[dict], on_conflict: str = "") -> list[dict]:
        if table not in self.tables:
            self.tables[table] = []
        payload = data if isinstance(data, list) else [data]
        results = []
        for row in payload:
            row = dict(row)
            # Check if row with matching conflict key exists
            existing = None
            if on_conflict:
                for existing_row in self.tables[table]:
                    if existing_row.get(on_conflict) == row.get(on_conflict):
                        existing = existing_row
                        break
            if existing:
                existing.update(row)
                results.append(existing)
            else:
                if "id" not in row:
                    row["id"] = str(uuid.uuid4())
                if "created_at" not in row:
                    row["created_at"] = datetime.now(timezone.utc).isoformat()
                self.tables[table].append(row)
                results.append(row)
        return results

    def count(self, table: str, filters: dict[str, Any] | None = None) -> int:
        rows = self.tables.get(table, [])
        if filters:
            rows = [r for r in rows if self._matches(r, filters)]
        return len(rows)

    def rpc(self, function_name: str, params: dict | None = None) -> Any:
        return None

    def health_check(self) -> bool:
        return self.available
