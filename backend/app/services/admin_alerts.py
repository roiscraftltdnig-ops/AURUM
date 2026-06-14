from app.core.config import get_settings
from app.services.telegram import telegram


async def notify_admins(title: str, body: str, exclude_chat_id: str | int | None = None) -> None:
    settings = get_settings()
    text = f"*{title}*\n\n{body}"
    if len(text) > 3900:
        text = text[:3850].rsplit("\n", 1)[0] + "\n\n[Admin summary truncated. Open dashboard for full conversation.]"
    targets = [settings.admin_chat_id, settings.admin_notification_group]
    excluded = str(exclude_chat_id) if exclude_chat_id is not None else None
    for target in [item for item in targets if item]:
        if excluded and str(target) == excluded:
            continue
        try:
            await telegram.send_message(target, text)
        except Exception:
            continue
