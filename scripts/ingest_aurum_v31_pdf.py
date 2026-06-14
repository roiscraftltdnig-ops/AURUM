import asyncio
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import get_settings
from app.services.rag import ingest_document


async def delete_existing_aurum_documents() -> None:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Prefer": "return=minimal",
    }
    url = f"{settings.supabase_url.rstrip('/')}/rest/v1/knowledge_documents?portfolio=eq.Aurum%20Foundation"
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.delete(url, headers=headers)
        response.raise_for_status()


async def main() -> None:
    active_path = ROOT / "knowledge_base" / "aurum_foundation" / "Aurum_Conversation_Knowledge_Base_V3_1.pdf"
    support_path = ROOT / "knowledge_base" / "aurum_foundation" / "Aurum_Conversation_Knowledge_Base_V3.pdf"
    if not active_path.exists():
        raise FileNotFoundError(active_path)
    await delete_existing_aurum_documents()
    active_result = await ingest_document(
        active_path.name,
        active_path.read_bytes(),
        "Aurum Foundation",
        None,
        {
            "resource_key": "aurum_conversation_kb_v31",
            "title": "Aurum Conversation Knowledge Base V3.1",
            "version": "3.1",
            "priority": 100,
            "public": True,
        },
    )
    print({"active": active_result})
    if support_path.exists():
        support_result = await ingest_document(
            support_path.name,
            support_path.read_bytes(),
            "Aurum Foundation",
            None,
            {
                "resource_key": "aurum_conversation_kb_v3",
                "title": "Aurum Conversation Knowledge Base V3",
                "version": "3.0",
                "priority": 80,
                "public": True,
            },
        )
        print({"support": support_result})


if __name__ == "__main__":
    asyncio.run(main())
