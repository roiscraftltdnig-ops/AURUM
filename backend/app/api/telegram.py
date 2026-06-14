from fastapi import APIRouter, Request
from app.telegram.handlers import handle_update

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook")
async def telegram_webhook(request: Request) -> dict:
    return await handle_update(request)
