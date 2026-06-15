from typing import Any
from datetime import datetime, timezone
from urllib.parse import quote

from app.core.config import get_settings
from app.db.supabase import supabase
from app.services.telegram import telegram


def segment_query(segment: dict[str, Any]) -> str:
    filters: list[str] = []
    stage = segment.get("stage")
    temperature = segment.get("temperature")
    followup_required = segment.get("followup_required")
    if stage and stage != "all":
        filters.append(f"qualification_stage=eq.{stage}")
    if temperature and temperature != "all":
        filters.append(f"lead_temperature=eq.{temperature}")
    if followup_required is not None:
        filters.append(f"followup_required=eq.{str(bool(followup_required)).lower()}")
    filters.append("order=last_seen_at.desc")
    return "&".join(filters)


async def dispatch_broadcast(broadcast_id: str) -> dict[str, int | str]:
    rows = await supabase.select("broadcasts", f"id=eq.{broadcast_id}", limit=1)
    if not rows:
        return {"broadcast_id": broadcast_id, "sent": 0, "failed": 0, "status": "missing"}

    broadcast = rows[0]
    users = await supabase.select("users", segment_query(broadcast.get("segment") or {}), limit=5000)
    sent = 0
    failed = 0
    for user in users:
        chat_id = user.get("telegram_chat_id")
        if not chat_id:
            continue
        try:
            name = user.get("first_name") or "there"
            body = broadcast["body"].replace("{name}", name)
            body = body.replace("{user_id}", user["id"])
            webinar_link = (broadcast.get("segment") or {}).get("_webinar_link")
            if webinar_link and "{tracking_link}" in body:
                base_url = get_settings().app_base_url.rstrip("/")
                tracking_link = f"{base_url}/webinar/click?broadcast_id={broadcast_id}&user_id={user['id']}&target={quote(webinar_link, safe='')}"
                body = body.replace("{tracking_link}", tracking_link)
            await telegram.send_message(chat_id, body)
            sent += 1
            await supabase.insert("engagement_events", {
                "user_id": user["id"],
                "event_type": "broadcast_sent",
                "event_value": broadcast_id,
                "metadata": {"title": broadcast["title"]},
            })
        except Exception:
            failed += 1

    await supabase.update("broadcasts", {"status": "sent", "sent_at": datetime.now(timezone.utc).isoformat()}, f"id=eq.{broadcast_id}")
    return {"broadcast_id": broadcast_id, "sent": sent, "failed": failed, "status": "sent"}


async def dispatch_due_broadcasts(limit: int = 25) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    rows = await supabase.select("broadcasts", "status=eq.scheduled&order=scheduled_for.asc", limit=limit)
    due = []
    for row in rows:
        scheduled_for = row.get("scheduled_for")
        if not scheduled_for:
            continue
        try:
            parsed = datetime.fromisoformat(scheduled_for.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if parsed <= now:
            due.append(row)

    sent_batches = 0
    failed_batches = 0
    for broadcast in due:
        try:
            await dispatch_broadcast(broadcast["id"])
            sent_batches += 1
        except Exception:
            failed_batches += 1

    return {"due": len(due), "sent_batches": sent_batches, "failed_batches": failed_batches}
