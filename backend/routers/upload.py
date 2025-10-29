from fastapi import APIRouter, Form, File, UploadFile, HTTPException, BackgroundTasks, Depends, status
from fastapi.responses import JSONResponse, FileResponse
import asyncio
from typing import Dict, List, Any
import time
import os

from services.chunk_service import chunk_service
from services.network_monitor import network_monitor
from db.crud import (
    create_file_session, get_file_session, mark_chunk_uploaded, 
    get_uploaded_chunk_numbers, update_upload_progress
)
from db.auth_crud import get_user_file_sessions, verify_file_ownership
from dependencies.auth import get_current_active_user as get_current_user
from config import settings

# Import WebSocket managers after router is created to avoid circular imports
router = APIRouter(prefix="/upload", tags=["upload"])

# WebSocket managers will be imported dynamically to avoid circular imports
async def get_upload_websocket_manager():
    """Dynamically import upload WebSocket manager to avoid circular imports"""
    try:
        from routers.websocket import upload_manager
        return upload_manager
    except ImportError:
        return None

async def get_chat_websocket_manager():
    """Dynamically import chat WebSocket manager to avoid circular imports"""
    try:
        from routers.websocket import chat_manager
        return chat_manager
    except ImportError:
        return None

@router.post("/start")
async def start_upload(
    background_tasks: BackgroundTasks,
    file_id: str = Form(...),
    filename: str = Form(...),
    total_chunks: int = Form(...),
    file_size: int = Form(...),
    file_hash: str = Form(...),
    current_user: dict = Depends(get_current_user)  # ✅ REQUIRE AUTH
):
    """Start chunked file upload (requires authentication)"""
    try:
        # Create session in database with individual parameters
        session = await create_file_session(
            file_id=file_id,
            filename=filename,
            total_chunks=total_chunks,
            file_size=file_size,
            file_hash=file_hash,
            user_id=current_user["id"],
            upload_type="regular"  # ✅ PRESERVE EXISTING BEHAVIOR
        )
        
        # Get optimal chunk size for this upload
        optimal_chunk_size = network_monitor.get_optimal_chunk_size()
        
        # Send WebSocket update
        manager = await get_websocket_manager()
        if manager:
            await manager.send_progress_update(file_id, {
                "type": "upload_started",
                "filename": filename,
                "total_chunks": total_chunks,
                "file_size": file_size,
                "recommended_chunk_size": optimal_chunk_size
            })
        
        return JSONResponse({
            "status": "started",
            "file_id": file_id,
            "chunk_size": optimal_chunk_size,
            "message": "Upload session created",
            "user_id": current_user["id"]  # ✅ RETURN USER INFO
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start upload: {str(e)}")

@router.post("/chunk")
async def upload_chunk(
    file_id: str = Form(...),
    chunk_number: int = Form(...),
    total_chunks: int = Form(...),
    chunk_hash: str = Form(...),
    attempt: int = Form(default=1),
    chunk: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)  # ✅ REQUIRE AUTH
):
    """Upload a single chunk with verification and retry support"""
    try:
        # Validate chunk
        if chunk.size == 0:
            raise HTTPException(status_code=400, detail="Empty chunk received")
        
        # Read chunk data
        chunk_data = await chunk.read()
        
        # ✅ USE SHARED HELPER FUNCTION (WORKS FOR BOTH REGULAR AND CHAT)
        result = await process_chunk_upload(
            file_id=file_id,
            chunk_number=chunk_number,
            chunk_data=chunk_data,
            chunk_hash=chunk_hash,
            user_id=current_user["id"]
        )
        
        # ✅ PRESERVE EXISTING RESPONSE FORMAT
        return JSONResponse({
            "status": "success",
            "chunk_number": result["chunk_number"],
            "uploaded_chunks": result["uploaded_chunks"],
            "total_chunks": result["total_chunks"],
            "progress": result["progress"],
            "recommended_chunk_size": network_monitor.get_optimal_chunk_size(),
            "upload_time": 0.1  # Placeholder for compatibility
        })
            
    except HTTPException:
        raise
    except Exception as e:
        # Record failure and provide retry guidance
        network_monitor.record_upload(len(chunk_data) if 'chunk_data' in locals() else 0, upload_time, False)
        
        # Send WebSocket error
        manager = await get_websocket_manager()
        if manager:
            await manager.send_progress_update(file_id, {
                "type": "chunk_failed", 
                "chunk_number": chunk_number,
                "error": str(e),
                "retry_recommended": True
            })
        
        # Suggest retry with smaller chunk size if this was a large chunk
        retry_chunk_size = network_monitor.get_optimal_chunk_size()
        
        raise HTTPException(
            status_code=500, 
            detail={
                "error": f"Chunk upload failed: {str(e)}",
                "retry_recommended": True,
                "suggested_chunk_size": retry_chunk_size,
                "attempt": attempt
            }
        )

@router.get("/status/{file_id}")
async def get_upload_status(
    file_id: str,
    current_user: dict = Depends(get_current_user)  # ✅ REQUIRE AUTH
):
    """Get current upload status and missing chunks"""
    try:
        # Get session info
        session = get_file_session(file_id)
        if not session:
            raise HTTPException(status_code=404, detail="Upload session not found")
        
        # ✅ VERIFY USER OWNS THIS UPLOAD SESSION
        if session.get("user_id") != current_user["id"]:
            raise HTTPException(status_code=403, detail="Unauthorized access to upload session")
        
        # Get uploaded chunks
        uploaded_chunks = await chunk_service.get_uploaded_chunks(file_id)
        total_chunks = session.get('total_chunks', 0)
        
        # Calculate missing chunks
        expected_chunks = set(range(total_chunks))
        missing_chunks = sorted(expected_chunks - set(uploaded_chunks))
        
        # Get network recommendations
        optimal_chunk_size = network_monitor.get_optimal_chunk_size()
        use_concurrent = network_monitor.should_use_concurrent_upload()
        
        return JSONResponse({
            "file_id": file_id,
            "uploaded_chunks": uploaded_chunks,
            "missing_chunks": missing_chunks,
            "total_chunks": total_chunks,
            "progress": (len(uploaded_chunks) / total_chunks * 100) if total_chunks > 0 else 0,
            "status": session.get('status', 'unknown'),
            "recommendations": {
                "chunk_size": optimal_chunk_size,
                "concurrent_uploads": settings.CONCURRENT_UPLOADS if use_concurrent else 1,
                "network_stable": len(missing_chunks) / total_chunks < 0.1 if total_chunks > 0 else True
            }
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

@router.post("/complete")
async def complete_upload(
    background_tasks: BackgroundTasks,
    file_id: str = Form(...),
    expected_hash: str = Form(...),
    current_user: dict = Depends(get_current_user)  # ✅ REQUIRE AUTH
):
    """Complete upload by merging chunks and verifying file"""
    try:
        # ✅ USE SHARED HELPER FUNCTION (WORKS FOR BOTH REGULAR AND CHAT)
        result = await complete_file_upload(
            file_id=file_id,
            expected_hash=expected_hash,
            user_id=current_user["id"]
        )
        
        # Schedule cleanup in background
        background_tasks.add_task(chunk_service.cleanup_chunks, file_id)
        
        # ✅ PRESERVE EXISTING RESPONSE FORMAT
        return JSONResponse({
            "status": result["status"],
            "file_path": result["file_path"],
            "file_id": result["file_id"],
            "merged_hash": result["file_hash"],
            "integrity_verified": True,  # Helper function already verified
            "message": "File uploaded and verified successfully"
        })
        
    except Exception as e:
        # Send WebSocket error
        manager = await get_websocket_manager()
        if manager:
            await manager.send_error(file_id, f"Failed to complete upload: {str(e)}")
        
        # Update session status to failed
        try:
            session = get_file_session(file_id)
            if session:
                await update_upload_progress(file_id, 0, session['total_chunks'], status="failed")
        except:
            pass
        
        raise HTTPException(status_code=500, detail=f"Failed to complete upload: {str(e)}")

@router.delete("/cancel/{file_id}")
async def cancel_upload(
    file_id: str, 
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)  # ✅ REQUIRE AUTH
):
    """Cancel an ongoing upload and clean up"""
    try:
        # Update session status
        session = get_file_session(file_id)
        if session:
            # ✅ VERIFY USER OWNS THIS UPLOAD SESSION
            if session.get("user_id") != current_user["id"]:
                raise HTTPException(status_code=403, detail="Unauthorized access to upload session")
            
            await update_upload_progress(file_id, 0, session['total_chunks'], status="cancelled")
        
        # Schedule cleanup
        background_tasks.add_task(chunk_service.cleanup_chunks, file_id)
        
        return JSONResponse({
            "status": "cancelled",
            "file_id": file_id,
            "message": "Upload cancelled and cleaned up"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel upload: {str(e)}")

# Background task to clean up stale uploads
@router.on_event("startup")
async def cleanup_stale_uploads():
    """Clean up old incomplete uploads on startup"""
    try:
        await chunk_service.cleanup_stale_uploads(max_age_hours=24)
    except Exception as e:
        print(f"Error during startup cleanup: {e}")

@router.get("/files")
async def list_user_files(current_user: dict = Depends(get_current_user)):
    """List all files uploaded by the current user"""
    try:
        # Get user's file sessions from database
        user_sessions = await get_user_file_sessions(current_user["id"])
        
        files = []
        for session in user_sessions:
            # Only include completed uploads
            if session.get("status") == "completed":
                filename = session.get("filename")
                file_path = settings.UPLOAD_DIR / filename
                
                # Check if file still exists
                if file_path.exists():
                    stat = file_path.stat()
                    files.append({
                        "id": session.get("file_id"),
                        "name": filename,
                        "size": session.get("file_size", stat.st_size),
                        "upload_date": session.get("created_at"),
                        "status": session.get("status"),
                        "hash": session.get("file_hash")
                    })
        
        return JSONResponse({
            "files": files,
            "total": len(files)
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

@router.delete("/files/{filename}")
async def delete_file(
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete an uploaded file"""
    try:
        # Handle both just filename or full path with filename
        if '/' in filename:
            filename = os.path.basename(filename)
        
        file_path = settings.UPLOAD_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found")
        
        # TODO: Add file ownership verification from database
        # For now allowing all authenticated users to delete files
        # In production, verify the user owns this file
        
        # Delete the file
        os.remove(file_path)
        
        return JSONResponse({
            "status": "deleted",
            "filename": filename,
            "message": f"File '{filename}' deleted successfully"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

@router.get("/download/{filename}")
async def download_file(
    filename: str,
    current_user: dict = Depends(get_current_user)  # ✅ REQUIRE AUTH
):
    """Download an uploaded file"""
    from fastapi.responses import FileResponse
    import os
    
    # Handle both just filename or full path with filename
    if '/' in filename:
        filename = os.path.basename(filename)
    
    file_path = settings.UPLOAD_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found in uploaded_files directory")
    
    # ✅ TODO: ADD FILE OWNERSHIP VERIFICATION
    # For now allowing all authenticated users to download files
    # In production, you might want to track file ownership in database
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='application/octet-stream'
    )


# ✅ HELPER FUNCTIONS FOR CHAT INTEGRATION (PRESERVES ALL EXISTING FUNCTIONALITY)

async def process_chunk_upload(file_id: str, chunk_number: int, chunk_data: bytes, 
                             chunk_hash: str, user_id: str) -> Dict[str, Any]:
    """Process chunk upload for both regular and chat uploads"""
    try:
        print(f"DEBUG: process_chunk_upload called with file_id={file_id}, chunk_number={chunk_number}, user_id={user_id}")
        
        # Get the file session
        session = get_file_session(file_id)
        if not session:
            print(f"DEBUG: File session {file_id} not found")
            raise HTTPException(status_code=404, detail=f"File session {file_id} not found")
        
        print(f"DEBUG: File session found: {session}")
        
        # Verify ownership (works for both regular and chat uploads)
        if session.get("user_id") != user_id:
            print(f"DEBUG: Ownership check failed - session user_id: {session.get('user_id')}, request user_id: {user_id}")
            raise HTTPException(status_code=403, detail="Not authorized to upload to this session")
        
        # Use existing chunk service
        print(f"DEBUG: About to call save_chunk_with_verification")
        success = await chunk_service.save_chunk_with_verification(
            file_id=file_id,
            chunk_number=chunk_number,
            chunk_data=chunk_data,
            expected_hash=chunk_hash
        )
        print(f"DEBUG: save_chunk_with_verification returned: {success}")
        
        if not success:
            print(f"DEBUG: Chunk upload failed, raising HTTPException")
            raise HTTPException(status_code=400, detail="Chunk upload failed")
        
        # Mark chunk as uploaded
        print(f"DEBUG: About to mark chunk as uploaded")
        await mark_chunk_uploaded(file_id, chunk_number)
        print(f"DEBUG: Chunk marked as uploaded")
        
        # Update progress
        print(f"DEBUG: About to get uploaded chunk numbers")
        uploaded_chunks = len(get_uploaded_chunk_numbers(file_id))
        print(f"DEBUG: Got uploaded chunk numbers, count: {uploaded_chunks}")
        progress = (uploaded_chunks / session["total_chunks"]) * 100
        print(f"DEBUG: Calculated progress: {progress}")
        
        print(f"DEBUG: About to update upload progress")
        await update_upload_progress(file_id, uploaded_chunks, session["total_chunks"])
        print(f"DEBUG: Upload progress updated")
        
        # ✅ NOTIFY WEBSOCKET (WORKS FOR BOTH REGULAR AND CHAT)
        websocket_manager = await get_upload_websocket_manager()
        if websocket_manager:
            await websocket_manager.send_progress_update(file_id, {
                "type": "chunk_uploaded",
                "file_id": file_id,
                "chunk_number": chunk_number,
                "progress": progress,
                "uploaded_chunks": uploaded_chunks,
                "total_chunks": session["total_chunks"]
            })
        
        result = {
            "status": "chunk_uploaded",
            "chunk_number": chunk_number,
            "progress": progress,
            "uploaded_chunks": uploaded_chunks,
            "total_chunks": session["total_chunks"],
            "filename": session.get("filename", "")
        }
        print(f"DEBUG: Returning result: {result}")
        return result
    
    except HTTPException as he:
        print(f"DEBUG: HTTPException in process_chunk_upload: status={he.status_code}, detail={he.detail}")
        raise he
    except Exception as e:
        print(f"DEBUG: Unexpected exception in process_chunk_upload: {type(e).__name__}: {e}")
        import traceback
        print(f"DEBUG: Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chunk upload failed: {str(e)}")


async def complete_file_upload(file_id: str, expected_hash: str, user_id: str) -> Dict[str, Any]:
    """Complete file upload for both regular and chat uploads"""
    try:
        print(f"DEBUG: complete_file_upload called with file_id={file_id}, user_id={user_id}")
        
        # Get the file session
        session = get_file_session(file_id)
        if not session:
            print(f"DEBUG: File session {file_id} not found")
            raise HTTPException(status_code=404, detail=f"File session {file_id} not found")
        
        print(f"DEBUG: File session found: {session}")
        
        # Verify ownership
        if session.get("user_id") != user_id:
            print(f"DEBUG: Ownership check failed - session user_id: {session.get('user_id')}, request user_id: {user_id}")
            raise HTTPException(status_code=403, detail="Not authorized to complete this upload")
        
        # Use existing chunk service to merge chunks
        print(f"DEBUG: About to call merge_chunks_with_verification")
        combined_file_path, computed_hash = await chunk_service.merge_chunks_with_verification(
            file_id=file_id,
            total_chunks=session["total_chunks"],
            expected_file_hash=expected_hash,
            filename=session["filename"]
        )
        print(f"DEBUG: merge_chunks_with_verification returned: {combined_file_path}, hash: {computed_hash}")
        
        if not combined_file_path:
            print(f"DEBUG: merge_chunks_with_verification failed, raising HTTPException")
            raise HTTPException(status_code=400, detail="Failed to combine chunks")
        
        # ✅ NOTIFY WEBSOCKET COMPLETION
        websocket_manager = await get_upload_websocket_manager()
        if websocket_manager:
            await websocket_manager.send_completion(file_id, str(combined_file_path))
        
        # Return comprehensive file info
        file_stats = os.stat(combined_file_path)
        
        return {
            "status": "completed",
            "file_id": file_id,
            "session_id": session.get("id"),
            "file_path": str(combined_file_path),
            "original_filename": session["filename"],
            "file_size": file_stats.st_size,
            "file_hash": expected_hash,
            "total_chunks": session["total_chunks"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload completion failed: {str(e)}")
