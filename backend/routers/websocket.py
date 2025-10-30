from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from typing import Dict, Set, Optional, List
import json
import asyncio
from datetime import datetime
from services.auth_service import auth_service
from db.chat_crud import ChatCRUD
from models.chat import MessageType, MessageStatus

router = APIRouter()

class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        # Store active connections by file_id with user info
        self.active_connections: Dict[str, Dict[WebSocket, dict]] = {}
        self.auth_service = auth_service
    
    async def connect(self, websocket: WebSocket, file_id: str, user: dict):
        """Accept WebSocket connection for a specific file upload"""
        await websocket.accept()
        
        if file_id not in self.active_connections:
            self.active_connections[file_id] = {}
        
        self.active_connections[file_id][websocket] = user
        print(f"📡 WebSocket connected for file: {file_id}, user: {user['email']}")
    
    def disconnect(self, websocket: WebSocket, file_id: str):
        """Remove WebSocket connection"""
        if file_id in self.active_connections:
            if websocket in self.active_connections[file_id]:
                user = self.active_connections[file_id][websocket]
                del self.active_connections[file_id][websocket]
                print(f"📡 WebSocket disconnected for file: {file_id}, user: {user['email']}")
            
            # Remove empty sets
            if not self.active_connections[file_id]:
                del self.active_connections[file_id]
    
    async def send_progress_update(self, file_id: str, data: dict):
        """Send progress update to all clients watching this file"""
        if file_id not in self.active_connections:
            return
        
        # Add timestamp to data
        data["timestamp"] = datetime.utcnow().isoformat()
        message = json.dumps(data)
        
        # Send to all connected clients for this file
        disconnected = set()
        for websocket in list(self.active_connections[file_id].keys()):
            try:
                await websocket.send_text(message)
            except Exception:
                # Connection is broken, mark for removal
                disconnected.add(websocket)
        
        # Remove broken connections
        for websocket in disconnected:
            self.disconnect(websocket, file_id)
    
    async def send_error(self, file_id: str, error: str):
        """Send error message to all clients watching this file"""
        await self.send_progress_update(file_id, {
            "type": "error",
            "message": error
        })
    
    async def send_completion(self, file_id: str, file_path: str):
        """Send completion message to all clients watching this file"""
        await self.send_progress_update(file_id, {
            "type": "completed",
            "message": "Upload completed successfully",
            "file_path": file_path
        })

