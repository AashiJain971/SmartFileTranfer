from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from supabase import create_client
from config import settings
from services.auth_service import auth_service

# Initialize Supabase client
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

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

async def create_user(user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Create a new user"""
    try:
        # Hash password
        user_data["password_hash"] = auth_service.hash_password(user_data.pop("password"))
        user_data["created_at"] = datetime.utcnow().isoformat()
        user_data["updated_at"] = datetime.utcnow().isoformat()
        
        result = supabase.table("users").insert(user_data).execute()
        
        if result.data:
            return result.data[0]
        return None
        
    except Exception as e:
        print(f"Error creating user: {e}")
        return None

async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email"""
    try:
        result = supabase.table("users").select("*").eq("email", email).execute()
        
        if result.data:
            return result.data[0]
        return None
        
    except Exception as e:
        print(f"Error getting user by email: {e}")
        return None

async def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Get user by username"""
    try:
        result = supabase.table("users").select("*").eq("username", username).execute()
        
        if result.data:
            return result.data[0]
        return None
        
    except Exception as e:
        print(f"Error getting user by username: {e}")
        return None

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

async def update_last_login(user_id: str):
    """Update user's last login timestamp"""
    try:
        supabase.table("users").update({
            "last_login": datetime.utcnow().isoformat()
        }).eq("id", user_id).execute()
        
    except Exception as e:
        print(f"Error updating last login: {e}")

async def create_user_session(user_id: str, token_hash: str, expires_at: datetime, 
                            device_info: str = None, ip_address: str = None) -> bool:
    """Create a user session"""
    try:
        session_data = {
            "user_id": user_id,
            "token_hash": token_hash,
            "expires_at": expires_at.isoformat(),
            "device_info": device_info,
            "ip_address": ip_address,
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("user_sessions").insert(session_data).execute()
        return bool(result.data)
        
    except Exception as e:
        print(f"Error creating user session: {e}")
        return False

async def invalidate_user_session(token_hash: str):
    """Invalidate a user session"""
    try:
        supabase.table("user_sessions").update({
            "is_active": False
        }).eq("token_hash", token_hash).execute()
        
    except Exception as e:
        print(f"Error invalidating session: {e}")

async def cleanup_expired_sessions():
    """Clean up expired sessions"""
    try:
        now = datetime.utcnow().isoformat()
        supabase.table("user_sessions").delete().lt("expires_at", now).execute()
        
    except Exception as e:
        print(f"Error cleaning up sessions: {e}")

async def create_password_reset_token(user_id: str, token_hash: str, expires_at: datetime) -> bool:
    """Create a password reset token"""
    try:
        token_data = {
            "user_id": user_id,
            "token_hash": token_hash,
            "expires_at": expires_at.isoformat(),
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("password_reset_tokens").insert(token_data).execute()
        return bool(result.data)
        
    except Exception as e:
        print(f"Error creating reset token: {e}")
        return False

async def verify_reset_token(token_hash: str) -> Optional[Dict[str, Any]]:
    """Verify a password reset token"""
    try:
        now = datetime.utcnow().isoformat()
        result = supabase.table("password_reset_tokens").select("*").eq(
            "token_hash", token_hash
        ).eq("used", False).gt("expires_at", now).execute()
        
        if result.data:
            return result.data[0]
        return None
        
    except Exception as e:
        print(f"Error verifying reset token: {e}")
        return None

async def mark_reset_token_used(token_id: str):
    """Mark a reset token as used"""
    try:
        supabase.table("password_reset_tokens").update({
            "used": True
        }).eq("id", token_id).execute()
        
    except Exception as e:
        print(f"Error marking reset token as used: {e}")

async def update_user_password(user_id: str, new_password_hash: str):
    """Update user password"""
    try:
        supabase.table("users").update({
            "password_hash": new_password_hash,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", user_id).execute()
        
    except Exception as e:
        print(f"Error updating password: {e}")

async def get_user_file_sessions(user_id: str) -> list:
    """Get all file sessions for a specific user"""
    try:
        result = supabase.table("file_sessions").select("*").eq("user_id", user_id).execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"Error getting user file sessions: {e}")
        return []

async def verify_file_ownership(file_id: str, user_id: str) -> bool:
    """Verify if a file belongs to a user"""
    try:
        result = supabase.table("file_sessions").select("user_id").eq("file_id", file_id).execute()
        if result.data:
            return result.data[0]["user_id"] == user_id
        return False
    except Exception as e:
        print(f"Error verifying file ownership: {e}")
        return False