import asyncio
import sys

sys.path.insert(0, r"C:\Users\HP\Documents\AY\backend")

from app.db.supabase import supabase


async def main() -> None:
    print("ready", supabase.ready(), supabase.base_url)
    try:
        rows = await supabase.select("users", "limit=1")
        print("users_table_ok", len(rows))
    except Exception as exc:
        print("supabase_error", type(exc).__name__, str(exc)[:300])


asyncio.run(main())