# ✅ ENHANCED CHAT CONNECTION MANAGER
class ChatConnectionManager:
    """Enhanced WebSocket manager for chat rooms with file upload support"""
    
    def __init__(self):
        # Room-based connections: {room_id: {user_id: websocket}}
        self.room_connections: Dict[str, Dict[str, WebSocket]] = {}
        # User-based connections: {user_id: {room_id: websocket}}
        self.user_connections: Dict[str, Dict[str, WebSocket]] = {}
        # User status: {user_id: {"status": "online", "last_seen": datetime}}
        self.user_status: Dict[str, dict] = {}
        self.auth_service = auth_service
        
    async def connect_to_room(self, websocket: WebSocket, room_id: str, user_id: str, username: str):
        """Connect user to a specific chat room"""
        await websocket.accept()
        
        # Initialize room if it doesn't exist
        if room_id not in self.room_connections:
            self.room_connections[room_id] = {}
        
        # Initialize user connections if it doesn't exist
        if user_id not in self.user_connections:
            self.user_connections[user_id] = {}
            
        # Add connection
        self.room_connections[room_id][user_id] = websocket
        self.user_connections[user_id][room_id] = websocket
        
        # Update user status
        self.user_status[user_id] = {
            "status": "online",
            "last_seen": datetime.utcnow(),
            "username": username
        }
        
        print(f"💬 Chat WebSocket connected - Room: {room_id}, User: {username}")
        
        # Notify others in the room that user joined
        await self.broadcast_to_room(room_id, {
            "type": "user_joined",
            "user_id": user_id,
            "username": username,
            "timestamp": datetime.utcnow().isoformat()
        }, exclude_user=user_id)
    
    def disconnect_from_room(self, room_id: str, user_id: str):
        """Disconnect user from a specific room"""
        username = self.user_status.get(user_id, {}).get("username", "Unknown")
        
        if room_id in self.room_connections:
            self.room_connections[room_id].pop(user_id, None)
            
        if user_id in self.user_connections:
            self.user_connections[user_id].pop(room_id, None)
            
        # Update user status if they have no active connections
        if user_id in self.user_connections and len(self.user_connections[user_id]) == 0:
            self.user_status[user_id] = {
                "status": "offline",
                "last_seen": datetime.utcnow(),
                "username": username
            }
        
        print(f"💬 Chat WebSocket disconnected - Room: {room_id}, User: {username}")
    
    async def broadcast_to_room(self, room_id: str, message: dict, exclude_user: str = None):
        """Send message to all users in a room with better error handling"""
        print(f"🔊 Broadcasting to room {room_id[:8]}..., message type: {message.get('type')}")
        print(f"🔍 Room exists in connections: {room_id in self.room_connections}")
        
        if room_id not in self.room_connections:
            print(f"❌ Room {room_id[:8]}... not found in connections")
            return
            
        print(f"👥 Users in room: {list(self.room_connections[room_id].keys())}")
        disconnected_users = []
        sent_count = 0
        
        total_users = len(self.room_connections[room_id])
        
        for user_id, websocket in self.room_connections[room_id].items():
            if exclude_user and user_id == exclude_user:
                print(f"🚫 Excluding sender {user_id[:8]}... from broadcast")
                continue
                
            try:
                # Check if WebSocket is still open before sending
                if websocket.client_state.value == 1:  # OPEN state
                    await websocket.send_text(json.dumps(message))
                    sent_count += 1
                    print(f"✅ Sent to user {user_id[:8]}...")
                else:
                    print(f"❌ WebSocket closed for user {user_id[:8]}..., marking for cleanup")
                    disconnected_users.append(user_id)
            except Exception as e:
                error_msg = str(e)
                if "close frame" in error_msg or "ConnectionClosedError" in error_msg:
                    print(f"❌ WebSocket connection closed for user {user_id[:8]}...")
                else:
                    print(f"❌ Error sending to user {user_id[:8]}...: {e}")
                disconnected_users.append(user_id)
        
        # Clean up disconnected users
        for user_id in disconnected_users:
            self.disconnect_from_room(room_id, user_id)
            
        excluded = 1 if exclude_user else 0
        print(f"💬 Broadcasted to {sent_count}/{total_users - excluded} users in room {room_id[:8]}... (excluded sender: {bool(exclude_user)})")
    
    async def send_to_user(self, user_id: str, room_id: str, message: dict):
        """Send message to a specific user in a room with error handling"""
        if (user_id in self.user_connections and 
            room_id in self.user_connections[user_id]):
            
            websocket = self.user_connections[user_id][room_id]
            try:
                # Check if WebSocket is still open
                if websocket.client_state.value == 1:  # OPEN state
                    await websocket.send_text(json.dumps(message))
                    return True
                else:
                    print(f"WebSocket closed for user {user_id}, cleaning up connection")
                    self.disconnect_from_room(room_id, user_id)
            except Exception as e:
                error_msg = str(e)
                if "close frame" in error_msg or "ConnectionClosedError" in error_msg:
                    print(f"WebSocket connection closed for user {user_id}")
                else:
                    print(f"❌ Error sending to user {user_id}: {e}")
                self.disconnect_from_room(room_id, user_id)
        return False
    
    async def get_online_users_in_room(self, room_id: str) -> List[dict]:
        """Get list of online users in a room"""
        online_users = []
        if room_id in self.room_connections:
            for user_id in self.room_connections[room_id]:
                if user_id in self.user_status:
                    user_info = self.user_status[user_id]
                    if user_info["status"] == "online":
                        online_users.append({
                            "user_id": user_id,
                            "username": user_info["username"],
                            "status": user_info["status"]
                        })
        return online_users

# Global connection managers
upload_manager = ConnectionManager()  # ✅ EXISTING UPLOAD MANAGER
chat_manager = ChatConnectionManager()  # ✅ NEW CHAT MANAGER

