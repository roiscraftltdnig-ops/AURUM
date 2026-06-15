import asyncio
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from app.api import admin, auth, public, telegram
from app.core.config import cors_origin_list
from app.services.content_audit import create_missing_resource_tasks
from app.workers.broadcasts import dispatch_due_broadcasts
from app.core.config import get_settings
from app.workers.reports import send_daily_report_to_admins

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="ROISCRAFT AI Ecosystem OS", version="1.0.0")
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(telegram.router)


async def scheduled_broadcast_loop() -> None:
    while True:
        try:
            await dispatch_due_broadcasts()
        except Exception:
            pass
        await asyncio.sleep(60)


async def scheduled_daily_report_loop() -> None:
    sent_dates: set[str] = set()
    settings = get_settings()
    while True:
        try:
            now = datetime.now(timezone.utc)
            today = now.date().isoformat()
            if now.hour == settings.daily_report_hour_utc and today not in sent_dates:
                await send_daily_report_to_admins()
                sent_dates.add(today)
        except Exception:
            pass
        await asyncio.sleep(300)


@app.on_event("startup")
async def startup_content_audit() -> None:
    try:
        await create_missing_resource_tasks()
    except Exception:
        pass
    asyncio.create_task(scheduled_broadcast_loop())
    asyncio.create_task(scheduled_daily_report_loop())
