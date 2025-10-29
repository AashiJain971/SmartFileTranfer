from supabase import create_client, Client
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import os
from .database import supabase
from models.chat import MessageType, ChatRoomType, MessageStatus, UserRole

class ChatCRUD:
    """CRUD operations for chat functionality integrated with existing file system"""
    
    # ✅ CHAT ROOM OPERATIONS
    
    @staticmethod
    async def create_chat_room(creator_id: str, room_type: str, name: Optional[str] = None) -> Dict[str, Any]:
        """Create a new chat room"""
        try:
            room_data = {
                "type": room_type,
                "created_by": creator_id,
                "name": name
            }
            
            result = supabase.table("chat_rooms").insert(room_data).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            raise Exception("Failed to create chat room - no data returned")
        except Exception as e:
            raise Exception(f"Failed to create chat room: {str(e)}")
    
    @staticmethod
    async def get_chat_room_by_id(room_id: str) -> Optional[Dict[str, Any]]:
        """Get chat room by ID"""
        try:
            result = supabase.table("chat_rooms")\
                .select("*, users!created_by(username)")\
                .eq("id", room_id)\
                .single()\
                .execute()
            
            return result.data if result.data else None
        except Exception:
            return None
    
    @staticmethod
    async def add_room_members(room_id: str, user_ids: List[str], role: str = "member") -> bool:
        """Add members to a chat room"""
        try:
            members_data = [
                {"room_id": room_id, "user_id": user_id, "role": role}
                for user_id in user_ids
            ]
            
            result = supabase.table("chat_room_members").insert(members_data).execute()
            return result.data is not None and len(result.data) == len(user_ids)
        except Exception as e:
            print(f"Error adding room members: {e}")
            return False
    
    @staticmethod
    async def get_user_chat_rooms(user_id: str) -> List[Dict[str, Any]]:
        """Get all chat rooms for a user with last message and unread count"""
        try:
            # Get rooms where user is a member
            result = supabase.table("chat_room_members")\
                .select("room_id, role, joined_at, chat_rooms(*, users!created_by(username))")\
                .eq("user_id", user_id)\
                .execute()
            
            rooms_with_info = []
            for member in result.data:
                room = member["chat_rooms"]
                if room:
                    # Get last message for this room
                    last_message = await ChatCRUD.get_last_message_for_room(room["id"])
                    
                    # Get unread count for this user
                    unread_count = await ChatCRUD.get_unread_count(room["id"], user_id)
                    
                    # Get all room members
                    members = await ChatCRUD.get_room_members_detailed(room["id"])
                    
                    room_info = {
                        **room,
                        "user_role": member["role"],
                        "user_joined_at": member["joined_at"],
                        "last_message": last_message,
                        "unread_count": unread_count,
                        "members": members
                    }
                    rooms_with_info.append(room_info)
            
            # Sort by last message time or creation time
            rooms_with_info.sort(
                key=lambda x: x["last_message"]["created_at"] if x["last_message"] else x["created_at"],
                reverse=True
            )
            
            return rooms_with_info
        except Exception as e:
            print(f"Error getting user chat rooms: {e}")
            return []
    
    @staticmethod
    async def get_room_members_detailed(room_id: str) -> List[Dict[str, Any]]:
        """Get detailed information about room members"""
        try:
            result = supabase.table("chat_room_members")\
                .select("user_id, role, joined_at, users(username, email)")\
                .eq("room_id", room_id)\
                .execute()
            
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
            
            return members
        except Exception as e:
            print(f"Error getting room members: {e}")
            return []
    
    @staticmethod
    async def is_user_in_room(user_id: str, room_id: str) -> bool:
        """Check if user is a member of the chat room"""
        try:
            result = supabase.table("chat_room_members")\
                .select("id")\
                .eq("user_id", user_id)\
                .eq("room_id", room_id)\
                .execute()
            
            return len(result.data) > 0
        except Exception:
            return False
    
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
    async def send_file_message(sender_id: str, room_id: str, file_session_id: int,
                              file_path: str, file_name: str, file_size: int, 
                              file_hash: str, reply_to_id: Optional[str] = None) -> Dict[str, Any]:
        """Send a file message linked to existing file upload system"""
        try:
            # Determine if it's an image or regular file
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'}
            file_extension = os.path.splitext(file_name.lower())[1]
            message_type = MessageType.IMAGE.value if file_extension in image_extensions else MessageType.FILE.value
            
            message_data = {
                "room_id": room_id,
                "sender_id": sender_id,
                "message_type": message_type,
                "file_session_id": file_session_id,  # ✅ LINKS TO EXISTING UPLOAD SYSTEM
                "file_path": file_path,
                "file_name": file_name,
                "file_size": file_size,
                "file_hash": file_hash,  # ✅ USES EXISTING HASH VERIFICATION
                "reply_to_id": reply_to_id
            }
            
            result = supabase.table("messages").insert(message_data).execute()
            if result.data and len(result.data) > 0:
                message = result.data[0]
                
                # Mark as sent for sender
                await ChatCRUD.mark_message_status(message["id"], sender_id, MessageStatus.SENT.value)
                
                return message
            raise Exception("Failed to send file message")
        except Exception as e:
            raise Exception(f"Failed to send file message: {str(e)}")
    
    @staticmethod
    async def get_room_messages(room_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get messages from a chat room with sender info and reply context"""
        try:
            result = supabase.table("messages")\
                .select("""
                    *, 
                    users!sender_id(username), 
                    reply_to:messages!reply_to_id(id, content, message_type, users!sender_id(username))
                """)\
                .eq("room_id", room_id)\
                .order("created_at", desc=False)\
                .range(offset, offset + limit - 1)\
                .execute()
            
            messages = []
            for msg in result.data:
                # Format the message with sender username
                message = {
                    **msg,
                    "sender_username": msg["users"]["username"] if msg["users"] else "Unknown"
                }
                
                # Format reply information if present
                if msg.get("reply_to"):
                    reply = msg["reply_to"]
                    message["reply_to"] = {
                        **reply,
                        "sender_username": reply["users"]["username"] if reply.get("users") else "Unknown"
                    }
                
                messages.append(message)
            
            return messages
        except Exception as e:
            print(f"Error getting room messages: {e}")
            return []
    
    @staticmethod
    async def get_message_by_id(message_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific message by ID"""
        try:
            result = supabase.table("messages")\
                .select("*, users!sender_id(username)")\
                .eq("id", message_id)\
                .single()\
                .execute()
            
            if result.data:
                message = result.data
                message["sender_username"] = message["users"]["username"] if message["users"] else "Unknown"
                return message
            return None
        except Exception:
            return None
    
    @staticmethod
    async def get_last_message_for_room(room_id: str) -> Optional[Dict[str, Any]]:
        """Get the last message sent in a room"""
        try:
            result = supabase.table("messages")\
                .select("*, users!sender_id(username)")\
                .eq("room_id", room_id)\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            if result.data and len(result.data) > 0:
                message = result.data[0]
                message["sender_username"] = message["users"]["username"] if message["users"] else "Unknown"
                return message
            return None
        except Exception:
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