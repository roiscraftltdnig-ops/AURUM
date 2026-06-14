import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.rag import ingest_document


async def main() -> None:
    config_path = ROOT / "config" / "knowledge_resources.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    uploaded_by = "local-seed"
    total = 0
    for resource in config["resources"]:
        path = ROOT / resource["path"]
        if not path.exists():
            print(f"missing {path}")
            continue
        content = path.read_bytes()
        result = await ingest_document(path.name, content, resource["portfolio"], uploaded_by)
        print(f"ingested {resource['key']}: {result}")
        total += 1
    print(f"completed {total} resources")


if __name__ == "__main__":
    asyncio.run(main())
