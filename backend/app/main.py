import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from app.api import admin, auth, public, telegram
from app.core.config import cors_origin_list
from app.services.content_audit import create_missing_resource_tasks
from app.workers.broadcasts import dispatch_due_broadcasts

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


@app.on_event("startup")
async def startup_content_audit() -> None:
    try:
        await create_missing_resource_tasks()
    except Exception:
        pass
    asyncio.create_task(scheduled_broadcast_loop())
