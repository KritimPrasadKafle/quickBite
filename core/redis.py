import redis.asyncio as aioredis
from jose import jwt, JWTError

REDIS_URL = "redis://localhost:6379"

redis_client = aioredis.from_url(REDIS_URL, decode_responses = True)

async def blacklist_token(token: str) -> None:
    """Store token in blacklist until it naturally expires."""

    try:
        payload = jwt.decode(token, key = "", options={"verify_signature": False})
        exp = payload.get("exp")
        if not exp:
            return 
        
        import time
        ttl = int(exp - time.time())
        if ttl > 0:
            await redis_client.setex(f"blacklist:{token}", ttl, "1")
    except JWTError:
        pass

async def is_token_blacklisted(token:str) -> bool:
    """Returns True if token has been blacklisted."""

    result = await redis_client.get(f"blacklist:{token}")
    return result is not None