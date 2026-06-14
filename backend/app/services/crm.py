from datetime import datetime, timezone
from typing import Any
from app.db.supabase import supabase


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_or_create_user(telegram_user: dict[str, Any], chat_id: int) -> dict[str, Any]:
    telegram_id = str(telegram_user.get("id"))
    existing = await supabase.select("users", f"telegram_id=eq.{telegram_id}", limit=1)
    payload = {
        "telegram_id": telegram_id,
        "telegram_chat_id": str(chat_id),
        "telegram_username": telegram_user.get("username"),
        "first_name": telegram_user.get("first_name"),
        "last_name": telegram_user.get("last_name"),
        "last_seen_at": now_iso(),
    }
    if existing:
        return (await supabase.update("users", payload, f"id=eq.{existing[0]['id']}"))[0]
    payload["lead_temperature"] = "COLD"
    payload["qualification_stage"] = "BEGINNER"
    return (await supabase.insert("users", payload))[0]


async def load_memory(user_id: str) -> dict[str, Any]:
    rows = await supabase.select("user_memory", f"user_id=eq.{user_id}", limit=1)
    return rows[0]["memory"] if rows else {}


async def save_memory(user_id: str, memory: dict[str, Any]) -> None:
    await supabase.upsert("user_memory", {"user_id": user_id, "memory": memory, "updated_at": now_iso()}, "user_id")


async def log_message(user_id: str, role: str, text: str, metadata: dict[str, Any] | None = None) -> None:
    await supabase.insert("messages", {"user_id": user_id, "role": role, "content": text, "metadata": metadata or {}})


async def update_user_profile(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    clean_payload = {key: value for key, value in payload.items() if value not in (None, "", [], {})}
    if not clean_payload:
        return {}
    clean_payload["last_seen_at"] = now_iso()
    rows = await supabase.update("users", clean_payload, f"id=eq.{user_id}")
    return rows[0] if rows else clean_payload


async def apply_qualification(user_id: str, current_score: int, qualification: Any) -> int:
    new_score = min(100, current_score + qualification.delta)
    await supabase.update("users", {
        "engagement_score": new_score,
        "qualification_stage": qualification.stage,
        "lead_temperature": qualification.lead_temperature,
        "followup_required": qualification.escalation_required,
    }, f"id=eq.{user_id}")
    await supabase.insert("lead_scores", {
        "user_id": user_id,
        "score": new_score,
        "temperature": qualification.lead_temperature,
        "stage": qualification.stage,
        "reasons": qualification.reasons,
    })
    return new_score


async def create_admin_task(user: dict[str, Any], summary: str, priority: str, recommended_action: str) -> None:
    await supabase.insert("admin_tasks", {
        "user_id": user["id"],
        "title": f"{priority.title()} lead: @{user.get('telegram_username') or user.get('telegram_id')}",
        "summary": summary,
        "priority": priority,
        "recommended_action": recommended_action,
        "status": "open",
    })
