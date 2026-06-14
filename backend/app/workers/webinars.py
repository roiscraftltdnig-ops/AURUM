from datetime import datetime, timedelta, timezone
from typing import Any
from app.db.supabase import supabase


def parse_webinar_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


async def schedule_webinar_campaign(payload: dict[str, Any]) -> dict[str, Any]:
    title = payload.get("title") or "Aurum Webinar"
    starts_at = parse_webinar_time(payload["starts_at"])
    link = payload["link"]
    segment = payload.get("segment") or {"temperature": "all", "stage": "all"}

    reminders = [
        (-60, f"Hello {{name}}, our Aurum webinar begins in one hour. This is a great opportunity to understand the products, ask questions, and learn more."),
        (-45, f"We are getting closer to today's Aurum webinar. We look forward to having you with us."),
        (-15, f"The webinar starts in 15 minutes. Here is your access link: {link}"),
        (0, f"We are live now. Join the Aurum webinar here: {link}"),
        (90, f"Thank you for attending. What part of today's session interested you the most?"),
    ]

    rows = []
    for offset_minutes, body in reminders:
        scheduled_for = starts_at + timedelta(minutes=offset_minutes)
        rows.append({
            "title": f"{title} reminder {offset_minutes:+d}m",
            "body": body,
            "segment": segment,
            "status": "scheduled",
            "scheduled_for": scheduled_for.isoformat(),
        })

    inserted = await supabase.insert("broadcasts", rows)
    return {"scheduled": len(inserted), "broadcasts": inserted}
