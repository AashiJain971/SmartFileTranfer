"""
Centralized Cache Invalidation Logic
Ensures data consistency when updates occur
"""
from services.cache_service import cache

class CacheInvalidator:
    """Centralized cache invalidation logic"""
    
    @staticmethod
    async def invalidate_user(user_id: str):
        """Invalidate all user-related caches"""
        await cache.delete(f"user:{user_id}")
        await cache.delete_pattern(f"user:email:*")
        await cache.delete_pattern(f"rooms:{user_id}*")
        await cache.delete_pattern(f"membership:{user_id}:*")
    
    @staticmethod
    async def invalidate_room(room_id: str):
        """Invalidate all room-related caches"""
        await cache.delete_pattern(f"messages:{room_id}:*")
        await cache.delete_pattern(f"members:{room_id}")
        await cache.delete_pattern(f"membership:*:{room_id}")
    
    @staticmethod
    async def invalidate_room_messages(room_id: str):
        """Invalidate only message caches for a room"""
        await cache.delete_pattern(f"messages:{room_id}:*")
    
    @staticmethod
    async def invalidate_membership(user_id: str, room_id: str):
        """Invalidate specific membership cache"""
        await cache.delete(f"membership:{user_id}:{room_id}")
        await cache.delete_pattern(f"rooms:{user_id}*")

# Global invalidator instance
invalidator = CacheInvalidator()
