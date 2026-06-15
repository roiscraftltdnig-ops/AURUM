from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from app.db.supabase import supabase

router = APIRouter(tags=["public"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "roiscraft-ai-ecosystem"}


@router.get("/webinar/click")
async def webinar_click(broadcast_id: str, user_id: str, target: str) -> RedirectResponse:
    if not target.startswith(("https://", "http://")):
        raise HTTPException(status_code=400, detail="Invalid webinar link")
    await supabase.insert("engagement_events", {
        "user_id": user_id,
        "event_type": "webinar_link_clicked",
        "event_value": broadcast_id,
        "metadata": {"target": target},
    })
    return RedirectResponse(target, status_code=302)
