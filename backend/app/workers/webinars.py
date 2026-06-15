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
    segment = {**segment, "_webinar_link": link, "_webinar_title": title}

    timezone_label = payload.get("timezone") or payload.get("time_zone") or "UTC"
    reminders = [
        (-1440, f"Hello {{name}}, tomorrow we have a special Aurum educational session: {title}. It is designed to help you understand the products, risks, plans, and next steps clearly. Time zone: {timezone_label}."),
        (-60, f"Hello {{name}}, the Aurum webinar starts in one hour. This is a good session to understand the products, ask questions, and decide what you need clarified before any next step. Access link: {{tracking_link}}"),
        (-45, f"Only 45 minutes to go before the Aurum webinar. Keep your questions ready, especially around EX-AI Bot, plans, withdrawals, and risk. Access link: {{tracking_link}}"),
        (-15, f"We're starting shortly. The Aurum webinar begins in 15 minutes. Here is your access link: {{tracking_link}}"),
        (-5, f"We are live in 5 minutes. Join here when you are ready: {{tracking_link}}"),
        (0, f"We are live now. Join the Aurum webinar here: {{tracking_link}}"),
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