# ✅ EXISTING UPLOAD WEBSOCKET (PRESERVED)
@router.websocket("/ws/upload/{file_id}")
async def websocket_upload_progress(
    websocket: WebSocket, 
    file_id: str,
    token: Optional[str] = Query(None)  # ✅ AUTH TOKEN AS QUERY PARAM
):
    """WebSocket endpoint for real-time upload progress with authentication"""
    
    # ✅ AUTHENTICATE USER BEFORE CONNECTING
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return
    
    try:
        # Verify JWT token
        payload = upload_manager.auth_service.verify_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return
            
        # Get user from database to verify they exist
        from db.auth_crud import get_user_by_id
        user = await get_user_by_id(user_id)
        if not user:
            await websocket.close(code=4001, reason="User not found")
            return
        
        # Prepare user info for connection
        user_info = {
            "id": user["id"],
            "email": user.get("email", "unknown")
        }
        
    except Exception as e:
        print(f"WebSocket auth error: {e}")
        await websocket.close(code=4001, reason="Authentication failed")
        return
    
    await upload_manager.connect(websocket, file_id, user_info)
    
    try:
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connected",
            "file_id": file_id,
            "user_id": user_info["id"],
            "message": f"Connected to upload progress for {file_id}",
            "timestamp": datetime.utcnow().isoformat()
        }))
        
        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for client message (optional - could be heartbeat)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                # Handle client messages if needed
                try:
                    client_message = json.loads(data)
                    if client_message.get("type") == "ping":
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        }))
                except json.JSONDecodeError:
                    pass
                    
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                await websocket.send_text(json.dumps({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                }))
                
    except WebSocketDisconnect:
        upload_manager.disconnect(websocket, file_id)
    except Exception as e:
        print(f"WebSocket error for {file_id}: {e}")
        upload_manager.disconnect(websocket, file_id)


# ✅ GENERAL CHAT WEBSOCKET (NO ROOM SPECIFIC)
@router.websocket("/ws/chat")
async def websocket_chat_general(websocket: WebSocket, token: str = Query(...)):
    """WebSocket endpoint for general chat connection (before room selection)"""
    try:
        print(f"WebSocket /ws/chat auth attempt - Token: {token[:50]}...")
        # ✅ AUTHENTICATE USER
        payload = chat_manager.auth_service.verify_token(token)
        print(f"Token verified - User ID: {payload.get('sub')}")
        user_id = payload.get("sub")
        
        if not user_id:
            print("No user ID in token payload")
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        # Get user info with retry logic
        from db.auth_crud import get_user_by_id
        user = await get_user_by_id(user_id)
        if not user:
            print(f"User {user_id} not found in database after retries")
            await websocket.close(code=4001, reason="User not found or database unavailable")
            return
        
        print(f"WebSocket authentication successful for user: {user.get('username')}")
        
        await websocket.accept()
        username = user.get("username", "Unknown")
        
        # Send connection confirmation with error handling
        try:
            await websocket.send_text(json.dumps({
                "type": "connected",
                "user_id": user_id,
                "username": username,
                "message": "Connected to chat system",
                "timestamp": datetime.utcnow().isoformat()
            }))
        except Exception as e:
            print(f"Failed to send connection confirmation: {e}")
            return
        
        try:
            while True:
                # ✅ RECEIVE AND HANDLE CLIENT MESSAGES WITH TIMEOUT
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                    message_data = json.loads(data)
                    
                    message_type = message_data.get("type")
                    
                    if message_type == "ping":
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        }))
                    elif message_type == "heartbeat":
                        await websocket.send_text(json.dumps({
                            "type": "heartbeat_ack",
                            "timestamp": datetime.utcnow().isoformat()
                        }))
                        
                except asyncio.TimeoutError:
                    # Check if connection is still alive
                    try:
                        await websocket.send_text(json.dumps({
                            "type": "server_ping",
                            "timestamp": datetime.utcnow().isoformat()
                        }))
                    except:
                        # Connection is dead, break loop
                        break
                        
        except WebSocketDisconnect:
            print("General Chat WebSocket disconnected normally")
        except Exception as e:
            print(f"General Chat WebSocket error: {e}")
            
    except HTTPException as he:
        print(f"WebSocket HTTP exception: {he.status_code} - {he.detail}")
        try:
            await websocket.close(code=4001, reason=he.detail)
        except:
            pass
    except Exception as e:
        print(f"General Chat WebSocket connection error: {e}")
        import traceback
        traceback.print_exc()
        try:
            await websocket.close(code=4000, reason="Internal server error")
        except:
            pass


