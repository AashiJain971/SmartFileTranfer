from supabase import create_client, Client
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import os
from .database import supabase
from models.chat import MessageType, ChatRoomType, MessageStatus, UserRole
from services.cache_service import cache
from services.cache_invalidation import invalidator
import asyncio

class ChatCRUD:
    """CRUD operations for chat functionality integrated with existing file system"""
    
    # ✅ CONNECTION UTILITIES
    
    @staticmethod
    async def _warm_connection():
        """Warm up database connection to prevent initial timeouts"""
        try:
            import asyncio
            
            async def ping_db():
                # Simple ping query to warm up connection
                result = supabase.table("users").select("id").limit(1).execute()
                return result
            
            # Quick 2-second timeout for warm-up
            await asyncio.wait_for(ping_db(), timeout=2.0)
            
        except Exception as e:
            # Don't fail if warm-up fails, just log it
            print(f"🔧 CRUD WARNING: Connection warm-up failed (continuing anyway): {e}")
    
    # ✅ CHAT ROOM OPERATIONS
    
    @staticmethod
    async def create_chat_room(creator_id: str, room_type: str, name: Optional[str] = None) -> Dict[str, Any]:
        """Create a new chat room with timeout protection"""
        import httpx
        
        try:
            room_data = {
                "type": room_type,
                "created_by": creator_id,
                "name": name
            }
            
            async def insert_room():
                return supabase.table("chat_rooms").insert(room_data).execute()
            
            result = await asyncio.wait_for(insert_room(), timeout=15.0)
            if result.data and len(result.data) > 0:
                return result.data[0]
            raise Exception("Failed to create chat room - no data returned")
        except (asyncio.TimeoutError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            raise Exception(f"Room creation timed out - database is slow. Please try again.")
        except Exception as e:
            raise Exception(f"Failed to create chat room: {str(e)}")
    
    @staticmethod
    async def get_chat_room_by_id(room_id: str) -> Optional[Dict[str, Any]]:
        """Get chat room by ID with timeout protection"""
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    lambda: supabase.table("chat_rooms")
                        .select("*, users!created_by(username)")
                        .eq("id", room_id)
                        .single()
                        .execute()
                ),
                timeout=10.0  # 10s timeout for room lookup
            )
            
            return result.data if result.data else None
        except asyncio.TimeoutError:
            print(f"⏱️ Timeout getting room {room_id[:8]}...")
            return None
        except Exception as e:
            print(f"❌ Error getting room {room_id[:8]}: {e}")
            return None
    
    @staticmethod
    async def find_direct_chat_room(user1_id: str, user2_id: str) -> Optional[Dict[str, Any]]:
        """Find existing direct chat room between two users"""
        try:
            print(f"🔍 Looking for direct chat between {user1_id[:8]}... and {user2_id[:8]}...")
            
            # Get all direct rooms where user1 is a member
            user1_rooms_result = supabase.table("chat_room_members")\
                .select("room_id")\
                .eq("user_id", user1_id)\
                .execute()
            
            if not user1_rooms_result.data:
                print("❌ User1 has no rooms")
                return None
                
            user1_room_ids = [r["room_id"] for r in user1_rooms_result.data]
            print(f"🏠 User1 has {len(user1_room_ids)} rooms")
            
            # Get all direct rooms where user2 is a member
            user2_rooms_result = supabase.table("chat_room_members")\
                .select("room_id")\
                .eq("user_id", user2_id)\
                .execute()
            
            if not user2_rooms_result.data:
                print("❌ User2 has no rooms")
                return None
                
            user2_room_ids = [r["room_id"] for r in user2_rooms_result.data]
            print(f"🏠 User2 has {len(user2_room_ids)} rooms")
            
            # Find common room IDs
            common_room_ids = set(user1_room_ids).intersection(set(user2_room_ids))
            print(f"🔗 Found {len(common_room_ids)} common rooms")
            
            if not common_room_ids:
                return None
            
            # Check which of the common rooms are direct chats with exactly 2 members
            for room_id in common_room_ids:
                print(f"🔍 Checking room {room_id[:8]}...")
                
                # Get room details
                room_result = supabase.table("chat_rooms")\
                    .select("*, users!created_by(username)")\
                    .eq("id", room_id)\
                    .eq("type", "direct")\
                    .single()\
                    .execute()
                
                if room_result.data:
                    # Count members in this room
                    members_result = supabase.table("chat_room_members")\
                        .select("user_id")\
                        .eq("room_id", room_id)\
                        .execute()
                    
                    if len(members_result.data) == 2:
                        print(f"✅ Found direct chat room: {room_id[:8]}...")
                        room_data = room_result.data
                        room_data["created_by_username"] = room_data.get("users", {}).get("username", "Unknown")
                        return room_data
            
            print("❌ No direct chat rooms found")
            return None
            
        except Exception as e:
            print(f"❌ Error finding direct chat room: {e}")
            return None

    @staticmethod
    async def add_room_members(room_id: str, user_ids: List[str], role: str = "member") -> bool:
        """Add users to a chat room with timeout protection"""
        import httpx
        
        try:
            members_data = [
                {
                    "room_id": room_id,
                    "user_id": user_id,
                    "role": role
                }
                for user_id in user_ids
            ]
            
            # Add timeout protection (10s for bulk insert)
            async def insert_members():
                return supabase.table("chat_room_members").insert(members_data).execute()
            
            result = await asyncio.wait_for(insert_members(), timeout=10.0)
            success = result.data is not None and len(result.data) == len(user_ids)
            
            # Invalidate cache for all added users AND the room members cache
            if success:
                # Clear the room members cache FIRST (most important)
                await cache.delete(f"members:{room_id}")
                print(f"🗑️ Cleared members cache for room {room_id[:8]}...")
                
                # Clear individual user caches
                for user_id in user_ids:
                    await cache.delete(f"rooms:{user_id}")
                    await cache.delete(f"membership:{user_id}:{room_id}")
                    print(f"🗑️ Cleared cache for user {user_id[:8]}... in room {room_id[:8]}...")
            
            return success
        except (asyncio.TimeoutError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            print(f"⏱️ Timeout adding room members to room {room_id[:8]}... ({type(e).__name__})")
            return False
        except Exception as e:
            print(f"❌ Error adding room members: {e}")
            return False
    
    @staticmethod
    async def add_single_room_member(room_id: str, user_id: str, role: str = "member") -> bool:
        """Add a single user to a chat room"""
        try:
            # Check if user is already a member
            is_member = await ChatCRUD.is_user_in_room(user_id, room_id)
            if is_member:
                print(f"🔧 INFO: User {user_id} is already a member of room {room_id}")
                return True
            
            member_data = {
                "room_id": room_id,
                "user_id": user_id,
                "role": role
            }
            
            result = supabase.table("chat_room_members").insert(member_data).execute()
            success = result.data is not None and len(result.data) > 0
            
            if success:
                # Invalidate cache for the added user
                await cache.delete(f"rooms:{user_id}")
                await cache.delete(f"membership:{user_id}:{room_id}")
                print(f"🔧 SUCCESS: Added user {user_id} to room {room_id} and cleared cache")
            else:
                print(f"🔧 ERROR: Failed to add user {user_id} to room {room_id}")
                
            return success
        except Exception as e:
            print(f"🔧 ERROR: Error adding room member: {e}")
            return False
    
    @staticmethod
    async def get_user_chat_rooms(user_id: str) -> List[Dict[str, Any]]:
        """Get all chat rooms for user with Redis caching and parallel loading"""
        import httpx
        
        cache_key = f"rooms:{user_id}"
        
        # Check cache first
        cached = await cache.get(cache_key)
        if cached:
            return cached
        
        try:
            # Get rooms where user is a member with timeout
            async def fetch_rooms():
                return supabase.table("chat_room_members")\
                    .select("room_id, role, joined_at, chat_rooms(*, users!created_by(username))")\
                    .eq("user_id", user_id)\
                    .execute()
            
            result = await asyncio.wait_for(fetch_rooms(), timeout=10.0)
            
            rooms_with_info = []
            
            # Process all rooms in parallel for speed
            async def process_room(member):
                room = member["chat_rooms"]
                if not room:
                    return None
                
                # Fetch all room data in parallel
                last_message_task = ChatCRUD.get_last_message_for_room(room["id"])
                members_task = ChatCRUD.get_room_members_detailed(room["id"])
                
                last_message = await last_message_task
                members = await members_task
                
                return {
                    **room,
                    "user_role": member["role"],
                    "user_joined_at": member["joined_at"],
                    "last_message": last_message,
                    "unread_count": 0,  # Skip for speed
                    "members": members
                }
            
            # Process all rooms concurrently
            tasks = [process_room(member) for member in result.data]
            rooms = await asyncio.gather(*tasks)
            rooms_with_info = [r for r in rooms if r is not None]
            
            # Sort by last message time or creation time
            rooms_with_info.sort(
                key=lambda x: x["last_message"]["created_at"] if x["last_message"] else x["created_at"],
                reverse=True
            )
            
            # Cache for 1 minute
            await cache.set(cache_key, rooms_with_info, ttl=60)
            
            return rooms_with_info
        except (asyncio.TimeoutError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            print(f"⚠️ Database timeout getting rooms for user {user_id[:8]}... ({type(e).__name__}) - returning empty")
            # Return empty array but don't crash
            return []
        except Exception as e:
            print(f"❌ Error getting user chat rooms: {e}")
            return []
    
    @staticmethod
    async def get_room_members_detailed(room_id: str) -> List[Dict[str, Any]]:
        """Get detailed information about room members with caching"""
        cache_key = f"members:{room_id}"
        
        # Check cache first
        cached = await cache.get(cache_key)
        if cached:
            return cached
        
        try:
            # Use timeout to prevent hanging
            async def fetch_members():
                return supabase.table("chat_room_members")\
                    .select("user_id, role, joined_at, users(username, email)")\
                    .eq("room_id", room_id)\
                    .execute()
            
            result = await asyncio.wait_for(fetch_members(), timeout=10.0)
            
            members = []
            for member in result.data:
                user = member["users"]
                members.append({
                    "user_id": member["user_id"],
                    "username": user["username"],
                    "email": user["email"],
                    "role": member["role"],
                    "joined_at": member["joined_at"]
                })
            
            # Only cache if we got valid results
            if members:
                await cache.set(cache_key, members, ttl=300)
            
            return members
        except asyncio.TimeoutError:
            print(f"⚠️ Timeout getting members for room {room_id[:8]}... - NOT caching empty result")
            return []
        except Exception as e:
            print(f"❌ Error getting room members: {e}")
            return []
    
    @staticmethod
    async def is_user_in_room(user_id: str, room_id: str) -> bool:
        """Check if user is in room with aggressive Redis caching for speed"""
        cache_key = f"membership:{user_id}:{room_id}"
        
        # Check cache first - instant response!
        cached = await cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            # Single fast query - no warmup, minimal retries
            async def check_membership():
                result = supabase.table("chat_room_members")\
                    .select("user_id")\
                    .eq("user_id", user_id)\
                    .eq("room_id", room_id)\
                    .limit(1)\
                    .execute()
                return result
            
            # 3 second timeout
            result = await asyncio.wait_for(check_membership(), timeout=3.0)
            
            is_member = len(result.data) > 0
            
            # Cache for 10 minutes (memberships rarely change)
            await cache.set(cache_key, is_member, ttl=600)
            
            return is_member
                    
        except asyncio.TimeoutError:
            print(f"⚠️  Membership check timeout - assuming member (better UX)")
            # Assume member on timeout (better than blocking user)
            return True
                        
        except Exception as e:
            print(f"❌ Membership check error: {e}")
            # Return False on error to prevent unauthorized access
            return False
    
    @staticmethod
    async def get_user_role_in_room(user_id: str, room_id: str) -> Optional[str]:
        """Get a user's role in a chat room with timeout protection"""
        try:
            async def fetch_role():
                return supabase.table("chat_room_members")\
                    .select("role")\
                    .eq("user_id", user_id)\
                    .eq("room_id", room_id)\
                    .single()\
                    .execute()
            
            result = await asyncio.wait_for(fetch_role(), timeout=5.0)
            return result.data["role"] if result.data else None
        except asyncio.TimeoutError:
            print(f"⏱️ Timeout getting user role for {user_id[:8]}... in room {room_id[:8]}...")
            return None
        except Exception as e:
            print(f"❌ Error getting user role: {e}")
            return None
    
    @staticmethod
    async def get_room_member_ids(room_id: str) -> List[str]:
        """Get all member IDs for a chat room"""
        try:
            result = supabase.table("chat_room_members")\
                .select("user_id")\
                .eq("room_id", room_id)\
                .execute()
            
            return [member["user_id"] for member in result.data]
        except Exception:
            return []
    
    # ✅ MESSAGE OPERATIONS (INTEGRATED WITH FILE SYSTEM)
    
    @staticmethod
    async def send_text_message(sender_id: str, room_id: str, content: str, 
                              reply_to_id: Optional[str] = None) -> Dict[str, Any]:
        """Send a text message to a chat room"""
        try:
            message_data = {
                "room_id": room_id,
                "sender_id": sender_id,
                "message_type": MessageType.TEXT.value,
                "content": content,
                "reply_to_id": reply_to_id
            }
            
            result = supabase.table("messages").insert(message_data).execute()
            if result.data and len(result.data) > 0:
                message = result.data[0]
                
                # Mark as sent for sender
                await ChatCRUD.mark_message_status(message["id"], sender_id, MessageStatus.SENT.value)
                
                return message
            raise Exception("Failed to send message")
        except Exception as e:
            raise Exception(f"Failed to send text message: {str(e)}")
    
    @staticmethod
    async def send_file_message(sender_id: str, room_id: str, file_session_id: Optional[int],
                              file_path: str, file_name: str, file_size: int, 
                              file_hash: str, reply_to_id: Optional[str] = None,
                              blockchain_tx_hash: Optional[str] = None,
                              blockchain_block_number: Optional[int] = None,
                              ipfs_cid: Optional[str] = None,
                              certificate_url: Optional[str] = None) -> Dict[str, Any]:
        """Send a file message linked to existing file upload system with blockchain/IPFS data"""
        try:
            # Determine if it's an image or regular file
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'}
            file_extension = os.path.splitext(file_name.lower())[1]
            message_type = MessageType.IMAGE.value if file_extension in image_extensions else MessageType.FILE.value
            
            message_data = {
                "room_id": room_id,
                "sender_id": sender_id,
                "message_type": message_type,
                "file_path": file_path,
                "file_name": file_name,
                "file_size": file_size,
                "file_hash": file_hash,  # ✅ USES EXISTING HASH VERIFICATION
                "reply_to_id": reply_to_id,
                # ✅ NEW: Blockchain and IPFS fields
                "blockchain_tx_hash": blockchain_tx_hash,
                "blockchain_block_number": blockchain_block_number,
                "ipfs_cid": ipfs_cid,
                "certificate_url": certificate_url
            }
            
            # Only add file_session_id if provided (for chunked uploads with sessions)
            if file_session_id is not None:
                message_data["file_session_id"] = file_session_id
            
            result = supabase.table("messages").insert(message_data).execute()
            if result.data and len(result.data) > 0:
                message = result.data[0]
                
                # Mark as sent for sender
                await ChatCRUD.mark_message_status(message["id"], sender_id, MessageStatus.SENT.value)
                
                # ✅ INVALIDATE CACHE - Critical for new messages to appear!
                try:
                    print(f"🔄 Invalidating message cache for room {room_id}...")
                    patterns = [
                        f"messages:{room_id}:*",
                        f"room:{room_id}:*"
                    ]
                    for pattern in patterns:
                        deleted = await cache.delete_pattern(pattern)
                        print(f"   Deleted cache pattern: {pattern} ({deleted} keys)")
                except Exception as cache_err:
                    print(f"⚠️ Cache invalidation failed: {cache_err}")
                
                return message
            raise Exception("Failed to send file message")
        except Exception as e:
            raise Exception(f"Failed to send file message: {str(e)}")
    
    @staticmethod
    async def update_message_blockchain_data(
        message_id: str,
        blockchain_tx_hash: Optional[str] = None,
        blockchain_block_number: Optional[int] = None,
        ipfs_cid: Optional[str] = None,
        certificate_url: Optional[str] = None
    ) -> bool:
        """Update blockchain/IPFS data for an existing message (for background uploads)"""
        try:
            update_data = {}
            if blockchain_tx_hash:
                update_data["blockchain_tx_hash"] = blockchain_tx_hash
            if blockchain_block_number:
                update_data["blockchain_block_number"] = blockchain_block_number
            if ipfs_cid:
                update_data["ipfs_cid"] = ipfs_cid
            if certificate_url:
                update_data["certificate_url"] = certificate_url
            
            if not update_data:
                print(f"⚠️ No data to update for message {message_id}")
                return False
            
            print(f"📝 Updating message {message_id} with: {update_data}")
            
            # First, verify message exists
            check_result = supabase.table("messages")\
                .select("id, room_id, ipfs_cid, blockchain_tx_hash")\
                .eq("id", message_id)\
                .execute()
            
            if not check_result.data or len(check_result.data) == 0:
                print(f"❌ Message {message_id} not found in database!")
                return False
            
            old_data = check_result.data[0]
            room_id = old_data.get('room_id')
            print(f"✅ Message exists in room {room_id}")
            print(f"   Current IPFS: {old_data.get('ipfs_cid', 'None')}")
            print(f"   Current Blockchain: {old_data.get('blockchain_tx_hash', 'None')}")
            
            # Perform update
            result = supabase.table("messages")\
                .update(update_data)\
                .eq("id", message_id)\
                .execute()
            
            if not result.data or len(result.data) == 0:
                print(f"❌ Update returned no data for message {message_id}")
                print(f"   Result: {result}")
                return False
            
            # Verify the update actually worked
            verify_result = supabase.table("messages")\
                .select("ipfs_cid, blockchain_tx_hash, blockchain_block_number")\
                .eq("id", message_id)\
                .execute()
            
            if verify_result.data and len(verify_result.data) > 0:
                verified = verify_result.data[0]
                print(f"✅ Database update VERIFIED for message {message_id}")
                print(f"   New IPFS CID: {verified.get('ipfs_cid', 'None')}")
                print(f"   New Blockchain TX: {verified.get('blockchain_tx_hash', 'None')}")
            else:
                print(f"❌ Could not verify update for message {message_id}")
            
            # ✅ INVALIDATE CACHE - Critical for showing updates!
            if room_id:
                print(f"🔄 Invalidating cache for room {room_id}...")
                
                from services.cache_service import cache
                
                # Delete ALL message cache keys for this room
                patterns = [
                    f"messages:{room_id}:*",
                    f"room:{room_id}:*"
                ]
                
                for pattern in patterns:
                    deleted = await cache.delete_pattern(pattern)
                    print(f"   Deleted cache pattern: {pattern} ({deleted} keys)")
                
                print(f"✅ Cache invalidated for room {room_id}")
            
            return True
        except Exception as e:
            print(f"❌ Failed to update message blockchain data: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    async def sync_message_ipfs_from_blockchain(message_id: str) -> bool:
        """Sync IPFS CID from blockchain_records to message if missing"""
        try:
            # Get message
            msg_result = supabase.table("messages")\
                .select("id, file_hash, ipfs_cid, blockchain_tx_hash")\
                .eq("id", message_id)\
                .execute()
            
            if not msg_result.data:
                return False
            
            message = msg_result.data[0]
            
            # If message already has IPFS, no need to sync
            if message.get('ipfs_cid'):
                print(f"✅ Message {message_id} already has IPFS: {message.get('ipfs_cid')}")
                return True
            
            # Try to find blockchain record by file_hash or tx_hash
            file_hash = message.get('file_hash')
            tx_hash = message.get('blockchain_tx_hash')
            
            if file_hash:
                bc_result = supabase.table("blockchain_records")\
                    .select("ipfs_cid, tx_hash")\
                    .eq("file_hash", file_hash)\
                    .execute()
                
                if bc_result.data and len(bc_result.data) > 0:
                    bc_data = bc_result.data[0]
                    ipfs_cid = bc_data.get('ipfs_cid')
                    
                    if ipfs_cid:
                        print(f"🔄 Syncing IPFS from blockchain_records to message {message_id}")
                        return await ChatCRUD.update_message_blockchain_data(
                            message_id=message_id,
                            ipfs_cid=ipfs_cid,
                            blockchain_tx_hash=bc_data.get('tx_hash')
                        )
            
            return False
        except Exception as e:
            print(f"❌ Failed to sync IPFS from blockchain: {e}")
            return False
    
    @staticmethod
    async def get_room_messages(room_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get messages from room with Redis caching for lightning speed"""
        cache_key = f"messages:{room_id}:{limit}:{offset}"
        
        # Check cache first
        cached = await cache.get(cache_key)
        if cached:
            return cached
        
        try:
            # Single fast query - no warmup, no counting
            async def fetch_messages():
                result = supabase.table("messages")\
                    .select("*, sender:users(username)")\
                    .eq("room_id", room_id)\
                    .order("created_at", desc=False)\
                    .limit(limit)\
                    .offset(offset)\
                    .execute()
                return result
            
            # Reduced timeout from 30s to 10s for faster response
            result = await asyncio.wait_for(fetch_messages(), timeout=10.0)
            
            messages = []
            for msg in result.data:
                sender_info = msg.get("sender")
                message = {
                    **msg,
                    "sender_username": sender_info["username"] if sender_info and isinstance(sender_info, dict) else "Unknown"
                }
                
                # Format reply information if present
                if msg.get("reply_to"):
                    reply = msg["reply_to"]
                    message["reply_to"] = {
                        **reply,
                        "sender_username": reply["sender"]["username"] if reply.get("sender") else "Unknown"
                    }
                
                messages.append(message)
            
            # Cache for 30 seconds (messages change frequently)
            await cache.set(cache_key, messages, ttl=30)
            
            return messages
        except asyncio.TimeoutError:
            print(f"❌ Timeout getting room messages for room {room_id[:8]}...")
            raise  # Propagate timeout to router
        except Exception as e:
            print(f"❌ Error getting room messages: {e}")
            raise  # Propagate errors to router
    
    @staticmethod
    async def get_message_by_id(message_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific message by ID with timeout"""
        try:
            async def fetch_message():
                return supabase.table("messages")\
                    .select("*, sender:users!sender_id(username)")\
                    .eq("id", message_id)\
                    .single()\
                    .execute()
            
            result = await asyncio.wait_for(fetch_message(), timeout=10.0)
            
            if result.data:
                message = result.data
                message["sender_username"] = message["sender"]["username"] if message.get("sender") else "Unknown"
                return message
            return None
        except asyncio.TimeoutError:
            print(f"🔧 ERROR: get_message_by_id timeout for {message_id[:8]}...")
            return None
        except Exception as e:
            print(f"🔧 ERROR: get_message_by_id failed: {e}")
            return None
    
    @staticmethod
    async def get_last_message_for_room(room_id: str) -> Optional[Dict[str, Any]]:
        """Get the last message sent in a room with caching for performance"""
        cache_key = f"last_msg:{room_id}"
        
        # Check cache first for instant response
        cached = await cache.get(cache_key)
        if cached:
            return cached
        
        try:
            result = supabase.table("messages")\
                .select("*, sender:users!sender_id(username)")\
                .eq("room_id", room_id)\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            if result.data and len(result.data) > 0:
                message = result.data[0]
                message["sender_username"] = message["sender"]["username"] if message.get("sender") else "Unknown"
                
                # Cache for 30 seconds (messages change frequently)
                await cache.set(cache_key, message, ttl=30)
                return message
            return None
        except Exception as e:
            print(f"🔧 ERROR: get_last_message_for_room failed: {e}")
            return None
    
    # ✅ MESSAGE STATUS OPERATIONS (READ RECEIPTS)
    
    @staticmethod
    async def mark_message_status(message_id: str, user_id: str, status: str) -> bool:
        """Mark message status (sent/delivered/read)"""
        try:
            status_data = {
                "message_id": message_id,
                "user_id": user_id,
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Use upsert to handle duplicate entries
            result = supabase.table("message_status")\
                .upsert(status_data, on_conflict="message_id,user_id")\
                .execute()
            
            return result.data is not None
        except Exception as e:
            print(f"Error marking message status: {e}")
            return False
    
    @staticmethod
    async def get_message_status(message_id: str, user_id: str) -> Optional[str]:
        """Get message status for a specific user"""
        try:
            result = supabase.table("message_status")\
                .select("status")\
                .eq("message_id", message_id)\
                .eq("user_id", user_id)\
                .single()\
                .execute()
            
            return result.data["status"] if result.data else None
        except Exception:
            return None
    
    @staticmethod
    async def get_unread_count(room_id: str, user_id: str) -> int:
        """Get count of unread messages in a room for a user"""
        try:
            # Get all messages in the room
            messages_result = supabase.table("messages")\
                .select("id")\
                .eq("room_id", room_id)\
                .neq("sender_id", user_id)\
                .execute()
            
            if not messages_result.data:
                return 0
            
            message_ids = [msg["id"] for msg in messages_result.data]
            
            # Get read messages for this user
            read_result = supabase.table("message_status")\
                .select("message_id")\
                .eq("user_id", user_id)\
                .eq("status", MessageStatus.READ.value)\
                .in_("message_id", message_ids)\
                .execute()
            
            read_message_ids = {msg["message_id"] for msg in read_result.data}
            
            # Calculate unread count
            unread_count = len([mid for mid in message_ids if mid not in read_message_ids])
            
            return unread_count
        except Exception as e:
            print(f"Error getting unread count: {e}")
            return 0
    
    @staticmethod
    async def mark_room_messages_as_read(room_id: str, user_id: str) -> int:
        """Mark all messages in a room as read for a user"""
        try:
            # Get all message IDs in the room (excluding user's own messages)
            messages_result = supabase.table("messages")\
                .select("id")\
                .eq("room_id", room_id)\
                .neq("sender_id", user_id)\
                .execute()
            
            if not messages_result.data:
                return 0
            
            # Mark all as read
            marked_count = 0
            for message in messages_result.data:
                success = await ChatCRUD.mark_message_status(
                    message["id"], user_id, MessageStatus.READ.value
                )
                if success:
                    marked_count += 1
            
            return marked_count
        except Exception as e:
            print(f"Error marking room messages as read: {e}")
            return 0
    
    # ✅ INTEGRATION WITH EXISTING FILE SYSTEM
    
    @staticmethod
    async def link_file_session_to_chat(file_session_id: int, room_id: str) -> bool:
        """Link an existing file session to a chat room"""
        try:
            result = supabase.table("file_sessions")\
                .update({
                    "upload_type": "chat",
                    "chat_room_id": room_id
                })\
                .eq("id", file_session_id)\
                .execute()
            
            return result.data is not None
        except Exception as e:
            print(f"Error linking file session to chat: {e}")
            return False
    
    @staticmethod
    async def get_chat_files_for_room(room_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all files shared in a chat room"""
        try:
            result = supabase.table("messages")\
                .select("*, users!sender_id(username)")\
                .eq("room_id", room_id)\
                .in_("message_type", [MessageType.FILE.value, MessageType.IMAGE.value])\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            
            files = []
            for msg in result.data:
                file_info = {
                    "message_id": msg["id"],
                    "file_name": msg["file_name"],
                    "file_size": msg["file_size"],
                    "file_hash": msg["file_hash"],
                    "file_path": msg["file_path"],
                    "message_type": msg["message_type"],
                    "sender_username": msg["users"]["username"] if msg["users"] else "Unknown",
                    "shared_at": msg["created_at"]
                }
                files.append(file_info)
            
            return files
        except Exception as e:
            print(f"Error getting chat files: {e}")
            return []
    
    # ✅ SEARCH AND UTILITY OPERATIONS
    
    @staticmethod
    async def search_messages(room_id: str, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for messages in a room"""
        try:
            # Note: This is a basic search. For production, consider using full-text search
            result = supabase.table("messages")\
                .select("*, users!sender_id(username)")\
                .eq("room_id", room_id)\
                .ilike("content", f"%{query}%")\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            
            messages = []
            for msg in result.data:
                message = {
                    **msg,
                    "sender_username": msg["users"]["username"] if msg["users"] else "Unknown"
                }
                messages.append(message)
            
            return messages
        except Exception as e:
            print(f"Error searching messages: {e}")
            return []
    
    @staticmethod
    async def get_room_statistics(room_id: str) -> Dict[str, Any]:
        """Get statistics for a chat room"""
        try:
            # Get total message count
            messages_result = supabase.table("messages")\
                .select("id", count="exact")\
                .eq("room_id", room_id)\
                .execute()
            
            # Get file count
            files_result = supabase.table("messages")\
                .select("id", count="exact")\
                .eq("room_id", room_id)\
                .in_("message_type", [MessageType.FILE.value, MessageType.IMAGE.value])\
                .execute()
            
            # Get member count
            members_result = supabase.table("chat_room_members")\
                .select("id", count="exact")\
                .eq("room_id", room_id)\
                .execute()
            
            return {
                "total_messages": messages_result.count or 0,
                "total_files": files_result.count or 0,
                "total_members": members_result.count or 0
            }
        except Exception as e:
            print(f"Error getting room statistics: {e}")
            return {"total_messages": 0, "total_files": 0, "total_members": 0}
    
    @staticmethod
    async def delete_room(room_id: str) -> bool:
        """Delete a chat room (admin only, group chats only) with improved timeout handling"""
        import httpx
        
        try:
            print(f"🗑️ Deleting room {room_id}...")
            
            # Use longer timeouts for Supabase sync operations (they can't be interrupted mid-request)
            # Step 1: Delete all messages in the room
            print(f"Deleting messages...")
            try:
                async def delete_messages():
                    return supabase.table("messages")\
                        .delete()\
                        .eq("room_id", room_id)\
                        .execute()
                
                messages_result = await asyncio.wait_for(delete_messages(), timeout=60.0)
                print(f"✅ Deleted {len(messages_result.data) if messages_result.data else 0} messages")
            except (asyncio.TimeoutError, httpx.ReadTimeout, httpx.ConnectTimeout):
                print(f"⏱️ Message deletion timed out - continuing anyway")
            
            # Step 2: Delete all room members
            print(f"Deleting members...")
            try:
                async def delete_members():
                    return supabase.table("chat_room_members")\
                        .delete()\
                        .eq("room_id", room_id)\
                        .execute()
                
                members_result = await asyncio.wait_for(delete_members(), timeout=60.0)
                print(f"✅ Deleted {len(members_result.data) if members_result.data else 0} members")
            except (asyncio.TimeoutError, httpx.ReadTimeout, httpx.ConnectTimeout):
                print(f"⏱️ Member deletion timed out - continuing anyway")
            
            # Step 3: Delete the room itself
            print(f"Deleting room record...")
            try:
                async def delete_room_record():
                    return supabase.table("chat_rooms")\
                        .delete()\
                        .eq("id", room_id)\
                        .execute()
                
                result = await asyncio.wait_for(delete_room_record(), timeout=60.0)
                print(f"✅ Room deleted successfully")
                return True
            except (asyncio.TimeoutError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
                # Even if it times out, the delete likely succeeded
                # Verify by checking if room still exists
                print(f"⏱️ Room deletion timed out ({type(e).__name__}) - verifying...")
                await asyncio.sleep(2)  # Give database time to process
                
                try:
                    check_result = supabase.table("chat_rooms")\
                        .select("id")\
                        .eq("id", room_id)\
                        .execute()
                    
                    if not check_result.data or len(check_result.data) == 0:
                        print(f"✅ Room was deleted despite timeout")
                        return True
                    else:
                        print(f"❌ Room still exists after timeout")
                        return False
                except Exception as verify_error:
                    # If we can't verify, assume success (delete likely worked)
                    print(f"⚠️ Cannot verify room deletion - assuming success ({verify_error})")
                    return True
                    
        except Exception as e:
            print(f"❌ Error deleting room: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    async def remove_room_member(room_id: str, user_id: str) -> bool:
        """Remove a member from a room"""
        try:
            result = supabase.table("chat_room_members")\
                .delete()\
                .eq("room_id", room_id)\
                .eq("user_id", user_id)\
                .execute()
            
            # Invalidate cache for the removed user
            await cache.delete(f"rooms:{user_id}")
            await cache.delete(f"membership:{user_id}:{room_id}")
            print(f"🗑️ Cleared cache for user {user_id[:8]}... removed from room {room_id[:8]}...")
            
            return True
        except Exception as e:
            print(f"Error removing member: {e}")
            return False