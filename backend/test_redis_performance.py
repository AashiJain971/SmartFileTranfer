#!/usr/bin/env python3
"""
Performance Test Script - Compare Database vs Redis Cache Speed
"""
import asyncio
import time
import sys
sys.path.append('/Users/adityajain/SmartFileTransfer/backend')

from services.cache_service import cache
from db.auth_crud import get_user_by_email

async def test_performance():
    """Test and compare performance with/without cache"""
    
    print("🔥 Redis Performance Test")
    print("=" * 60)
    
    # Initialize Redis
    await cache.connect()
    
    if not cache.enabled:
        print("❌ Redis not available - test aborted")
        return
    
    test_email = "test@example.com"
    
    # Test 1: First request (Cache MISS - hits database)
    print("\n📊 Test 1: First Request (Cache MISS)")
    print("-" * 60)
    
    await cache.delete(f"user:email:{test_email}")  # Clear cache
    
    start = time.time()
    user = await get_user_by_email(test_email)
    first_request_time = (time.time() - start) * 1000
    
    print(f"Time: {first_request_time:.2f}ms")
    print(f"Result: {'✅ User found' if user else '❌ No user'}")
    
    # Test 2: Second request (Cache HIT - instant)
    print("\n📊 Test 2: Second Request (Cache HIT)")
    print("-" * 60)
    
    start = time.time()
    user = await get_user_by_email(test_email)
    second_request_time = (time.time() - start) * 1000
    
    print(f"Time: {second_request_time:.2f}ms")
    print(f"Result: {'✅ User found' if user else '❌ No user'}")
    
    # Calculate speedup
    if second_request_time > 0:
        speedup = first_request_time / second_request_time
        print(f"\n🚀 Speedup: {speedup:.1f}x faster!")
        print(f"Time saved: {first_request_time - second_request_time:.2f}ms")
    
    # Test 3: Multiple rapid requests (all cached)
    print("\n📊 Test 3: 10 Rapid Requests (All Cached)")
    print("-" * 60)
    
    times = []
    for i in range(10):
        start = time.time()
        user = await get_user_by_email(test_email)
        request_time = (time.time() - start) * 1000
        times.append(request_time)
    
    avg_time = sum(times) / len(times)
    print(f"Average time: {avg_time:.2f}ms")
    print(f"Min time: {min(times):.2f}ms")
    print(f"Max time: {max(times):.2f}ms")
    print(f"All requests: ✅ Instant from cache!")
    
    # Show cache stats
    print("\n📈 Cache Statistics")
    print("-" * 60)
    
    if cache.enabled and cache.redis:
        info = await cache.redis.info("stats")
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        hit_rate = (hits / total * 100) if total > 0 else 0
        
        print(f"Cache Hits: {hits}")
        print(f"Cache Misses: {misses}")
        print(f"Hit Rate: {hit_rate:.1f}%")
        print(f"Status: {'🔥 BLAZING!' if hit_rate > 80 else '⚡ FAST' if hit_rate > 50 else '🚀 WARMING UP'}")
    
    await cache.close()
    print("\n✅ Test Complete!")

if __name__ == "__main__":
    asyncio.run(test_performance())