# ✅ ROOM-SPECIFIC CHAT WEBSOCKET WITH FILE UPLOAD INTEGRATION
@router.websocket("/ws/chat/{room_id}")
async def websocket_chat_endpoint(websocket: WebSocket, room_id: str, token: str = Query(...)):
    """WebSocket endpoint for real-time chat with file upload progress"""
    try:
        # ✅ AUTHENTICATE USER
        payload = chat_manager.auth_service.verify_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        # Get user info with retry logic
        from db.auth_crud import get_user_by_id
        user = await get_user_by_id(user_id)
        if not user:
            await websocket.close(code=4001, reason="User not found or database unavailable")
            return
        
        # ✅ GET USERNAME FIRST BEFORE USING IT
        username = user.get("username", "Unknown")
        
        # ✅ CHECK ROOM MEMBERSHIP WITH DETAILED DEBUGGING
        try:
            print(f"🔍 Checking room membership: User {username} ({user_id[:8]}...) -> Room {room_id[:8]}...")
            is_member = await ChatCRUD.is_user_in_room(user_id, room_id)
            print(f"🔍 Membership result: {is_member}")
            
            if not is_member:
                print(f"❌ Access denied: {username} is not a member of room {room_id[:8]}...")
                await websocket.close(code=4003, reason="Not a member of this room")
                return
            else:
                print(f"✅ Access granted: {username} is a member of room {room_id[:8]}...")
        except Exception as e:
            print(f"❌ Error checking room membership: {e}")
            await websocket.close(code=4000, reason="Database error checking room access")
            return
        
        # ✅ ACCEPT WEBSOCKET CONNECTION FIRST
        await websocket.accept()
        
        # ✅ CONNECT TO CHAT ROOM (without accepting again)
        # username already defined above
        
        # Add connection to manager manually (since connect_to_room accepts again)
        # Initialize room if it doesn't exist
        if room_id not in chat_manager.room_connections:
            chat_manager.room_connections[room_id] = {}
        
        # Initialize user connections if it doesn't exist
        if user_id not in chat_manager.user_connections:
            chat_manager.user_connections[user_id] = {}
            
        # Add connection
        chat_manager.room_connections[room_id][user_id] = websocket
        chat_manager.user_connections[user_id][room_id] = websocket
        
        # Update user status
        chat_manager.user_status[user_id] = {
            "status": "online",
            "last_seen": datetime.utcnow(),
            "username": username
        }
        
        print(f"💬 Chat WebSocket connected - Room: {room_id}, User: {username}")
        
        # Send connection confirmation with room info
        try:
            online_users = await chat_manager.get_online_users_in_room(room_id)
            await websocket.send_text(json.dumps({
                "type": "connected",
                "room_id": room_id,
                "user_id": user_id,
                "username": username,
                "online_users": online_users,
                "timestamp": datetime.utcnow().isoformat()
            }))
            
            # Notify others in the room that user joined
            await chat_manager.broadcast_to_room(room_id, {
                "type": "user_joined",
                "user_id": user_id,
                "username": username,
                "timestamp": datetime.utcnow().isoformat()
            }, exclude_user=user_id)
            
        except Exception as e:
            print(f"❌ Failed to send room connection confirmation: {e}")
            return
        
        try:
            while True:
                # ✅ RECEIVE AND HANDLE CLIENT MESSAGES WITH TIMEOUT
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                    message_data = json.loads(data)
                    
                    message_type = message_data.get("type")
                    print(f"📨 WebSocket message received: {message_type} from {username}")
                    
                    if message_type == "text_message":
                        print(f"💬 Processing text message: {message_data.get('content', '')[:50]}...")
                        await handle_text_message(room_id, user_id, username, message_data)
                    elif message_type == "typing":
                        await handle_typing_indicator(room_id, user_id, username, message_data)
                    elif message_type == "read_receipt":
                        await handle_read_receipt(room_id, user_id, message_data)
                    elif message_type == "ping":
                        try:
                            await websocket.send_text(json.dumps({
                                "type": "pong",
                                "timestamp": datetime.utcnow().isoformat()
                            }))
                        except:
                            # Connection is dead
                            break
                    else:
                        print(f"❓ Unknown message type: {message_type}")
                            
                except asyncio.TimeoutError:
                    # Check if connection is still alive with server ping
                    try:
                        await websocket.send_text(json.dumps({
                            "type": "server_ping",
                            "timestamp": datetime.utcnow().isoformat()
                        }))
                    except:
                        # Connection is dead, break loop
                        print(f"💬 Room WebSocket timeout - connection lost for user {username} in room {room_id}")
                        break
                        
        except WebSocketDisconnect:
            print(f"💬 Room WebSocket disconnected normally - user {username} left room {room_id}")
        except Exception as e:
            print(f"💬 Room WebSocket error for user {username} in room {room_id}: {e}")
        finally:
            # ✅ CLEAN UP CONNECTION
            try:
                chat_manager.disconnect_from_room(room_id, user_id)
                
                # Notify others that user left
                await chat_manager.broadcast_to_room(room_id, {
                    "type": "user_left",
                    "user_id": user_id,
                    "username": username,
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                print(f"❌ Error during WebSocket cleanup: {e}")
            
    except Exception as e:
        print(f"Chat WebSocket connection error: {e}")
        try:
            await websocket.close(code=4000, reason="Internal server error")
        except:
            pass


# ✅ CHAT MESSAGE HANDLERS
async def handle_text_message(room_id: str, sender_id: str, sender_username: str, message_data: dict):
    """Handle incoming text message"""
    try:
        content = message_data.get("content", "").strip()
        if not content:
            return
            
        reply_to_id = message_data.get("reply_to_id")
        
        # Save message to database
        message = await ChatCRUD.send_text_message(
            sender_id=sender_id,
            room_id=room_id,
            content=content,
            reply_to_id=reply_to_id
        )
        
        # Get reply context if exists
        reply_context = None
        if reply_to_id:
            reply_msg = await ChatCRUD.get_message_by_id(reply_to_id)
            if reply_msg:
                reply_context = {
                    "id": reply_msg["id"],
                    "content": reply_msg["content"][:100] + ("..." if len(reply_msg["content"]) > 100 else ""),
                    "sender_username": reply_msg.get("sender_username", "Unknown"),
                    "message_type": reply_msg["message_type"]
                }
        
        # ✅ BROADCAST MESSAGE TO ALL ROOM MEMBERS
        broadcast_message = {
            "type": "new_message",
            "message": {
                "id": message["id"],
                "room_id": room_id,
                "sender_id": sender_id,
                "sender_username": sender_username,
                "message_type": MessageType.TEXT.value,
                "content": content,
                "reply_to": reply_context,
                "created_at": message["created_at"]
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await chat_manager.broadcast_to_room(room_id, broadcast_message)
        
        # Mark as delivered for all room members
        member_ids = await ChatCRUD.get_room_member_ids(room_id)
        for member_id in member_ids:
            if member_id != sender_id:  # Don't mark as delivered for sender
                await ChatCRUD.mark_message_status(message["id"], member_id, MessageStatus.DELIVERED.value)
        
    except Exception as e:
        print(f"Error handling text message: {e}")


async def handle_typing_indicator(room_id: str, user_id: str, username: str, message_data: dict):
    """Handle typing indicator"""
    try:
        is_typing = message_data.get("is_typing", False)
        
        await chat_manager.broadcast_to_room(room_id, {
            "type": "typing",
            "user_id": user_id,
            "username": username,
            "is_typing": is_typing,
            "timestamp": datetime.utcnow().isoformat()
        }, exclude_user=user_id)
        
    except Exception as e:
        print(f"Error handling typing indicator: {e}")


async def handle_read_receipt(room_id: str, user_id: str, message_data: dict):
    """Handle read receipt"""
    try:
        message_id = message_data.get("message_id")
        if not message_id:
            return
            
        # Mark message as read
        success = await ChatCRUD.mark_message_status(message_id, user_id, MessageStatus.READ.value)
        
        if success:
            # Notify sender about read receipt
            message = await ChatCRUD.get_message_by_id(message_id)
            if message and message["sender_id"] != user_id:
                await chat_manager.send_to_user(message["sender_id"], room_id, {
                    "type": "message_read",
                    "message_id": message_id,
                    "reader_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                })
        
    except Exception as e:
        print(f"Error handling read receipt: {e}")


# ✅ HELPER FUNCTIONS FOR FILE UPLOAD INTEGRATION
async def notify_chat_file_progress(room_id: str, file_id: str, sender_id: str, 
                                  progress_data: dict):
    """Notify chat room about file upload progress"""
    try:
        await chat_manager.broadcast_to_room(room_id, {
            "type": "file_upload_progress",
            "file_id": file_id,
            "sender_id": sender_id,
            "progress": progress_data.get("progress", 0),
            "chunk_number": progress_data.get("chunk_number", 0),
            "total_chunks": progress_data.get("total_chunks", 0),
            "file_name": progress_data.get("file_name", ""),
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        print(f"Error notifying chat file progress: {e}")


async def notify_chat_file_complete(room_id: str, message: dict):
    """Notify chat room about completed file upload"""
    try:
        await chat_manager.broadcast_to_room(room_id, {
            "type": "new_file_message",
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        print(f"Error notifying chat file completion: {e}")


# ✅ EXPORT MANAGERS FOR USE IN OTHER MODULES
__all__ = ["upload_manager", "chat_manager", "notify_chat_file_progress", "notify_chat_file_complete"]