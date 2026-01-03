from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import asyncio
from contextlib import asynccontextmanager
import time
import logging
import os
from pathlib import Path

# Load environment variables FIRST before any imports that need them
from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
print(f"🔍 Loading .env from: {env_path}")
print(f"🔍 .env exists: {env_path.exists()}")
load_dotenv(dotenv_path=env_path, override=True)

# Debug: Check if Pinata keys are loaded
print(f"🔍 PINATA_API_KEY loaded: {os.getenv('PINATA_API_KEY')[:10] + '...' if os.getenv('PINATA_API_KEY') else 'NOT SET'}")
print(f"🔍 PINATA_SECRET_KEY loaded: {os.getenv('PINATA_SECRET_KEY')[:10] + '...' if os.getenv('PINATA_SECRET_KEY') else 'NOT SET'}")

from routers import upload
from routers import websocket  # Add WebSocket router
from routers import auth  # Add auth router
from routers import chat  # ✅ ADD CHAT ROUTER
from services.chunk_service import chunk_service
from services.network_predictor import AdaptiveNetworkPredictor
from db.crud import cleanup_failed_sessions
from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global AI predictor instance (persists across requests, learns over time)
network_ai = AdaptiveNetworkPredictor()

# AI confidence threshold for using predictions (0.0 - 1.0)
# ✅ Lowered from 0.7 to 0.5 for faster AI adoption (50% confidence is reasonable)
AI_CONFIDENCE_THRESHOLD = 0.5

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting Smart File Transfer Backend...")
    
    # Initialize Redis cache FIRST for maximum speed
    try:
        from services.cache_service import cache
        await cache.connect()
        print("✅ Redis cache initialized - SPEED BOOST ACTIVE!")
    except Exception as e:
        print(f"⚠️  Redis unavailable (will work without cache): {e}")
    
    # Warm up database connections
    try:
        from db.auth_crud import warm_up_database_connections
        success = await warm_up_database_connections()
        if not success:
            print("⚠️  Database unavailable - server will run in LIMITED MODE")
            print("   💡 File uploads will work, but no auth/chat/persistence")
            print("   🔧 Fix: Update SUPABASE_URL and SUPABASE_KEY in .env")
    except Exception as e:
        print(f"⚠️  Database connection error: {e}")
        print("   Server running in LIMITED MODE (no database features)")
    
    # Clean up any stale uploads from previous runs
    try:
        await chunk_service.cleanup_stale_uploads(max_age_hours=24)
        cleaned_sessions = await cleanup_failed_sessions(hours_old=24)
        print(f"🧹 Cleaned up {cleaned_sessions} stale sessions")
    except Exception as e:
        # Cleanup failure is OK - it will retry later
        pass
    
    # Start background cleanup task
    cleanup_task = asyncio.create_task(periodic_cleanup())
    
    print("✅ Backend ready - Lightning fast with Redis caching!")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down Smart File Transfer Backend...")
    
    # Close Redis connection
    try:
        from services.cache_service import cache
        await cache.close()
    except:
        pass
    
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

async def periodic_cleanup():
    """Background task to periodically clean up stale uploads"""
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            await chunk_service.cleanup_stale_uploads(max_age_hours=24)
            await cleanup_failed_sessions(hours_old=24)
            print("Periodic cleanup completed")
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in periodic cleanup: {e}")

