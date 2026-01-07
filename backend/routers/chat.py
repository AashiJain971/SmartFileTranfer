from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from typing import List, Optional, Dict
from models.chat import *
from db.chat_crud import ChatCRUD
from db.auth_crud import get_user_by_id, get_user_by_email
from dependencies.auth import get_current_active_user
from routers.websocket import chat_manager, notify_chat_file_progress, notify_chat_file_complete
from utils.file_utils import save_upload_file, get_file_extension
from utils.hash_utils import calculate_file_hash
from services.blockchain_service import get_blockchain_service
from services.ipfs_service import get_ipfs_service
from services.certificate_service import get_certificate_service
import os
import shutil
import uuid
import json
import asyncio
import time
import hashlib
import re
from datetime import datetime

router = APIRouter(prefix="/chat", tags=["chat"])

# 📦 In-memory storage for upload sessions (Phase 1 verification tracking)
upload_sessions: Dict[str, dict] = {}

# ✅ CHAT ROOM MANAGEMENT

@router.post("/rooms", response_model=ChatRoomResponse)
async def create_chat_room(
    request: CreateChatRoomRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Create a new chat room (direct or group chat)"""
    try:
        # Validate room name for group chats
        if request.type == ChatRoomType.GROUP and not request.name:
            raise HTTPException(status_code=400, detail="Group chats must have a name")
        
        # ✅ FOR DIRECT CHATS: Check if room already exists between users
        if request.type == ChatRoomType.DIRECT and request.members:
            print(f"🔍 Checking for existing direct chat between {current_user['username']} and {request.members}")
            
            # Get the other user first
            member_identifier = request.members[0]
            other_user = None
            
            # Try to find the other user
            import re
            uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            
            if re.match(uuid_pattern, member_identifier, re.IGNORECASE):
                try:
                    other_user = await get_user_by_id(member_identifier)
                except:
                    pass
            
            if not other_user:
                try:
                    other_user = await get_user_by_email(member_identifier)
                except:
                    pass
                    
            if not other_user:
                try:
                    from db.auth_crud import get_user_by_username
                    other_user = await get_user_by_username(member_identifier)
                except:
                    pass
            
            if other_user:
                # Check if direct chat already exists
                existing_room = await ChatCRUD.find_direct_chat_room(current_user["id"], other_user["id"])
                if existing_room:
                    print(f"✅ Found existing direct chat room: {existing_room['id']}")
                    
                    # Return existing room with member details
                    members = await ChatCRUD.get_room_members_detailed(existing_room["id"])
                    return ChatRoomResponse(
                        id=existing_room["id"],
                        name=existing_room["name"],
                        type=ChatRoomType(existing_room["type"]),
                        created_by=existing_room["created_by"],
                        created_by_username=existing_room.get("created_by_username", "Unknown"),
                        members=[
                            ChatRoomMember(
                                user_id=m["user_id"],
                                username=m["username"],
                                role=UserRole(m["role"]),
                                joined_at=m["joined_at"]
                            ) for m in members
                        ],
                        created_at=existing_room["created_at"],
                        updated_at=existing_room["updated_at"]
                    )
                else:
                    print(f"🆕 No existing direct chat found, creating new room...")
            else:
                raise HTTPException(status_code=404, detail=f"User not found: {member_identifier}")
        
        # Generate room name if not provided (for direct chats)
        room_name = request.name
        if not room_name and request.type == ChatRoomType.DIRECT:
            # For direct chats, generate name from participants
            if request.members:
                member_identifier = request.members[0]
                
                # Try to get the other user's name
                other_user = None
                import re
                uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                
                if re.match(uuid_pattern, member_identifier, re.IGNORECASE):
                    try:
                        other_user = await get_user_by_id(member_identifier)
                    except:
                        pass
                
                if not other_user:
                    try:
                        other_user = await get_user_by_email(member_identifier)
                    except:
                        pass
                        
                if not other_user:
                    try:
                        from db.auth_crud import get_user_by_username
                        other_user = await get_user_by_username(member_identifier)
                    except:
                        pass
                
                if other_user:
                    room_name = f"{current_user['username']} & {other_user['username']}"
                else:
                    room_name = f"Direct Chat - {current_user['username']}"
            else:
                room_name = f"Direct Chat - {current_user['username']}"
        
        # Create the room
        room = await ChatCRUD.create_chat_room(
            creator_id=current_user["id"],
            room_type=request.type.value,
            name=room_name
        )
        
        # Add creator as admin
        await ChatCRUD.add_room_members(room["id"], [current_user["id"]], role="admin")
        
        # Add other members with better error handling
        member_ids = []
        for member_identifier in request.members:
            user = None
            
            # Check if it looks like a UUID (contains hyphens and is proper length)
            import re
            uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            
            print(f"🔍 Looking up user: {member_identifier}")
            
            # Try multiple lookup methods with timeout handling
            if re.match(uuid_pattern, member_identifier, re.IGNORECASE):
                # Try as UUID first
                try:
                    user = await get_user_by_id(member_identifier)
                    if user:
                        print(f"✅ Found user by ID: {user['username']}")
                except Exception as e:
                    print(f"❌ ID lookup failed: {e}")
            
            if not user:
                # Try as email with timeout handling
                try:
                    user = await get_user_by_email(member_identifier)
                    if user:
                        print(f"✅ Found user by email: {user['username']}")
                except Exception as e:
                    print(f"❌ Email lookup failed: {e}")
                    
            if not user:
                # Try as username
                try:
                    from db.auth_crud import get_user_by_username
                    user = await get_user_by_username(member_identifier)
                    if user:
                        print(f"✅ Found user by username: {user['username']}")
                except Exception as e:
                    print(f"❌ Username lookup failed: {e}")
            
            if user and user["id"] != current_user["id"]:
                member_ids.append(user["id"])
                print(f"✅ Added member: {user['username']}")
            elif not user:
                # More specific error message
                error_msg = f"User not found or database temporarily unavailable: {member_identifier}"
                print(f"❌ {error_msg}")
                raise HTTPException(
                    status_code=404, 
                    detail=error_msg
                )
        
        if member_ids:
            success = await ChatCRUD.add_room_members(room["id"], member_ids)
            if not success:
                raise HTTPException(status_code=400, detail="Failed to add some members")
        
        # Get complete room info for response
        members = await ChatCRUD.get_room_members_detailed(room["id"])
        
        # ✅ INVALIDATE CACHE FOR ALL ROOM MEMBERS
        from services.cache_service import cache
        for member in members:
            member_id = member["user_id"]
            cache_key = f"rooms:{member_id}"
            await cache.delete(cache_key)
            print(f"🗑️ Cleared cache for member: {member.get('username', member_id[:8])}")
        
        room_response = ChatRoomResponse(
            id=room["id"],
            name=room["name"],
            type=ChatRoomType(room["type"]),
            created_by=room["created_by"],
            created_by_username=current_user["username"],
            members=[
                ChatRoomMember(
                    user_id=m["user_id"],
                    username=m["username"],
                    role=UserRole(m["role"]),
                    joined_at=m["joined_at"]
                ) for m in members
            ],
            created_at=room["created_at"],
            updated_at=room["updated_at"]
        )
        
        # ✅ BROADCAST NEW ROOM TO ALL MEMBERS via General WebSocket
        try:
            print(f"📢 Broadcasting new room notification to {len(members)} members...")
            from routers.websocket import chat_manager
            from datetime import datetime
            
            # Create room notification
            room_notification = {
                "type": "new_room",
                "room": {
                    "id": room["id"],
                    "name": room["name"],
                    "type": room["type"],
                    "created_by": current_user["username"],
                    "member_count": len(members)
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send notification to all room members via general chat WebSocket
            for member in members:
                member_id = member["user_id"]
                if member_id in chat_manager.user_connections:
                    for room_ws_id, websocket in chat_manager.user_connections[member_id].items():
                        try:
                            await websocket.send_text(json.dumps(room_notification))
                            print(f"✅ Sent room notification to {member['username']}")
                        except:
                            print(f"❌ Failed to send room notification to {member['username']}")
            
        except Exception as e:
            print(f"❌ Failed to broadcast room notification: {e}")
            # Don't fail the request if notification fails
        
        return room_response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create chat room: {str(e)}")


@router.get("/rooms", response_model=ChatRoomListResponse)
async def get_user_chat_rooms(
    current_user: dict = Depends(get_current_active_user)
):
    """Get all chat rooms for the current user"""
    try:
        rooms_data = await ChatCRUD.get_user_chat_rooms(current_user["id"])
        
        room_responses = []
        for room_data in rooms_data:
            # Convert members to proper format
            members = [
                ChatRoomMember(
                    user_id=m["user_id"],
                    username=m["username"],
                    role=UserRole(m["role"]),
                    joined_at=m["joined_at"]
                ) for m in room_data.get("members", [])
            ]
            
            # Convert last message if exists
            last_message = None
            if room_data.get("last_message"):
                msg = room_data["last_message"]
                last_message = MessageResponse(
                    id=msg["id"],
                    room_id=msg["room_id"],
                    sender_id=msg["sender_id"],
                    sender_username=msg.get("sender_username", "Unknown"),
                    message_type=MessageType(msg["message_type"]),
                    content=msg.get("content"),
                    file_session_id=msg.get("file_session_id"),
                    file_path=msg.get("file_path"),
                    file_name=msg.get("file_name"),
                    file_size=msg.get("file_size"),
                    file_hash=msg.get("file_hash"),
                    created_at=msg["created_at"],
                    updated_at=msg.get("updated_at", msg["created_at"])
                )
            
            room_response = ChatRoomResponse(
                id=room_data["id"],
                name=room_data["name"],
                type=ChatRoomType(room_data["type"]),
                created_by=room_data["created_by"],
                created_by_username=room_data.get("users", {}).get("username", "Unknown"),
                members=members,
                last_message=last_message,
                unread_count=room_data.get("unread_count", 0),
                created_at=room_data["created_at"],
                updated_at=room_data["updated_at"]
            )
            room_responses.append(room_response)
        
        return ChatRoomListResponse(rooms=room_responses, total=len(room_responses))
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chat rooms: {str(e)}")


@router.get("/rooms/{room_id}")
async def get_chat_room(
    room_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Get detailed information about a specific chat room"""
    try:
        # Check if user is member of the room
        is_member = await ChatCRUD.is_user_in_room(current_user["id"], room_id)
        if not is_member:
            raise HTTPException(status_code=403, detail="Not a member of this room")
        
        room = await ChatCRUD.get_chat_room_by_id(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Chat room not found")
        
        members = await ChatCRUD.get_room_members_detailed(room_id)
        statistics = await ChatCRUD.get_room_statistics(room_id)
        
        return {
            "room": room,
            "members": members,
            "statistics": statistics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ MESSAGE OPERATIONS

@router.get("/rooms/{room_id}/messages", response_model=MessagesResponse)
async def get_room_messages(
    room_id: str,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_active_user)
):
    """Get messages from a chat room"""
    print(f"🔧 DEBUG: get_room_messages called for room_id={room_id}, user={current_user['username']}")
    try:
        # Check if user is member of the room
        print(f"🔧 DEBUG: Checking room membership...")
        print(f"🔧 DEBUG: Checking membership for user_id={current_user['id']}, room_id={room_id}")
        is_member = await ChatCRUD.is_user_in_room(current_user["id"], room_id)
        print(f"🔧 DEBUG: Room membership check result: {is_member}")
        
        if not is_member:
            print(f"🔧 DEBUG: Membership check failed - querying database directly...")
            from db.database import supabase
            debug_result = supabase.table("chat_room_members")\
                .select("*")\
                .eq("user_id", current_user["id"])\
                .eq("room_id", room_id)\
                .execute()
            print(f"🔧 DEBUG: Direct query result: {debug_result.data}")
            
            # Also check all memberships for this user
            all_memberships = supabase.table("chat_room_members")\
                .select("*")\
                .eq("user_id", current_user["id"])\
                .execute()
            print(f"🔧 DEBUG: All memberships for user: {all_memberships.data}")
        
        if not is_member:
            print(f"🔧 DEBUG: ❌ User {current_user['username']} is not a member of room {room_id}")
            raise HTTPException(status_code=403, detail="Not a member of this room")
        
        print(f"🔧 DEBUG: Fetching messages from CRUD...")
        messages_data = await ChatCRUD.get_room_messages(room_id, limit, offset)
        print(f"🔧 DEBUG: Retrieved {len(messages_data)} messages from database")
        
        messages = []
        for msg in messages_data:
            # Get user's status for this message
            status = await ChatCRUD.get_message_status(msg["id"], current_user["id"])
            
            # Convert reply_to if exists
            reply_to = None
            if msg.get("reply_to"):
                reply = msg["reply_to"]
                reply_to = MessageResponse(
                    id=reply["id"],
                    room_id=room_id,
                    sender_id=reply.get("sender_id", ""),
                    sender_username=reply.get("sender_username", "Unknown"),
                    message_type=MessageType(reply["message_type"]),
                    content=reply.get("content"),
                    created_at=reply.get("created_at", datetime.utcnow()),
                    updated_at=reply.get("updated_at", datetime.utcnow())
                )
            
            message = MessageResponse(
                id=msg["id"],
                room_id=msg["room_id"],
                sender_id=msg["sender_id"],
                sender_username=msg.get("sender_username", "Unknown"),
                message_type=MessageType(msg["message_type"]),
                content=msg.get("content"),
                file_session_id=msg.get("file_session_id"),
                file_path=msg.get("file_path"),
                file_name=msg.get("file_name"),
                file_size=msg.get("file_size"),
                file_hash=msg.get("file_hash"),
                reply_to=reply_to,
                created_at=msg["created_at"],
                updated_at=msg.get("updated_at", msg["created_at"]),
                status=MessageStatus(status) if status else None
            )
            messages.append(message)
        
        return MessagesResponse(
            messages=messages,
            total=len(messages),
            limit=limit,
            offset=offset,
            room_id=room_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rooms/{room_id}/messages")
async def send_text_message(
    room_id: str,
    request: SendTextMessageRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Send a text message to a chat room"""
    print(f"🔧 DEBUG: send_text_message called with room_id={room_id}")
    print(f"🔧 DEBUG: Request content: {request.content if hasattr(request, 'content') else 'No content'}")
    print(f"🔧 DEBUG: Request reply_to_id: {request.reply_to_id if hasattr(request, 'reply_to_id') else 'No reply_to_id'}")
    print(f"🔧 DEBUG: Current user: {current_user['username']} (ID: {current_user['id']})")
    try:
        # Check if user is member of the room
        is_member = await ChatCRUD.is_user_in_room(current_user["id"], room_id)
        if not is_member:
            raise HTTPException(status_code=403, detail="Not a member of this room")
        
        # Send message via CRUD 
        print(f"🔧 DEBUG: About to call ChatCRUD.send_text_message")
        message = await ChatCRUD.send_text_message(
            sender_id=current_user["id"],
            room_id=room_id,
            content=request.content,
            reply_to_id=request.reply_to_id
        )
        print(f"🔧 DEBUG: Message sent successfully, ID: {message['id']}")
        
        # ✅ BROADCAST MESSAGE VIA WEBSOCKET TO ALL ROOM MEMBERS
        print(f"🔧 DEBUG: Broadcasting message via WebSocket...")
        try:
            # Get reply context if exists
            reply_context = None
            if request.reply_to_id:
                reply_msg = await ChatCRUD.get_message_by_id(request.reply_to_id)
                if reply_msg:
                    reply_context = {
                        "id": reply_msg["id"],
                        "content": reply_msg["content"][:100] + ("..." if len(reply_msg["content"]) > 100 else ""),
                        "sender_username": reply_msg.get("sender_username", "Unknown"),
                        "message_type": reply_msg["message_type"]
                    }

            # Import the WebSocket manager and broadcast function
            from routers.websocket import chat_manager
            from models.chat import MessageType
            from datetime import datetime
            
            # Create broadcast message
            broadcast_message = {
                "type": "new_message",
                "message": {
                    "id": message["id"],
                    "room_id": room_id,
                    "sender_id": current_user["id"],
                    "sender_username": current_user["username"],
                    "message_type": MessageType.TEXT.value,
                    "content": request.content,
                    "reply_to": reply_context,
                    "created_at": message["created_at"]
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Broadcast to all room members
            await chat_manager.broadcast_to_room(room_id, broadcast_message)
            print(f"🔧 DEBUG: ✅ WebSocket broadcast successful")
            
            # Mark as delivered for all room members (except sender)
            member_ids = await ChatCRUD.get_room_member_ids(room_id)
            for member_id in member_ids:
                if member_id != current_user["id"]:  # Don't mark as delivered for sender
                    await ChatCRUD.mark_message_status(message["id"], member_id, "delivered")
            print(f"🔧 DEBUG: ✅ Message marked as delivered for room members")
            
        except Exception as ws_error:
            print(f"🔧 DEBUG: ❌ WebSocket broadcast failed: {ws_error}")
            # Don't fail the API call if WebSocket fails
        
        # Verify message was stored
        print(f"🔧 DEBUG: Verifying message storage...")
        verification = await ChatCRUD.get_message_by_id(message["id"])
        if verification:
            print(f"🔧 DEBUG: ✅ Message verification successful: {verification}")
        else:
            print(f"🔧 DEBUG: ❌ Message verification failed - message not found in DB")
        
        return {"status": "sent", "message_id": message["id"]}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rooms/{room_id}/messages/{message_id}/read")
async def mark_message_as_read(
    room_id: str,
    message_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Mark a message as read"""
    try:
        # Check if user is member of the room
        is_member = await ChatCRUD.is_user_in_room(current_user["id"], room_id)
        if not is_member:
            raise HTTPException(status_code=403, detail="Not a member of this room")
        
        success = await ChatCRUD.mark_message_status(
            message_id, current_user["id"], MessageStatus.READ.value
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to mark message as read")
        
        return {"status": "marked_as_read", "message_id": message_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rooms/{room_id}/messages/mark-all-read")
async def mark_all_messages_as_read(
    room_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Mark all messages in a room as read"""
    try:
        # Check if user is member of the room
        is_member = await ChatCRUD.is_user_in_room(current_user["id"], room_id)
        if not is_member:
            raise HTTPException(status_code=403, detail="Not a member of this room")
        
        marked_count = await ChatCRUD.mark_room_messages_as_read(room_id, current_user["id"])
        
        return {
            "status": "marked_as_read",
            "room_id": room_id,
            "marked_count": marked_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ FILE SHARING (SIMPLE UPLOAD)

@router.post("/rooms/{room_id}/files")
async def send_simple_file(
    room_id: str,
    file: UploadFile = File(...),
    reply_to_id: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_active_user)
):
    """Send a small file directly to chat (not chunked)"""
    try:
        # Check if user is member of the room
        is_member = await ChatCRUD.is_user_in_room(current_user["id"], room_id)
        if not is_member:
            raise HTTPException(status_code=403, detail="Not a member of this room")
        
        # File size limit for simple upload (10MB)
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        file_content = await file.read()
        
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413, 
                detail="File too large. Use chunked upload for files over 10MB."
            )
        
        # Calculate file hash
        from utils.hash_utils import compute_chunk_hash
        file_hash = compute_chunk_hash(file_content)
        
        # Create chat files directory
        chat_files_dir = "uploaded_files/chat"
        os.makedirs(chat_files_dir, exist_ok=True)
        
        # Save file with unique name
        file_extension = get_file_extension(file.filename)
        unique_filename = f"{file_hash}{file_extension}"
        file_path = os.path.join(chat_files_dir, unique_filename)
        
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Create file message
        message = await ChatCRUD.send_file_message(
            sender_id=current_user["id"],
            room_id=room_id,
            file_session_id=None,  # No session for simple upload
            file_path=file_path,
            file_name=file.filename,
            file_size=len(file_content),
            file_hash=file_hash,
            reply_to_id=reply_to_id
        )
        
        return {
            "status": "sent",
            "message_id": message["id"],
            "file_size": len(file_content),
            "file_hash": file_hash
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ CHUNKED FILE UPLOAD FOR CHAT (INTEGRATION WITH EXISTING SYSTEM)

@router.post("/rooms/{room_id}/files/start")
async def start_chat_file_upload(
    room_id: str,
    request: StartChatFileUploadRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """
    🚀 PHASE 1: VERIFY MEMBERSHIP (One-time Security Check)
    - Verify user is room member BEFORE allowing ANY chunks
    - Short timeout (5s) - fail fast
    - If verified: generate file_id and return chunk_size
    - If timeout: reject immediately (user retries later)
    """
    import asyncio
    import time
    
    try:
        # ✅ SECURITY GATE: Verify membership with short timeout
        try:
            is_member = await asyncio.wait_for(
                ChatCRUD.is_user_in_room(current_user["id"], room_id),
                timeout=5.0  # Fail fast - don't make user wait 30s
            )
            
            if not is_member:
                raise HTTPException(
                    status_code=403,
                    detail="Not a member of this room"
                )
                
        except asyncio.TimeoutError:
            # DB timeout at start → REJECT upload immediately
            print(f"⚠️ Membership verification timeout for user {current_user['id']} in room {room_id}")
            raise HTTPException(
                status_code=503,
                detail="Cannot verify membership at this time. Please try again in a moment."
            )
        except Exception as e:
            # Any other error → REJECT upload
            print(f"❌ Membership check failed: {e}")
            raise HTTPException(
                status_code=503,
                detail="Database temporarily unavailable. Please retry."
            )
        
        # ✅ VERIFIED: User is a member, allow upload
        
        # Generate unique file ID embedding room_id for security
        file_id = f"chat-{room_id}-{uuid.uuid4().hex}"
        
        # Calculate dynamic chunk size based on file size
        file_size = request.file_size
        if file_size < 5 * 1024 * 1024:  # < 5MB
            chunk_size = 256 * 1024  # 256KB
        elif file_size > 500 * 1024 * 1024:  # > 500MB
            chunk_size = 2 * 1024 * 1024  # 2MB
        else:
            chunk_size = 1024 * 1024  # 1MB
        
        # Store upload session in memory (no DB required)
        upload_sessions[file_id] = {
            "start_time": time.time(),
            "user_id": current_user["id"],
            "room_id": room_id,
            "filename": request.filename,
            "file_size": file_size,
            "file_hash": request.file_hash,
            "verified": True
        }
        
        print(f"✅ Upload started: {file_id} - {request.filename} ({file_size} bytes)")
        
        return FileUploadResponse(
            file_id=file_id,
            upload_url=f"/chat/rooms/{room_id}/files/chunk",
            chunk_size=chunk_size,
            message_id=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Start upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rooms/{room_id}/files/status/{file_id}")
async def get_upload_status(
    room_id: str,
    file_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    🔍 PHASE 5: GET UPLOAD STATUS (Auto-Resume Support)
    - Scans filesystem ONLY (no database queries)
    - Returns list of uploaded chunk numbers
    - Always works even when database is down
    """
    import re
    
    try:
        # Validate file_id format (security check)
        if not file_id.startswith(f"chat-{room_id}-"):
            raise HTTPException(
                status_code=403,
                detail="Invalid file_id for this room"
            )
        
        # ✅ FILESYSTEM SCAN (No DB required!)
        chunk_dir = f"temp_chunks/{file_id}"
        
        if not os.path.exists(chunk_dir):
            # No chunks uploaded yet
            return {
                "file_id": file_id,
                "chunks_received": [],
                "total_chunks": 0,
                "status": "not_started"
            }
        
        # List all chunk files
        try:
            files = os.listdir(chunk_dir)
        except Exception as e:
            print(f"⚠️ Error listing chunks: {e}")
            return {
                "file_id": file_id,
                "chunks_received": [],
                "total_chunks": 0,
                "status": "error"
            }
        
        # Extract chunk numbers from filenames (chunk_0, chunk_1, etc.)
        chunk_numbers = []
        for filename in files:
            match = re.match(r'^chunk_(\d+)$', filename)
            if match:
                chunk_numbers.append(int(match.group(1)))
        
        # Sort chunk numbers
        chunk_numbers.sort()
        
        # Get session info if available
        session = upload_sessions.get(file_id, {})
        total_chunks = session.get("total_chunks", 0)
        
        print(f"📊 Status for {file_id}: {len(chunk_numbers)}/{total_chunks} chunks")
        
        return {
            "file_id": file_id,
            "chunks_received": chunk_numbers,
            "total_chunks": total_chunks,
            "status": "in_progress" if chunk_numbers else "not_started",
            "filename": session.get("filename", "unknown")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting upload status: {e}")
        # Return empty status to allow fresh upload
        return {
            "file_id": file_id,
            "chunks_received": [],
            "total_chunks": 0,
            "status": "error",
            "error": str(e)
        }


@router.post("/rooms/{room_id}/files/chunk")
async def upload_chat_file_chunk(
    room_id: str,
    file_id: str = Form(...),
    chunk_number: int = Form(...),
    total_chunks: int = Form(...),
    chunk: UploadFile = File(...),
    chunk_hash: str = Form(...),
    current_user: dict = Depends(get_current_active_user)
):
    """
    📤 PHASE 3: UPLOAD CHUNKS (Network-Independent)
    - NO membership checks (already verified in Phase 1)
    - NO database queries (filesystem only)
    - Validates chunk hash (prevents corruption)
    - Fast and reliable
    """
    import hashlib
    
    try:
        # Lightweight validation: Check file_id format
        if not file_id.startswith(f"chat-{room_id}-"):
            raise HTTPException(
                status_code=403,
                detail="Invalid file_id for this room"
            )
        
        # Read chunk data
        chunk_data = await chunk.read()
        
        # ✅ VALIDATE CHUNK HASH (detect corruption/tampering)
        calculated_hash = hashlib.sha256(chunk_data).hexdigest()
        if calculated_hash != chunk_hash:
            print(f"❌ Hash mismatch for chunk {chunk_number}: expected {chunk_hash}, got {calculated_hash}")
            raise HTTPException(
                status_code=400,
                detail=f"Chunk {chunk_number} hash mismatch. Please retry this chunk."
            )
        
        # ✅ SAVE CHUNK TO FILESYSTEM (no database)
        chunk_dir = f"temp_chunks/{file_id}"
        os.makedirs(chunk_dir, exist_ok=True)
        
        chunk_path = os.path.join(chunk_dir, f"chunk_{chunk_number}")
        
        with open(chunk_path, 'wb') as f:
            f.write(chunk_data)
        
        # Update session total_chunks if needed
        if file_id in upload_sessions:
            upload_sessions[file_id]["total_chunks"] = total_chunks
        
        print(f"✅ Chunk {chunk_number}/{total_chunks} saved ({len(chunk_data)} bytes)")
        
        # Notify via WebSocket (best-effort, non-blocking)
        try:
            progress_percent = ((chunk_number + 1) / total_chunks) * 100
            await notify_chat_file_progress(room_id, file_id, current_user["id"], {
                "progress": progress_percent,
                "chunk_number": chunk_number,
                "total_chunks": total_chunks,
                "file_name": upload_sessions.get(file_id, {}).get("filename", "")
            })
        except Exception as ws_error:
            # WebSocket failed, but chunk is saved successfully
            print(f"⚠️ WebSocket notification failed: {ws_error}")
        
        return {
            "status": "ok",
            "chunk": chunk_number,
            "total_chunks": total_chunks,
            "progress": ((chunk_number + 1) / total_chunks) * 100
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Chunk upload error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save chunk {chunk_number}: {str(e)}"
        )


@router.post("/rooms/{room_id}/files/complete")
async def complete_chat_file_upload(
    room_id: str,
    file_id: str = Form(...),
    expected_hash: str = Form(...),
    reply_to_id: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Phase 6: Complete upload - merge chunks, validate, create message
    
    KEY PRINCIPLE: Upload succeeds even if database times out
    - Merge chunks from filesystem
    - Validate file hash
    - Fire-and-forget message creation (non-blocking)
    - Return success immediately
    """
    try:
        user_id = current_user["id"]
        
        # NO membership re-verification (already verified at start)
        # Trust the session - if they uploaded chunks, they had permission
        
        # Get session data
        session_data = upload_sessions.get(file_id)
        if not session_data:
            raise HTTPException(
                status_code=400,
                detail="Upload session not found. Please restart upload."
            )
        
        filename = session_data["filename"]
        total_chunks = session_data["total_chunks"]
        
        print(f"📦 Completing upload: {filename} ({total_chunks} chunks)")
        
        # ✅ VALIDATE ALL CHUNKS PRESENT
        chunk_dir = f"temp_chunks/{file_id}"
        if not os.path.exists(chunk_dir):
            raise HTTPException(
                status_code=400,
                detail="No chunks found. Upload may have failed."
            )
        
        uploaded_chunks = []
        for i in range(total_chunks):
            chunk_path = os.path.join(chunk_dir, f"chunk_{i}")
            if not os.path.exists(chunk_path):
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing chunk {i}/{total_chunks}. Please resume upload."
                )
            uploaded_chunks.append(chunk_path)
        
        print(f"✅ All {total_chunks} chunks verified")
        
        # ✅ MERGE CHUNKS TO FINAL FILE
        final_dir = f"uploaded_files/{room_id}"
        os.makedirs(final_dir, exist_ok=True)
        
        # Generate unique filename with timestamp
        timestamp = int(time.time())
        safe_filename = filename.replace("/", "_").replace("\\", "_")
        final_path = os.path.join(final_dir, f"{timestamp}_{safe_filename}")
        
        print(f"🔧 Merging chunks to: {final_path}")
        
        with open(final_path, 'wb') as final_file:
            for chunk_path in uploaded_chunks:
                with open(chunk_path, 'rb') as chunk_file:
                    final_file.write(chunk_file.read())
        
        # ✅ VALIDATE FINAL FILE HASH
        with open(final_path, 'rb') as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()
        
        if actual_hash != expected_hash:
            # Delete corrupted file
            os.remove(final_path)
            raise HTTPException(
                status_code=400,
                detail=f"File hash mismatch. Expected {expected_hash}, got {actual_hash}. Please retry upload."
            )
        
        file_size = os.path.getsize(final_path)
        print(f"✅ File hash verified: {actual_hash} ({file_size} bytes)")
        
        # ✅ CLEANUP TEMP CHUNKS
        import shutil
        try:
            shutil.rmtree(chunk_dir)
            print(f"🗑️ Cleaned up temp chunks: {chunk_dir}")
        except Exception as cleanup_error:
            print(f"⚠️ Cleanup warning: {cleanup_error}")
            # Continue even if cleanup fails
        
        # Remove session from memory
        if file_id in upload_sessions:
            del upload_sessions[file_id]
        
        # ✅ BLOCKCHAIN & IPFS RECORDING (Smart timeout based on file size)
        blockchain_result = None
        ipfs_result = None
        certificate_path = None
        message_id_for_update = None  # Store message ID for background updates
        
        # Start blockchain and IPFS uploads in background (don't block response)
        async def record_blockchain_and_ipfs(msg_id: Optional[str] = None):
            nonlocal blockchain_result, ipfs_result, certificate_path
            
            print(f"\n🔄 Starting blockchain/IPFS processing...")
            if msg_id:
                print(f"   Message ID: {msg_id}")
            print(f"   File: {filename}")
            print(f"   Size: {file_size / 1024 / 1024:.2f} MB")
            print(f"   Hash: {actual_hash}")
            
            try:
                # Upload to IPFS first (if configured)
                print(f"\n📤 Uploading to IPFS...")
                ipfs_service = get_ipfs_service()
                ipfs_result = await ipfs_service.upload_file(
                    file_path=final_path,
                    file_name=filename
                )
                
                if ipfs_result.get('success'):
                    print(f"✅ IPFS upload successful: {ipfs_result.get('cid')}")
                    
                    # ✅ UPDATE MESSAGE WITH IPFS CID (for background uploads)
                    if msg_id:
                        updated = await ChatCRUD.update_message_blockchain_data(
                            message_id=msg_id,
                            ipfs_cid=ipfs_result.get('cid')
                        )
                        if updated:
                            print(f"✅ Updated message {msg_id} with IPFS CID")
                            
                            # 🔔 NOTIFY CLIENTS via WebSocket that IPFS is ready
                            try:
                                from routers.websocket import broadcast_to_room
                                await broadcast_to_room(
                                    room_id,
                                    {
                                        'type': 'message_updated',
                                        'message_id': msg_id,
                                        'ipfs_cid': ipfs_result.get('cid'),
                                        'update_type': 'ipfs_complete'
                                    }
                                )
                                print(f"📢 Notified clients about IPFS completion")
                            except Exception as ws_err:
                                print(f"⚠️ WebSocket notification failed: {ws_err}")
                        else:
                            print(f"❌ Failed to update message {msg_id} with IPFS CID")
                else:
                    print(f"⚠️ IPFS upload failed: {ipfs_result.get('error', 'Not configured')}")
                
            except Exception as ipfs_error:
                print(f"❌ IPFS upload exception: {ipfs_error}")
                import traceback
                traceback.print_exc()
                ipfs_result = {'success': False, 'error': str(ipfs_error)}
            
            try:
                # Record on blockchain
                print(f"\n⛓️ Recording on blockchain...")
                blockchain_service = get_blockchain_service()
                blockchain_result = await blockchain_service.record_transfer(
                    file_hash=actual_hash,
                    file_name=filename,
                    sender_id=user_id,
                    receiver_id=room_id,
                    ipfs_cid=ipfs_result.get('cid', '') if ipfs_result else '',
                    file_size=file_size
                )
                
                if blockchain_result.get('success'):
                    print(f"✅ Blockchain recording successful: {blockchain_result.get('transaction_hash')}")
                    print(f"🔗 View on Etherscan: {blockchain_result.get('explorer_url')}")
                    
                    # ✅ UPDATE MESSAGE WITH BLOCKCHAIN DATA (for background uploads)
                    if msg_id:
                        updated = await ChatCRUD.update_message_blockchain_data(
                            message_id=msg_id,
                            blockchain_tx_hash=blockchain_result.get('transaction_hash'),
                            blockchain_block_number=blockchain_result.get('block_number')
                        )
                        if updated:
                            print(f"✅ Updated message {msg_id} with blockchain data")
                            
                            # 🔔 NOTIFY CLIENTS via WebSocket
                            try:
                                from routers.websocket import broadcast_to_room
                                await broadcast_to_room(
                                    room_id,
                                    {
                                        'type': 'message_updated',
                                        'message_id': msg_id,
                                        'blockchain_tx_hash': blockchain_result.get('transaction_hash'),
                                        'update_type': 'blockchain_complete'
                                    }
                                )
                                print(f"📢 Notified clients about blockchain completion")
                            except Exception as ws_err:
                                print(f"⚠️ WebSocket notification failed: {ws_err}")
                    
                    # Generate proof certificate
                    try:
                        certificate_service = get_certificate_service()
                        certificate_pdf = certificate_service.generate_blockchain_certificate(
                            file_info={
                                'name': filename,
                                'size': file_size,
                                'hash': actual_hash,
                                'sender_id': user_id,
                                'receiver_id': receiver_id,
                                'room_id': room_id,
                                'timestamp': datetime.now().isoformat()
                            },
                            blockchain_info=blockchain_result,
                            ipfs_info=ipfs_result if ipfs_result and ipfs_result.get('success') else None
                        )
                        
                        # Save certificate
                        os.makedirs("certificates", exist_ok=True)
                        certificate_path = f"certificates/{file_id}_proof.pdf"
                        with open(certificate_path, 'wb') as f:
                            f.write(certificate_pdf)
                        
                        print(f"📄 Certificate generated: {certificate_path}")
                        
                        # ✅ UPDATE MESSAGE WITH CERTIFICATE URL (for background uploads)
                        if msg_id:
                            await ChatCRUD.update_message_blockchain_data(
                                message_id=msg_id,
                                certificate_url=f"/certificates/{file_id}_proof.pdf"
                            )
                        
                    except Exception as cert_error:
                        print(f"⚠️ Certificate generation failed: {cert_error}")
                        
                else:
                    print(f"⚠️ Blockchain recording failed: {blockchain_result.get('error', 'Unknown error')}")
                    
            except Exception as blockchain_error:
                print(f"⚠️ Blockchain recording failed: {blockchain_error}")
                blockchain_result = {'success': False, 'error': str(blockchain_error)}
        
        # ✅ SMART TIMEOUT: Wait for small files (<50MB), skip for large files
        MAX_WAIT_SIZE = 50 * 1024 * 1024  # 50MB (images, small videos)
        if file_size < MAX_WAIT_SIZE:
            # Small file - wait up to 120s for blockchain/IPFS
            try:
                await asyncio.wait_for(record_blockchain_and_ipfs(), timeout=120.0)
                print(f"✅ Blockchain/IPFS completed for small file ({file_size} bytes)")
            except asyncio.TimeoutError:
                print(f"⚠️ Blockchain/IPFS timed out for small file (120s) - will retry in background after message creation")
            except Exception as bg_error:
                print(f"⚠️ Background task error: {bg_error}")
                import traceback
                traceback.print_exc()
        else:
            # Large file - skip for now, will start background task after message creation
            print(f"⏭️ Large file ({file_size / 1024 / 1024:.2f} MB) - will process blockchain/IPFS in background after message creation")
        
        # ✅ FIRE-AND-FORGET MESSAGE CREATION (Non-blocking background task)
        # Create message asynchronously without blocking response
        message_data = None
        message_error = None
        
        try:
            # Attempt to create chat message (3s timeout - faster fail)
            message = await asyncio.wait_for(
                ChatCRUD.send_file_message(
                    sender_id=user_id,
                    room_id=room_id,
                    file_session_id=None,  # ✅ Pass None instead of file_id string
                    file_path=final_path,
                    file_name=filename,
                    file_size=file_size,
                    file_hash=actual_hash,
                    reply_to_id=reply_to_id,
                    # ✅ Pass blockchain/IPFS data (may be None for large files in background)
                    blockchain_tx_hash=blockchain_result.get('transaction_hash') if blockchain_result and blockchain_result.get('success') else None,
                    blockchain_block_number=blockchain_result.get('block_number') if blockchain_result and blockchain_result.get('success') else None,
                    ipfs_cid=ipfs_result.get('cid') if ipfs_result and ipfs_result.get('success') else None,
                    certificate_url=f"/certificates/{file_id}_proof.pdf" if certificate_path and os.path.exists(certificate_path) else None
                ),
                timeout=3.0  # Reduced from 5s to fail faster
            )
            message_data = message
            message_id_for_update = message['id']  # Store for background updates
            print(f"✅ Message created: {message['id']}")
            
            # ✅ For large files, start background task NOW with message ID
            if file_size >= 50 * 1024 * 1024 and not (blockchain_result and ipfs_result):
                print(f"🚀 Starting background IPFS/blockchain for message {message_id_for_update}")
                task = asyncio.create_task(record_blockchain_and_ipfs(message_id_for_update))
                def handle_background_error(task):
                    try:
                        task.result()
                    except Exception as e:
                        print(f"❌ Background IPFS/blockchain task failed: {e}")
                        import traceback
                        traceback.print_exc()
                task.add_done_callback(handle_background_error)
            
            # Try WebSocket notification (best effort)
            try:
                await notify_chat_file_complete(room_id, message)
                print(f"✅ WebSocket notification sent")
            except Exception as ws_error:
                print(f"⚠️ WebSocket notification failed: {ws_error}")
                
        except asyncio.TimeoutError:
            message_error = "Database timeout (3s) - message not created"
            print(f"⚠️ Message creation timed out after 3s - file saved successfully")
        except Exception as msg_error:
            message_error = str(msg_error)
            print(f"⚠️ Message creation failed: {msg_error} - file saved successfully")
        
        # ✅ RETURN SUCCESS (even if message creation failed)
        # Note: For large files, blockchain/IPFS may still be processing in background
        result = {
            "status": "completed",
            "file_id": file_id,
            "file_path": final_path,
            "file_name": filename,
            "file_size": file_size,
            "file_hash": actual_hash,
            "message_id": message_data["id"] if message_data else None,
            "message_created": message_data is not None,
            "message_error": message_error,  # Include error info for frontend
            # Blockchain proof (may still be processing for large files)
            "blockchain": blockchain_result if blockchain_result else {
                'success': False, 
                'error': 'Processing in background (check later for large files)',
                'processing': True
            },
            "ipfs": ipfs_result if ipfs_result else {
                'success': False, 
                'error': 'Processing in background (check later for large files)',
                'processing': True
            },
            "certificate_url": f"/certificates/{file_id}_proof.pdf" if certificate_path and os.path.exists(certificate_path) else None
        }
        
        print(f"📤 Upload completion response: {result}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Complete upload error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to complete upload: {str(e)}"
        )


# ✅ RETRY MESSAGE CREATION (for files that completed upload but message creation failed)

@router.post("/files/{file_id}/retry-message")
async def retry_message_creation(
    file_id: str,
    room_id: str = Form(...),
    reply_to_id: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_active_user)
):
    """Retry creating a chat message for an already-uploaded file"""
    try:
        print(f"🔄 Retrying message creation for file {file_id} in room {room_id}")
        
        # Verify user is member of the room
        is_member = await ChatCRUD.is_user_in_room(current_user["id"], room_id)
        if not is_member:
            raise HTTPException(status_code=403, detail="Not a member of this room")
        
        # Check if file exists
        final_path = os.path.join("uploaded_files", file_id)
        if not os.path.exists(final_path):
            raise HTTPException(status_code=404, detail="File not found on server")
        
        # Get file info
        filename = file_id  # Original filename is the file_id in storage
        file_size = os.path.getsize(final_path)
        
        # Calculate hash
        actual_hash = hashlib.sha256()
        with open(final_path, "rb") as f:
            while chunk := f.read(8192):
                actual_hash.update(chunk)
        file_hash = actual_hash.hexdigest()
        
        # Try to create the message with extended timeout (10s for retry)
        try:
            message = await asyncio.wait_for(
                ChatCRUD.send_file_message(
                    sender_id=current_user["id"],
                    room_id=room_id,
                    file_session_id=None,  # ✅ Pass None instead of file_id string
                    file_path=final_path,
                    file_name=filename,
                    file_size=file_size,
                    file_hash=file_hash,
                    reply_to_id=reply_to_id
                ),
                timeout=10.0  # Longer timeout for manual retry
            )
            
            print(f"✅ Message created on retry: {message['id']}")
            
            # Try WebSocket notification
            try:
                await notify_chat_file_complete(room_id, message)
                print(f"✅ WebSocket notification sent")
            except Exception as ws_error:
                print(f"⚠️ WebSocket notification failed: {ws_error}")
            
            return {
                "status": "success",
                "message_id": message["id"],
                "message": message,
                "file_path": final_path,
                "file_name": filename,
                "file_size": file_size,
                "file_hash": file_hash
            }
            
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504,
                detail="Database timeout - message creation failed. Please try again later."
            )
        except Exception as msg_error:
            print(f"❌ Message creation failed on retry: {msg_error}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create message: {str(msg_error)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Retry message creation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retry message creation: {str(e)}"
        )


# ✅ BLOCKCHAIN VERIFICATION ENDPOINTS

@router.get("/files/{file_hash}/blockchain-status")
async def get_blockchain_status(
    file_hash: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Get blockchain verification status for a file"""
    try:
        blockchain_service = get_blockchain_service()
        
        if not blockchain_service.enabled:
            return {
                "blockchain_enabled": False,
                "message": "Blockchain service not configured"
            }
        
        # Check if transfer exists on blockchain
        transfer = await blockchain_service.get_transfer(file_hash)
        
        if transfer:
            return {
                "blockchain_enabled": True,
                "verified": True,
                "transfer": transfer,
                "explorer_url": blockchain_service.get_explorer_url(transfer.get('transaction_hash', '')),
                "contract_url": blockchain_service.get_contract_explorer_url()
            }
        else:
            return {
                "blockchain_enabled": True,
                "verified": False,
                "message": "Transfer not found on blockchain"
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check blockchain status: {str(e)}"
        )


@router.get("/certificates/{file_id}_proof.pdf")
async def download_certificate(
    file_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Download blockchain proof certificate"""
    try:
        certificate_path = f"certificates/{file_id}_proof.pdf"
        
        if not os.path.exists(certificate_path):
            raise HTTPException(
                status_code=404,
                detail="Certificate not found. It may still be generating."
            )
        
        from fastapi.responses import FileResponse
        return FileResponse(
            path=certificate_path,
            media_type='application/pdf',
            filename=f"blockchain_proof_{file_id}.pdf"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download certificate: {str(e)}"
        )


# ✅ FILE DOWNLOAD

@router.get("/files/{message_id}/download")
async def download_chat_file(
    message_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Download a file from chat message"""
    try:
        # Get message and verify access
        message = await ChatCRUD.get_message_by_id(message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Check if user has access to this room
        is_member = await ChatCRUD.is_user_in_room(current_user["id"], message["room_id"])
        if not is_member:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Verify message contains a file
        if message["message_type"] not in ["file", "image"]:
            raise HTTPException(status_code=400, detail="Message does not contain a file")
        
        file_path = message["file_path"]
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found on server")
        
        # ✅ USE EXISTING HASH VERIFICATION
        from utils.hash_utils import verify_file_integrity
        
        if not await verify_file_integrity(file_path, message["file_hash"]):
            raise HTTPException(status_code=500, detail="File integrity check failed")
        
        from fastapi.responses import FileResponse
        return FileResponse(
            path=file_path,
            media_type='application/octet-stream',
            filename=message["file_name"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ UTILITY ENDPOINTS

@router.post("/rooms/{room_id}/members/{user_id}")
async def add_user_to_room(
    room_id: str,
    user_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Add a user to an existing chat room (admin only)"""
    try:
        # Check if current user is admin of the room
        user_role = await ChatCRUD.get_user_role_in_room(current_user["id"], room_id)
        if user_role != "admin":
            raise HTTPException(status_code=403, detail="Only room admins can add members")
        
        # Check if target user exists
        target_user = await get_user_by_id(user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Add user to room
        success = await ChatCRUD.add_single_room_member(room_id, user_id, "member")
        
        if success:
            return {"status": "success", "message": f"User {target_user['username']} added to room"}
        else:
            raise HTTPException(status_code=400, detail="Failed to add user to room")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/rooms/{room_id}")
async def delete_room(
    room_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Delete a chat room (admin only, group chats only)"""
    try:
        print(f"🗑️ DELETE ROOM: {room_id} by user {current_user['id']}")
        
        # Get room details
        room = await ChatCRUD.get_chat_room_by_id(room_id)
        print(f"Room found: {room}")
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        # Check if it's a group chat
        if room["type"] != "group":
            raise HTTPException(status_code=400, detail="Cannot delete direct chats")
        
        # Check if current user is admin
        user_role = await ChatCRUD.get_user_role_in_room(current_user["id"], room_id)
        print(f"User role: {user_role}")
        if user_role != "admin":
            raise HTTPException(status_code=403, detail="Only room admins can delete rooms")
        
        # Get all room members before deleting (to clear their caches)
        members = await ChatCRUD.get_room_members_detailed(room_id)
        member_ids = [m["user_id"] for m in members]
        print(f"Room has {len(member_ids)} members")
        
        # Delete the room (cascade will delete members and messages)
        print(f"Deleting room {room_id}...")
        success = await ChatCRUD.delete_room(room_id)
        print(f"Delete result: {success}")
        
        if success:
            # Invalidate cache for ALL members who were in this room
            from services.cache_service import cache
            for member_id in member_ids:
                cache_key = f"rooms:{member_id}"
                deleted = await cache.delete(cache_key)
                print(f"Cleared cache for member: {member_id[:8]}... (deleted: {deleted})")
            
            # Also clear member cache for the room
            await cache.delete(f"members:{room_id}")
            
            # Also invalidate room-specific caches
            from services.cache_invalidation import invalidator
            await invalidator.invalidate_room(room_id)
            
            print(f"✅ Room {room_id[:8]}... deleted and all caches cleared")
            
            return {"status": "success", "message": f"Room deleted successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to delete room")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ DELETE ROOM ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/rooms/{room_id}/members/{user_id}")
async def remove_room_member(
    room_id: str,
    user_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Remove a member from room or leave room (admin or self)"""
    try:
        # Get room details
        room = await ChatCRUD.get_chat_room_by_id(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        # Check if it's a group chat
        if room["type"] != "group":
            raise HTTPException(status_code=400, detail="Cannot leave/remove from direct chats")
        
        # Check permissions: admin can remove anyone, user can remove self
        current_user_role = await ChatCRUD.get_user_role_in_room(current_user["id"], room_id)
        
        if user_id == current_user["id"]:
            # User is leaving
            success = await ChatCRUD.remove_room_member(room_id, user_id)
            message = "You left the room"
        elif current_user_role == "admin":
            # Admin is removing someone
            success = await ChatCRUD.remove_room_member(room_id, user_id)
            target_user = await get_user_by_id(user_id)
            message = f"Removed {target_user['username']} from room"
        else:
            raise HTTPException(status_code=403, detail="Only admins can remove other members")
        
        if success:
            return {"status": "success", "message": message}
        else:
            raise HTTPException(status_code=400, detail="Failed to remove member")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rooms/{room_id}/files")
async def get_room_files(
    room_id: str,
    limit: int = 50,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all files shared in a chat room"""
    try:
        # Check if user is member of the room
        is_member = await ChatCRUD.is_user_in_room(current_user["id"], room_id)
        if not is_member:
            raise HTTPException(status_code=403, detail="Not a member of this room")
        
        files = await ChatCRUD.get_chat_files_for_room(room_id, limit)
        
        return {
            "files": files,
            "total": len(files),
            "room_id": room_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rooms/{room_id}/search")
async def search_room_messages(
    room_id: str,
    q: str,
    limit: int = 20,
    current_user: dict = Depends(get_current_active_user)
):
    """Search messages in a chat room"""
    try:
        # Check if user is member of the room
        is_member = await ChatCRUD.is_user_in_room(current_user["id"], room_id)
        if not is_member:
            raise HTTPException(status_code=403, detail="Not a member of this room")
        
        if len(q.strip()) < 2:
            raise HTTPException(status_code=400, detail="Search query must be at least 2 characters")
        
        messages = await ChatCRUD.search_messages(room_id, q, limit)
        
        return {
            "messages": messages,
            "query": q,
            "total": len(messages),
            "room_id": room_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ BLOCKCHAIN ENDPOINTS

@router.get("/api/blockchain/transaction/{tx_hash}")
async def get_blockchain_transaction(tx_hash: str):
    """Get blockchain transaction details (public endpoint - no auth required)
    Accepts both tx_hash and file_hash for backward compatibility
    Also attempts to sync IPFS data from blockchain_records if missing
    """
    print(f"\n🚨 ENDPOINT HIT: /api/blockchain/transaction/{tx_hash[:20]}...")
    try:
        blockchain_service = get_blockchain_service()
        
        print(f"🔍 GET BLOCKCHAIN TRANSACTION: {tx_hash[:40]}...")
        print(f"   Blockchain service enabled: {blockchain_service.enabled}")
        
        transaction = None
        
        # Normalize the hash - remove 0x prefix if present for file_hash checks
        normalized_hash = tx_hash[2:] if tx_hash.startswith('0x') else tx_hash
        
        # Strategy 1: Try as tx_hash first (blockchain_records.tx_hash field)
        print(f"   🔍 Trying tx_hash lookup: {tx_hash[:20]}...")
        transaction = await blockchain_service.get_transaction(tx_hash)
        print(f"   TX hash result: {'Found' if transaction else 'Not found'}")
        
        # Strategy 2: If not found, try as file_hash (could be with or without 0x prefix)
        if not transaction and len(normalized_hash) == 64:
            print(f"   🔍 Trying file_hash lookup: {normalized_hash[:16]}...")
            try:
                result = blockchain_service.supabase.table("blockchain_records")\
                    .select("*")\
                    .eq("file_hash", normalized_hash)\
                    .execute()
                
                print(f"   File hash query result: {len(result.data) if result.data else 0} records")
                
                if result.data and len(result.data) > 0:
                    transaction = result.data[0]
                    print(f"   ✅ Found transaction by file_hash!")
                    print(f"   TX Hash: {transaction.get('tx_hash')}")
                    print(f"   IPFS CID: {transaction.get('ipfs_cid')}")
            except Exception as file_hash_error:
                print(f"   ⚠️ File hash lookup failed: {file_hash_error}")
        
        # ⚡ AUTO-SYNC: Try to update message with IPFS from blockchain if we found the transaction
        if transaction:
            try:
                # Find message with this file_hash to sync IPFS
                msg_result = blockchain_service.supabase.table("messages")\
                    .select("id, ipfs_cid, file_hash")\
                    .eq("file_hash", transaction.get('file_hash'))\
                    .execute()
                
                if msg_result.data and len(msg_result.data) > 0:
                    message = msg_result.data[0]
                    message_id = message['id']
                    
                    print(f"   Found message: {message_id}")
                    print(f"   Message IPFS: {message.get('ipfs_cid')}")
                    
                    # If message is missing IPFS but blockchain has it
                    if not message.get('ipfs_cid') and transaction.get('ipfs_cid'):
                        print(f"   🔄 Auto-syncing IPFS to message {message_id}...")
                        await ChatCRUD.sync_message_ipfs_from_blockchain(message_id)
            except Exception as sync_err:
                print(f"   ⚠️ Auto-sync failed (non-critical): {sync_err}")
        
        # If still not found, return 404
        if not transaction:
            print(f"   ❌ Transaction not found for: {tx_hash}")
            raise HTTPException(status_code=404, detail=f"Transaction not found for hash: {tx_hash}")
        
        return transaction
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Failed to get transaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/blockchain/explorer/tx/{tx_hash}")
async def blockchain_explorer_page(tx_hash: str):
    """Serve blockchain explorer HTML page"""
    from fastapi.responses import FileResponse
    
    explorer_path = os.path.join(os.path.dirname(__file__), "..", "blockchain_explorer.html")
    
    if not os.path.exists(explorer_path):
        raise HTTPException(status_code=404, detail="Explorer page not found")
    
    return FileResponse(explorer_path, media_type="text/html")


@router.get("/certificates/{file_id}_proof.pdf")
async def download_certificate(file_id: str):
    """Download blockchain proof certificate"""
    from fastapi.responses import FileResponse
    
    cert_path = f"certificates/{file_id}_proof.pdf"
    
    if not os.path.exists(cert_path):
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    return FileResponse(
        cert_path,
        media_type="application/pdf",
        filename=f"{file_id}_blockchain_proof.pdf"
    )