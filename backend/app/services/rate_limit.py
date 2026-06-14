import time
from collections import defaultdict, deque
from redis.asyncio import Redis
from app.core.config import get_settings

local_windows: dict[str, deque[float]] = defaultdict(deque)


async def allow_event(key: str, limit: int, window_seconds: int) -> bool:
    settings = get_settings()
    if settings.redis_url:
        try:
            redis = Redis.from_url(settings.redis_url, decode_responses=True)
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, window_seconds)
            await redis.aclose()
            return count <= limit
        except Exception:
            pass

    now = time.time()
    window = local_windows[key]
    while window and window[0] <= now - window_seconds:
        window.popleft()
    if len(window) >= limit:
        return False
    window.append(now)
    return True
