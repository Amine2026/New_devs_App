import json
import redis.asyncio as redis
from typing import Dict, Any
import os

# Initialize Redis client (typically configured centrally).
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

async def get_revenue_summary(
    property_id: str,
    tenant_id: str,
    month: int = 3,
    year: int = 2024,
) -> Dict[str, Any]:
    """
    Fetches revenue summary, utilizing tenant-isolated caching to improve performance.
    """
    cache_key = f"revenue:{tenant_id}:{property_id}:{year}:{month:02d}"

    # Try to get from cache
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            cached_data = json.loads(cached)
            if cached_data.get("tenant_id") == tenant_id:
                return cached_data
    except Exception:
        pass

    # Revenue calculation is delegated to the reservation service.
    from app.services.reservations import calculate_total_revenue

    # Calculate revenue
    result = await calculate_total_revenue(property_id, tenant_id, month=month, year=year)

    # Cache the result for 5 minutes under the tenant-isolated key
    try:
        await redis_client.setex(cache_key, 300, json.dumps(result))
    except Exception:
        pass

    return result
