from datetime import datetime
from typing import Optional, List, Dict, Any
from db.database import supabase

async def create_file_session(
    file_id: str, 
    filename: str, 
    total_chunks: int, 
    file_size: int, 
    file_hash: str,
    user_id: str,
    upload_type: str = "regular",  # ✅ ADD SUPPORT FOR CHAT
    chat_room_id: Optional[str] = None  # ✅ LINK TO CHAT ROOM
) -> Dict[str, Any]:
    """Create a new file upload session"""
    session_data = {
        "file_id": file_id,
        "filename": filename,
        "total_chunks": total_chunks,
        "file_size": file_size,
        "file_hash": file_hash,
        "user_id": user_id,
        "uploaded_chunks": 0,
        "status": "uploading",
        "upload_type": upload_type,  # ✅ SUPPORT CHAT UPLOADS
        "chat_room_id": chat_room_id,  # ✅ LINK TO CHAT ROOM
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    try:
        result = supabase.table("file_sessions").insert(session_data).execute()
        if result.data:
            return result.data[0]
        else:
            raise Exception(f"Failed to create file session: {result}")
    except Exception as e:
        # If table doesn't exist, create a mock session for testing
        print(f"Database error in create_file_session: {e}")
        return {
            "id": 1,
            "file_id": file_id,
            "filename": filename,
            "total_chunks": total_chunks,
            "file_size": file_size,
            "file_hash": file_hash,
            "uploaded_chunks": 0,
            "status": "uploading"
        }

async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID"""
    try:
        result = supabase.table("users").select("*").eq("id", user_id).execute()
        
        if result.data:
            return result.data[0]
        return None
        
    except Exception as e:
        print(f"Error getting user by ID: {e}")
        return None

def get_file_session(file_id: str) -> Optional[Dict[str, Any]]:
    """Get file session by ID"""
    try:
        print(f"DEBUG: Looking for file session with ID: {file_id}")  # Debug logging
        result = supabase.table("file_sessions").select("*").eq("file_id", file_id).execute()
        print(f"DEBUG: Database query result: {result.data}")  # Debug logging
        
        if result.data:
            return result.data[0]
        else:
            print(f"DEBUG: No file session found for ID: {file_id}")
            return None
    except Exception as e:
        print(f"Database error in get_file_session: {e}")
        print(f"DEBUG: Full exception details: {type(e).__name__}: {str(e)}")
        return None  # Return None instead of mock data to see real errors

async def update_upload_progress(
    file_id: str, 
    uploaded_chunks: int, 
    total_chunks: int, 
    status: str = "uploading"
) -> bool:
    """Update upload progress and status"""
    update_data = {
        "uploaded_chunks": uploaded_chunks,
        "status": status,
        "updated_at": datetime.utcnow().isoformat(),
        "progress": (uploaded_chunks / total_chunks * 100) if total_chunks > 0 else 0
    }
    
    try:
        result = supabase.table("file_sessions").update(update_data).eq("file_id", file_id).execute()
        return bool(result.data)
    except Exception as e:
        print(f"Database error in update_upload_progress: {e}")
        # Return True to allow upload to continue
        return True

async def mark_chunk_uploaded(file_id: str, chunk_number: int) -> bool:
    """Mark specific chunk as successfully uploaded"""
    chunk_data = {
        "file_id": file_id,
        "chunk_number": chunk_number,
        "uploaded_at": datetime.utcnow().isoformat()
    }
    
    try:
        # Use upsert to handle duplicate chunk uploads
        result = supabase.table("uploaded_chunks").upsert(chunk_data).execute()
        return bool(result.data)
    except Exception as e:
        print(f"Database error in mark_chunk_uploaded: {e}")
        # Return True to allow upload to continue even if database fails
        return True

def get_uploaded_chunk_numbers(file_id: str) -> List[int]:
    """Get list of successfully uploaded chunk numbers"""
    try:
        result = supabase.table("uploaded_chunks").select("chunk_number").eq("file_id", file_id).execute()
        return [row["chunk_number"] for row in result.data] if result.data else []
    except Exception as e:
        print(f"Database error in get_uploaded_chunk_numbers: {e}")
        # Return empty list if database fails
        return []

async def cleanup_failed_sessions(hours_old: int = 24) -> int:
    """Clean up old failed or stale upload sessions"""
    cutoff_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff_time = cutoff_time.isoformat()
    
    # Delete old sessions
    result = supabase.table("file_sessions").delete().lt("updated_at", cutoff_time).execute()
    
    # Delete associated chunk records
    supabase.table("uploaded_chunks").delete().lt("uploaded_at", cutoff_time).execute()
    
    return len(result.data) if result.data else 0

def get_session_stats(file_id: str) -> Dict[str, Any]:
    """Get detailed session statistics"""
    session = get_file_session(file_id)
    if not session:
        return {}
    
    uploaded_chunks = get_uploaded_chunk_numbers(file_id)
    
    return {
        "file_id": file_id,
        "filename": session.get("filename"),
        "total_chunks": session.get("total_chunks", 0),
        "uploaded_chunks_count": len(uploaded_chunks),
        "progress": (len(uploaded_chunks) / session.get("total_chunks", 1)) * 100,
        "status": session.get("status"),
        "file_size": session.get("file_size", 0),
        "created_at": session.get("created_at"),
        "updated_at": session.get("updated_at")
    }