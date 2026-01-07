from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from supabase import create_client
from config import settings
from services.auth_service import auth_service
from services.cache_service import cache
import asyncio
import time

# Initialize Supabase client with timeout configuration
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

async def warm_up_database_connections():
    """Pre-warm database connections to avoid cold start timeouts"""
    try:
        # Make a simple query to establish connection
        result = supabase.table("users").select("id").limit(1).execute()
        print("🔥 Database connection established and warmed up")
        
        # Pre-warm a few more connections with different queries
        await asyncio.sleep(0.1)
        supabase.table("user_sessions").select("id").limit(1).execute()
        await asyncio.sleep(0.1)
        
        return True
    except Exception as e:
        error_msg = str(e)
        
        # Provide helpful error diagnosis
        if "nodename nor servname" in error_msg or "[Errno 8]" in error_msg:
            print(f"❌ Database warm-up failed: DNS resolution error")
            print(f"   💡 Check: 1) Internet connection 2) SUPABASE_URL in .env")
            print(f"   📍 Current SUPABASE_URL: {settings.SUPABASE_URL[:30]}...")
        elif "Connection refused" in error_msg:
            print(f"❌ Database warm-up failed: Connection refused")
            print(f"   💡 Check: Network/firewall or Supabase service status")
        elif "timeout" in error_msg.lower():
            print(f"❌ Database warm-up failed: Connection timeout")
            print(f"   💡 Check: Internet speed or Supabase service status")
        else:
            print(f"❌ Database warm-up failed: {error_msg}")
        
        return False

async def retry_database_operation(operation_func, max_retries=None, delay=None):
    """Retry database operations on timeout"""
    if max_retries is None:
        max_retries = settings.DB_MAX_RETRIES
    if delay is None:
        delay = settings.DB_RETRY_DELAY
        
    for attempt in range(max_retries):
        try:
            return await operation_func()
        except Exception as e:
            error_msg = str(e).lower()
            if ("timeout" in error_msg or "connection" in error_msg or 
                "read operation timed out" in error_msg or 
                "network" in error_msg or "unreachable" in error_msg):
                
                if attempt < max_retries - 1:
                    wait_time = delay * (1.5 ** attempt)  # Exponential backoff
                    wait_time = min(wait_time, 5.0)  # Cap at 5 seconds
                    print(f"🔄 Database timeout on attempt {attempt + 1}/{max_retries}, retrying in {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    print(f"❌ Database operation failed after {max_retries} attempts: {error_msg}")
            # Re-raise non-timeout errors or final attempt
            raise e

async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID with Redis caching"""
    cache_key = f"user:{user_id}"
    
    # Try cache first
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    async def _operation():
        result = supabase.table("users").select("*").eq("id", user_id).execute()
        if result.data:
            return result.data[0]
        return None
    
    try:
        user = await retry_database_operation(_operation)
        if user:
            # Cache for 10 minutes
            await cache.set(cache_key, user, ttl=600)
        return user
    except Exception as e:
        print(f"❌ Error getting user by ID after retries: {e}")
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
    """Get user by email with Redis caching"""
    cache_key = f"user:email:{email}"
    
    # Try cache first
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    async def _operation():
        result = supabase.table("users").select("*").eq("email", email).execute()
        if result.data:
            return result.data[0]
        return None
    
    try:
        user = await retry_database_operation(_operation)
        if user:
            # Cache for 10 minutes
            await cache.set(cache_key, user, ttl=600)
            # Also cache by user_id
            await cache.set(f"user:{user['id']}", user, ttl=600)
        return user
    except Exception as e:
        print(f"❌ Error getting user by email after retries: {e}")
        return None

async def get_user_by_email_with_login_retry(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email with Redis caching and enhanced retry for login"""
    cache_key = f"user:email:{email}"
    
    # Try cache first for instant login
    cached = await cache.get(cache_key)
    if cached:
        print(f"🔥 FAST LOGIN - User loaded from cache: {email[:10]}...")
        return cached
    
    async def _operation():
        print(f"🔍 Querying user by email: {email[:10]}...")
        result = supabase.table("users").select("*").eq("email", email).execute()
        if result.data:
            print(f"✅ User found for email: {email[:10]}...")
            return result.data[0]
        print(f"❌ No user found for email: {email[:10]}...")
        return None
    
    try:
        # Enhanced retry for login with more attempts and better backoff
        print(f"🚀 Starting login database query for: {email[:10]}...")
        user = await retry_database_operation(_operation, max_retries=6, delay=0.3)
        if user:
            # Cache for 10 minutes for fast subsequent logins
            await cache.set(cache_key, user, ttl=600)
            await cache.set(f"user:{user['id']}", user, ttl=600)
        return user
    except Exception as e:
        print(f"❌ Error getting user by email for login after enhanced retries: {e}")
        return None

async def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Get user by username with retry logic"""
    async def _operation():
        result = supabase.table("users").select("*").eq("username", username).execute()
        if result.data:
            return result.data[0]
        return None
    
    try:
        return await retry_database_operation(_operation)
    except Exception as e:
        print(f"❌ Error getting user by username after retries: {e}")
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

async def delete_user_account(user_id: str) -> bool:
    """
    Permanently delete a user account and all associated data.
    Uses database CASCADE constraints for automatic cleanup - FAST and reliable!
    
    Database automatically deletes:
    - user_sessions (ON DELETE CASCADE)
    - password_reset_tokens (ON DELETE CASCADE)  
    - file_sessions (ON DELETE CASCADE)
    - chat_room_members (ON DELETE CASCADE)
    - messages (ON DELETE CASCADE via sender_id)
    - chat_rooms created_by user (ON DELETE CASCADE)
    """
    try:
        print(f"🗑️  Starting FAST CASCADE deletion for user {user_id}")
        
        # Just delete the user - database CASCADE handles everything!
        delete_result = supabase.table("users").delete().eq("id", user_id).execute()
        
        # Verify deletion succeeded
        if delete_result.data and len(delete_result.data) > 0:
            deleted_user = delete_result.data[0]
            print(f"✅ User deleted: {deleted_user.get('username', 'unknown')} ({deleted_user.get('email', 'unknown')})")
        else:
            # Double-check user is actually gone
            print(f"⚠️  Delete returned no data, verifying...")
            verify = supabase.table("users").select("id").eq("id", user_id).execute()
            if verify.data and len(verify.data) > 0:
                raise Exception(f"User {user_id} still exists after deletion")
            print(f"✅ User {user_id} verified deleted")
        
        # Clear cache
        try:
            from services.cache_service import invalidate_user_cache
            invalidate_user_cache(user_id)
            print("💾 Cache cleared")
        except Exception as e:
            print(f"⚠️  Cache clear failed (non-critical): {e}")
        
        print(f"✅ Account deletion completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR deleting user: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Failed to delete user: {str(e)}")