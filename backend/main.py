from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from contextlib import asynccontextmanager

from routers import upload
from routers import websocket  # Add WebSocket router
from routers import auth  # Add auth router
from services.chunk_service import chunk_service
from db.crud import cleanup_failed_sessions
from config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting Smart File Transfer Backend...")
    
    # Clean up any stale uploads from previous runs
    try:
        await chunk_service.cleanup_stale_uploads(max_age_hours=24)
        cleaned_sessions = await cleanup_failed_sessions(hours_old=24)
        print(f"Cleaned up {cleaned_sessions} stale sessions")
    except Exception as e:
        print(f"Warning: Startup cleanup failed: {e}")
    
    # Start background cleanup task
    cleanup_task = asyncio.create_task(periodic_cleanup())
    
    yield
    
    # Shutdown
    print("Shutting down Smart File Transfer Backend...")
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
    title="Smart File Transfer API",
    description="Robust file transfer system with chunk-based uploads for unstable networks",
    version="2.0.0",
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
app.include_router(upload.router)
app.include_router(websocket.router)  # Add WebSocket routes
app.include_router(auth.router)  # Add authentication routes

@app.get("/")
async def root():
    return {
        "message": "Smart File Transfer API",
        "version": "2.0.0",
        "features": [
            "Chunked uploads with resume",
            "Network-adaptive chunk sizing",
            "Automatic retry mechanisms",
            "File integrity verification",
            "Robust error handling",
            "Concurrent upload support"
        ]
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "settings": {
            "max_chunk_size": settings.MAX_CHUNK_SIZE,
            "min_chunk_size": settings.MIN_CHUNK_SIZE,
            "max_retries": settings.MAX_RETRIES,
            "concurrent_uploads": settings.CONCURRENT_UPLOADS
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
