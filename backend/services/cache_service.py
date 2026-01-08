"""
Redis Cache Service for Lightning-Fast Performance
Provides caching layer to eliminate database bottlenecks
"""
import redis.asyncio as redis
import json
from typing import Optional, Any
import os
from datetime import timedelta

class CacheService:
    """High-performance Redis caching layer"""
    
    def __init__(self):
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis = None
        self.redis_url = redis_url
        self.default_ttl = 300  # 5 minutes
        self.enabled = True
        
    async def connect(self):
        """Initialize Redis connection"""
        try:
            self.redis = await redis.from_url(
                self.redis_url,
                decode_responses=True,
                encoding='utf-8',
                socket_connect_timeout=5,
                socket_timeout=5
            )
            await self.redis.ping()
            print("✅ Redis cache connected")
            self.enabled = True
        except Exception as e:
            print(f"⚠️  Redis unavailable (caching disabled): {e}")
            self.enabled = False
    
    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            print("✅ Redis connection closed")
        
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        if not self.enabled or not self.redis:
            return None
        try:
            value = await self.redis.get(key)
            if value:
                print(f"🔥 Cache HIT: {key}")
                return json.loads(value)
            print(f"❄️  Cache MISS: {key}")
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = None):
        """Set cached value with TTL"""
        if not self.enabled or not self.redis:
            return
        try:
            await self.redis.setex(
                key,
                ttl or self.default_ttl,
                json.dumps(value, default=str)
            )
            print(f"💾 Cache SET: {key} (TTL: {ttl or self.default_ttl}s)")
        except Exception as e:
            print(f"Cache set error: {e}")
    
    async def delete(self, key: str):
        """Delete cached value"""
        if not self.enabled or not self.redis:
            return
        try:
            await self.redis.delete(key)
            print(f"🗑️  Cache DELETE: {key}")
        except Exception as e:
            print(f"Cache delete error: {e}")
    
    async def delete_pattern(self, pattern: str):
        """Delete all keys matching pattern"""
        if not self.enabled or not self.redis:
            return
        try:
            cursor = 0
            count = 0
            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
                if keys:
                    await self.redis.delete(*keys)
                    count += len(keys)
                if cursor == 0:
                    break
            print(f"🗑️  Cache DELETE PATTERN: {pattern} ({count} keys)")
        except Exception as e:
            print(f"Cache delete pattern error: {e}")
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.enabled or not self.redis:
            return False
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            print(f"Cache exists error: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        if not self.enabled or not self.redis:
            return 0
        try:
            return await self.redis.incrby(key, amount)
        except Exception as e:
            print(f"Cache increment error: {e}")
            return 0
    
    async def expire(self, key: str, seconds: int):
        """Set expiration on existing key"""
        if not self.enabled or not self.redis:
            return
        try:
            await self.redis.expire(key, seconds)
        except Exception as e:
            print(f"Cache expire error: {e}")

# Global cache instance
cache = CacheService()
