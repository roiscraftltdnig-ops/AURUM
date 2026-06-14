from typing import Any
from uuid import uuid4
import httpx
from app.core.config import get_settings


class SupabaseClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.supabase_url.rstrip("/")
        self.headers = {
            "apikey": self.settings.supabase_service_role_key,
            "Authorization": f"Bearer {self.settings.supabase_service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def ready(self) -> bool:
        return bool(self.base_url and self.settings.supabase_service_role_key)

    async def select(self, table: str, query: str = "", limit: int | None = None) -> list[dict[str, Any]]:
        if not self.ready():
            return []
        suffix = f"?{query}" if query else ""
        if limit is not None:
            suffix += ("&" if suffix else "?") + f"limit={limit}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{self.base_url}/rest/v1/{table}{suffix}", headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def insert(self, table: str, payload: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not self.ready():
            rows = payload if isinstance(payload, list) else [payload]
            return [{**row, "id": str(uuid4())} for row in rows]
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(f"{self.base_url}/rest/v1/{table}", headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def upsert(self, table: str, payload: dict[str, Any] | list[dict[str, Any]], on_conflict: str = "") -> list[dict[str, Any]]:
        if not self.ready():
            rows = payload if isinstance(payload, list) else [payload]
            return [{**row, "id": row.get("id") or str(uuid4())} for row in rows]
        headers = {**self.headers, "Prefer": "resolution=merge-duplicates,return=representation"}
        suffix = f"?on_conflict={on_conflict}" if on_conflict else ""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(f"{self.base_url}/rest/v1/{table}{suffix}", headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def update(self, table: str, payload: dict[str, Any], query: str) -> list[dict[str, Any]]:
        if not self.ready():
            return [{**payload, "id": str(uuid4())}]
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.patch(f"{self.base_url}/rest/v1/{table}?{query}", headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def rpc(self, function: str, payload: dict[str, Any]) -> Any:
        if not self.ready():
            if function == "dashboard_metrics":
                return {"total_users": 0, "active_users": 0, "hot_leads": 0, "open_tasks": 0, "vip_requests": 0, "documents": 0, "broadcasts": 0}
            return []
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{self.base_url}/rest/v1/rpc/{function}", headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()


supabase = SupabaseClient()
