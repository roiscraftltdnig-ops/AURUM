import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.rag import ingest_document


async def main() -> None:
    path = ROOT / "knowledge_base" / "aurum_foundation" / "overview.md"
    result = await ingest_document(path.name, path.read_bytes(), "Aurum Foundation", None)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