app = FastAPI(
    title="Smart File Transfer with Chat API",
    description="Robust file transfer system with chunk-based uploads and real-time chat for unstable networks",
    version="3.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)  # Add authentication routes
app.include_router(upload.router)
app.include_router(chat.router)  # ✅ ADD CHAT ROUTES
app.include_router(websocket.router)  # Add WebSocket routes

@app.get("/")
async def root():
    return {
        "message": "Smart File Transfer with Chat API",
        "version": "3.0.0",
        "features": [
            "Chunked uploads with resume",
            "Network-adaptive chunk sizing", 
            "Automatic retry mechanisms",
            "File integrity verification",
            "Robust error handling",
            "Concurrent upload support",
            "Real-time chat messaging",  # ✅ NEW FEATURE
            "Person-to-person file sharing",  # ✅ NEW FEATURE
            "Group chat with file sharing",  # ✅ NEW FEATURE
            "WebSocket real-time updates",  # ✅ NEW FEATURE
            "Read receipts and typing indicators"  # ✅ NEW FEATURE
        ]
    }

@app.get("/health")
async def health_check(file_size: Optional[int] = None):
    """
    Enhanced health endpoint with AI-powered chunk size recommendation
    
    Hybrid approach: AI-first with traditional fallback
    Optional file_size parameter to cap chunk size appropriately
    """
    start_time = time.time()
    
    # Simulate minimal processing delay
    await asyncio.sleep(0.001)
    latency_ms = (time.time() - start_time) * 1000
    
    # Estimate bandwidth (can be enhanced with actual measurement)
    bandwidth_mbps = 10.0  # Default assumption
    
    # === STEP 1: Calculate traditional chunk size (ALWAYS RUNS) ===
    traditional_chunk_size = _calculate_traditional_chunk_size(latency_ms, bandwidth_mbps)
    
    # ✅ CAP CHUNK SIZE TO FILE SIZE IF PROVIDED
    if file_size and file_size > 0:
        traditional_chunk_size = min(traditional_chunk_size, file_size)
    
    # === STEP 2: Try AI prediction (MAY FAIL) ===
    ai_chunk_size = None
    ai_prediction = None
    ai_used = False
    fallback_reason = None
    
    try:
        # Record measurement for AI learning
        network_ai.add_measurement(
            latency=latency_ms,
            bandwidth=bandwidth_mbps
        )
        
        # Get AI prediction
        prediction = network_ai.predict_next_quality(lookahead_seconds=10)
        ai_prediction = prediction
        
        # === DECISION: Use AI only if confident enough ===
        if prediction['confidence'] >= AI_CONFIDENCE_THRESHOLD:
            # AI is confident - use its recommendation
            ai_chunk_size = _apply_ai_adjustment(traditional_chunk_size, prediction)
            ai_used = True
            logger.info(f"✅ Using AI recommendation (confidence: {prediction['confidence']:.2f})")
        else:
            # AI not confident enough - stick with traditional
            fallback_reason = f"AI confidence too low ({prediction['confidence']:.2f} < {AI_CONFIDENCE_THRESHOLD})"
            logger.warning(f"⚠️ {fallback_reason} - using traditional logic")
    
    except Exception as e:
        # AI failed - gracefully fall back to traditional
        fallback_reason = f"AI prediction failed: {str(e)}"
        logger.error(f"❌ {fallback_reason} - using traditional logic")
    
    # === STEP 3: Decide final chunk size ===
    if ai_used and ai_chunk_size is not None:
        final_chunk_size = ai_chunk_size
        calculation_method = "ai_preemptive"
    else:
        final_chunk_size = traditional_chunk_size
        calculation_method = "traditional_fallback"
    
    # ✅ FINAL CAP: Ensure chunk size never exceeds file size
    if file_size and file_size > 0:
        final_chunk_size = min(final_chunk_size, file_size)
        if ai_chunk_size:
            ai_chunk_size = min(ai_chunk_size, file_size)
    
    # === STEP 4: Build response ===
    return {
        "status": "healthy",
        "timestamp": time.time(),
        
        # Core network metrics
        "latency_ms": round(latency_ms, 2),
        "bandwidth_mbps": bandwidth_mbps,
        "network_quality": _latency_to_quality(latency_ms),
        
        # Final chunk size recommendation
        "recommended_chunk_size": final_chunk_size,
        "recommended_chunk_size_human": _format_bytes(final_chunk_size),
        
        # Calculation transparency
        "calculation_details": {
            "method_used": calculation_method,
            "traditional_chunk_size": traditional_chunk_size,
            "traditional_chunk_size_human": _format_bytes(traditional_chunk_size),
            "ai_chunk_size": ai_chunk_size,
            "ai_chunk_size_human": _format_bytes(ai_chunk_size) if ai_chunk_size else None,
            "ai_used": ai_used,
            "fallback_reason": fallback_reason
        },
        
        # AI prediction details (may be None if AI failed)
        "ai_prediction": ai_prediction if ai_prediction else {
            "available": False,
            "reason": fallback_reason
        },
        
        # Learning stats
        "ai_stats": {
            "measurements_collected": len(network_ai.recent_history),
            "hourly_patterns_learned": len(network_ai.hourly_patterns),
            "confidence_threshold": AI_CONFIDENCE_THRESHOLD
        },
        
        # Original features
        "features": [
            "file_transfer",
            "chat", 
            "websocket", 
            "authentication",
            "ai_network_prediction"
        ],
        "settings": {
            "max_chunk_size": settings.MAX_CHUNK_SIZE,
            "min_chunk_size": settings.MIN_CHUNK_SIZE,
            "max_retries": settings.MAX_RETRIES,
            "concurrent_uploads": settings.CONCURRENT_UPLOADS
        }
    }


def _calculate_traditional_chunk_size(latency_ms: float, bandwidth_mbps: float) -> int:
    """
    Traditional chunk size logic (FALLBACK - always reliable)
    Based on latency and bandwidth measurements
    """
    # Latency-based base calculation
    if latency_ms < 100:
        base = 2 * 1024 * 1024  # 2MB for excellent
    elif latency_ms < 300:
        base = 1 * 1024 * 1024  # 1MB for good
    elif latency_ms < 600:
        base = 512 * 1024        # 512KB for fair
    else:
        base = 256 * 1024        # 256KB for poor
    
    # Bandwidth-based adjustment
    speed_kbps = bandwidth_mbps * 1024
    if speed_kbps < 128:
        base = min(base, 128 * 1024)
    elif speed_kbps < 256:
        base = min(base, 256 * 1024)
    elif speed_kbps < 512:
        base = min(base, 512 * 1024)
    
    return base


def _apply_ai_adjustment(base_chunk_size: int, prediction: dict) -> int:
    """
    AI pre-emptive adjustment (only called if AI is confident)
    """
    if prediction.get('is_anomaly', False):
        # Defensive: force smallest safe size for anomalies
        return 128 * 1024  # 128KB
    
    if prediction['predicted_quality'] == 'degrading':
        # Network will degrade - reduce chunk size NOW
        return max(int(base_chunk_size * 0.5), 128 * 1024)
    
    elif prediction['predicted_quality'] == 'improving':
        # Network will improve - safe to increase
        return min(int(base_chunk_size * 1.5), 4 * 1024 * 1024)  # Cap at 4MB
    
    return base_chunk_size  # Stable - no change


def _latency_to_quality(latency_ms: float) -> str:
    """Convert latency to human-readable quality label"""
    if latency_ms < 100:
        return "excellent"
    elif latency_ms < 300:
        return "good"
    elif latency_ms < 600:
        return "fair"
    return "poor"


def _format_bytes(bytes_val: int) -> str:
    """Format bytes to human-readable string"""
    if bytes_val >= 1024 * 1024:
        return f"{bytes_val / (1024 * 1024):.1f} MB"
    elif bytes_val >= 1024:
        return f"{bytes_val / 1024:.0f} KB"
    return f"{bytes_val} bytes"

@app.get("/admin/cache/stats")
async def cache_stats():
    """Get Redis cache statistics"""
    try:
        from services.cache_service import cache
        if not cache.enabled:
            return {"error": "Redis cache not available"}
        
        info = await cache.redis.info("stats")
        keyspace = await cache.redis.info("keyspace")
        
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        hit_rate = (hits / total * 100) if total > 0 else 0
        
        return {
            "enabled": cache.enabled,
            "total_connections": info.get("total_connections_received", 0),
            "total_commands": info.get("total_commands_processed", 0),
            "keyspace_hits": hits,
            "keyspace_misses": misses,
            "hit_rate_percent": round(hit_rate, 2),
            "total_keys": keyspace.get("db0", {}).get("keys", 0) if keyspace.get("db0") else 0,
            "status": "🔥 BLAZING FAST!" if hit_rate > 80 else "⚡ FAST" if hit_rate > 50 else "🚀 WARMING UP"
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/admin/cache/clear")
async def clear_cache():
    """Clear all cache (admin only)"""
    try:
        from services.cache_service import cache
        if not cache.enabled:
            return {"error": "Redis cache not available"}
        
        await cache.redis.flushdb()
        return {"message": "✅ Cache cleared successfully - Speed will rebuild as users interact"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/speedtest/{size_kb}")
async def speed_test(size_kb: int):
    """
    Endpoint for network speed testing - returns random data of specified size
    """
    from fastapi.responses import Response
    import os
    
    # Limit size to prevent abuse (max 1MB)
    size_kb = min(size_kb, 1024)
    size_bytes = size_kb * 1024
    
    # Generate random data
    random_data = os.urandom(size_bytes)
    
    return Response(
        content=random_data,
        media_type="application/octet-stream",
        headers={
            "Content-Length": str(size_bytes),
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
