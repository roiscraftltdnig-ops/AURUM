import csv
from io import StringIO
from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from app.core.security import require_admin
from app.db.supabase import supabase
from app.services.admin_alerts import notify_admins
from app.services.content_audit import audit_required_resources
from app.services.rag import ingest_document
from app.services.telegram import telegram
from app.core.config import get_settings
from app.workers.broadcasts import dispatch_broadcast
from app.workers.reports import generate_daily_report
from app.workers.webinars import schedule_webinar_campaign

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/metrics")
async def metrics() -> dict:
    dashboard = await supabase.rpc("dashboard_metrics", {})
    return dashboard if isinstance(dashboard, dict) else {"metrics": dashboard}


@router.get("/content-audit")
async def content_audit() -> dict:
    return await audit_required_resources()


@router.get("/users")
async def users(stage: str | None = None, temperature: str | None = None) -> list[dict]:
    filters = []
    if stage:
        filters.append(f"qualification_stage=eq.{stage}")
    if temperature:
        filters.append(f"lead_temperature=eq.{temperature}")
    query = "&".join(filters) + ("&" if filters else "") + "order=last_seen_at.desc"
    return await supabase.select("users", query, limit=200)


@router.get("/users/export.csv")
async def export_users() -> StreamingResponse:
    rows = await supabase.select("users", "order=last_seen_at.desc", limit=5000)
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=[
        "telegram_id", "telegram_username", "first_name", "last_name", "email", "phone_number",
        "country", "qualification_stage", "lead_temperature", "engagement_score", "followup_required",
        "last_seen_at", "created_at"
    ])
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key) for key in writer.fieldnames})
    buffer.seek(0)
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=roiscraft-users.csv"})


@router.get("/users/{user_id}/messages")
async def user_messages(user_id: str) -> list[dict]:
    return await supabase.select("messages", f"user_id=eq.{user_id}&order=created_at.asc", limit=500)


@router.post("/users/{user_id}/notes")
async def add_user_note(user_id: str, payload: dict, admin=Depends(require_admin)) -> list[dict]:
    return await supabase.insert("admin_logs", {
        "admin_id": admin["sub"],
        "action": "user_note",
        "metadata": {"user_id": user_id, "note": payload.get("note", ""), "priority": payload.get("priority")},
    })


@router.get("/tasks")
async def tasks(status: str = "open") -> list[dict]:
    return await supabase.select("admin_tasks", f"status=eq.{status}&order=created_at.desc", limit=200)


@router.patch("/tasks/{task_id}")
async def update_task(task_id: str, payload: dict) -> list[dict]:
    return await supabase.update("admin_tasks", payload, f"id=eq.{task_id}")


@router.post("/documents")
async def upload_document(file: UploadFile = File(...), portfolio: str = Form("ROISCRAFT"), admin=Depends(require_admin)) -> dict:
    content = await file.read()
    return await ingest_document(file.filename or "document", content, portfolio, admin["sub"])


@router.post("/community-groups")
async def upsert_group(payload: dict) -> list[dict]:
    return await supabase.upsert("community_groups", payload, "key")


@router.get("/community-groups")
async def list_groups() -> list[dict]:
    return await supabase.select("community_groups", "order=portfolio.asc,label.asc", limit=500)


@router.post("/broadcasts")
async def create_broadcast(payload: dict) -> dict:
    rows = await supabase.insert("broadcasts", payload)
    return rows[0]


@router.post("/broadcasts/{broadcast_id}/dispatch")
async def dispatch_broadcast_now(broadcast_id: str) -> dict:
    result = await dispatch_broadcast(broadcast_id)
    await notify_admins("Broadcast dispatched", f"Broadcast {broadcast_id} sent to {result['sent']} Telegram users.")
    return result


@router.post("/webinars/schedule")
async def schedule_webinar(payload: dict) -> dict:
    return await schedule_webinar_campaign(payload)


@router.post("/reports/daily")
async def daily_report() -> dict:
    report = await generate_daily_report()
    await notify_admins("Daily ROISCRAFT intelligence report", report["telegram_text"])
    return report


@router.post("/telegram/webhook")
async def set_telegram_webhook() -> dict:
    settings = get_settings()
    return await telegram.set_webhook(f"{settings.app_base_url.rstrip('/')}/telegram/webhook", settings.telegram_webhook_secret)
