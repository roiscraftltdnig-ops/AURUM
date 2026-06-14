from fastapi import APIRouter

router = APIRouter(tags=["public"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "roiscraft-ai-ecosystem"}
