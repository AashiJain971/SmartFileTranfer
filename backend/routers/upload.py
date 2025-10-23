from fastapi import APIRouter, Form, File, UploadFile, HTTPException, BackgroundTasks, Depends, status
from fastapi.responses import JSONResponse, FileResponse
import asyncio
from typing import Dict, List
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

# Import WebSocket manager after router is created to avoid circular imports
router = APIRouter(prefix="/upload", tags=["upload"])

# WebSocket manager will be imported dynamically to avoid circular imports
async def get_websocket_manager():
    """Dynamically import WebSocket manager to avoid circular imports"""
    try:
        from routers.websocket import manager
        return manager
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
            user_id=current_user["id"]
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
    start_time = time.time()
    
    try:
        # ✅ VERIFY USER OWNS THIS UPLOAD SESSION
        session = get_file_session(file_id)
        if not session or session.get("user_id") != current_user["id"]:
            raise HTTPException(status_code=403, detail="Unauthorized access to upload session")
        # Validate chunk
        if chunk.size == 0:
            raise HTTPException(status_code=400, detail="Empty chunk received")
        
        # Read chunk data
        chunk_data = await chunk.read()
        
        # Send WebSocket update - chunk started
        manager = await get_websocket_manager()
        if manager:
            await manager.send_progress_update(file_id, {
                "type": "chunk_started",
                "chunk_number": chunk_number,
                "chunk_size": len(chunk_data)
            })
        
        # Save chunk with verification
        success = await chunk_service.save_chunk_with_verification(
            file_id=file_id,
            chunk_number=chunk_number,
            chunk_data=chunk_data,
            expected_hash=chunk_hash,
            max_retries=1  # We handle retries at the router level
        )
        
        if success:
            # Mark chunk as uploaded in database
            await mark_chunk_uploaded(file_id, chunk_number)
            
            # Update progress
            uploaded_chunks = await chunk_service.get_uploaded_chunks(file_id)
            await update_upload_progress(file_id, len(uploaded_chunks), total_chunks)
            
            # Get new recommendations based on performance
            new_chunk_size = network_monitor.get_optimal_chunk_size()
            
            # Send WebSocket update - chunk completed
            upload_time = time.time() - start_time
            progress_percent = (len(uploaded_chunks) / total_chunks) * 100
            
            if manager:
                await manager.send_progress_update(file_id, {
                    "type": "chunk_completed",
                    "chunk_number": chunk_number,
                    "uploaded_chunks": len(uploaded_chunks),
                    "total_chunks": total_chunks,
                    "progress": progress_percent,
                    "upload_time": upload_time,
                    "recommended_chunk_size": new_chunk_size,
                    "network_stable": network_monitor.should_use_concurrent_upload()
                })
            
            return JSONResponse({
                "status": "success",
                "chunk_number": chunk_number,
                "uploaded_chunks": len(uploaded_chunks),
                "total_chunks": total_chunks,
                "progress": progress_percent,
                "recommended_chunk_size": new_chunk_size,
                "upload_time": upload_time
            })
        else:
            raise HTTPException(status_code=500, detail=f"Failed to save chunk {chunk_number}")
            
    except ValueError as e:
        # Hash mismatch or verification error
        manager = await get_websocket_manager()
        if manager:
            await manager.send_progress_update(file_id, {
                "type": "chunk_failed",
                "chunk_number": chunk_number,
                "error": str(e)
            })
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Record failure and provide retry guidance
        upload_time = time.time() - start_time
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
        # Send WebSocket update - merging started
        manager = await get_websocket_manager()
        if manager:
            await manager.send_progress_update(file_id, {
                "type": "merging_started",
                "message": "Merging chunks into final file..."
            })
        
        # Get session info
        session = get_file_session(file_id)
        if not session:
            raise HTTPException(status_code=404, detail="Upload session not found")
        
        # ✅ VERIFY USER OWNS THIS UPLOAD SESSION
        if session.get("user_id") != current_user["id"]:
            raise HTTPException(status_code=403, detail="Unauthorized access to upload session")
        
        # Merge chunks with verification
        final_file_path, merged_hash = await chunk_service.merge_chunks_with_verification(
            file_id=file_id,
            total_chunks=session['total_chunks'],
            expected_file_hash=expected_hash,
            filename=session['filename']
        )
        
        # Update session status
        await update_upload_progress(file_id, session['total_chunks'], session['total_chunks'], status="completed")
        
        # Send WebSocket completion
        if manager:
            await manager.send_completion(file_id, str(final_file_path))
        
        # Schedule cleanup in background
        background_tasks.add_task(chunk_service.cleanup_chunks, file_id)
        
        return JSONResponse({
            "status": "completed",
            "file_path": str(final_file_path),
            "file_id": file_id,
            "merged_hash": merged_hash,
            "integrity_verified": merged_hash == expected_hash,
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
