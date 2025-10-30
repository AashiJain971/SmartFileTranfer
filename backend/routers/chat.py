from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from typing import List, Optional
from models.chat import *
from db.chat_crud import ChatCRUD
from db.auth_crud import get_user_by_id, get_user_by_email
from dependencies.auth import get_current_active_user
from routers.websocket import chat_manager, notify_chat_file_progress, notify_chat_file_complete
from utils.file_utils import save_upload_file, get_file_extension
from utils.hash_utils import calculate_file_hash
import os
import shutil
import uuid
import json
from datetime import datetime

router = APIRouter(prefix="/chat", tags=["chat"])

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
    """Start chunked file upload for chat - uses existing upload system"""
    try:
        # Check room membership
        is_member = await ChatCRUD.is_user_in_room(current_user["id"], room_id)
        if not is_member:
            raise HTTPException(status_code=403, detail="Not a member of this room")
        
        # Use existing file session system
        from db.crud import create_file_session
        
        # Generate unique file ID for this upload session first
        file_id = f"chat-{uuid.uuid4().hex[:8]}-{room_id}"
        
        file_session = await create_file_session(
            file_id,  # ✅ PROVIDE file_id AS FIRST ARGUMENT
            request.filename,
            request.total_chunks,
            request.file_size,
            request.file_hash,
            current_user["id"],
            upload_type="chat",  # ✅ MARK AS CHAT UPLOAD
            chat_room_id=room_id  # ✅ ASSOCIATE WITH CHAT ROOM
        )
        
        return FileUploadResponse(
            file_id=file_id,
            upload_url=f"/chat/rooms/{room_id}/files/chunk",
            chunk_size=1048576,  # 1MB chunks
            message_id=None  # Will be created when upload completes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    """Upload file chunk for chat - REUSES existing chunk upload logic"""
    try:
        # Verify room membership
        is_member = await ChatCRUD.is_user_in_room(current_user["id"], room_id)
        if not is_member:
            raise HTTPException(status_code=403, detail="Not a member of this room")
        
        # Use existing chunk upload logic
        from routers.upload import process_chunk_upload
        
        chunk_data = await chunk.read()
        try:
            result = await process_chunk_upload(
                file_id=file_id,
                chunk_number=chunk_number,
                chunk_data=chunk_data,
                chunk_hash=chunk_hash,
                user_id=current_user["id"]
            )
            
            print(f"DEBUG: Chat router - result type: {type(result)}, value: {result}")
            
            # ✅ NOTIFY CHAT ROOM VIA WEBSOCKET
            progress_data = {
                "progress": result.get("progress", 0),
                "chunk_number": chunk_number,
                "total_chunks": total_chunks,
                "file_name": result.get("filename", "")
            }
        except Exception as e:
            print(f"DEBUG: Chat router - Exception in process_chunk_upload: {type(e).__name__}: {e}")
            print(f"DEBUG: Exception details - status_code: {getattr(e, 'status_code', 'N/A')}, detail: {getattr(e, 'detail', 'N/A')}")
            import traceback
            print(f"DEBUG: Full traceback: {traceback.format_exc()}")
            raise
        
        await notify_chat_file_progress(room_id, file_id, current_user["id"], progress_data)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rooms/{room_id}/files/complete")
async def complete_chat_file_upload(
    room_id: str,
    file_id: str = Form(...),
    expected_hash: str = Form(...),
    reply_to_id: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_active_user)
):
    """Complete chunked file upload and create chat message"""
    try:
        print(f"DEBUG: complete_chat_file_upload called with file_id={file_id}, room_id={room_id}")
        
        # Verify room membership
        is_member = await ChatCRUD.is_user_in_room(current_user["id"], room_id)
        if not is_member:
            print(f"DEBUG: User {current_user['id']} not a member of room {room_id}")
            raise HTTPException(status_code=403, detail="Not a member of this room")
        
        print(f"DEBUG: Room membership verified")
        
        # Use existing complete upload logic
        from routers.upload import complete_file_upload
        
        print(f"DEBUG: About to call complete_file_upload")
        completed_file = await complete_file_upload(
            file_id=file_id,
            expected_hash=expected_hash,
            user_id=current_user["id"]
        )
        print(f"DEBUG: complete_file_upload returned: {completed_file}")
        
        # Create chat message with the completed file
        print(f"DEBUG: About to call send_file_message")
        print(f"DEBUG: completed_file data: {completed_file}")
        print(f"DEBUG: file_session_id: {completed_file['session_id']} (type: {type(completed_file['session_id'])})")
        
        try:
            message = await ChatCRUD.send_file_message(
                sender_id=current_user["id"],
                room_id=room_id,
                file_session_id=completed_file["session_id"],
                file_path=completed_file["file_path"],
                file_name=completed_file["original_filename"],
                file_size=completed_file["file_size"],
                file_hash=completed_file["file_hash"],
                reply_to_id=reply_to_id
            )
            print(f"DEBUG: send_file_message returned: {message}")
        except Exception as e:
            print(f"ERROR: Exception in send_file_message: {type(e).__name__}: {e}")
            import traceback
            print(f"ERROR: Full traceback: {traceback.format_exc()}")
            raise
        
        # ✅ NOTIFY CHAT ROOM VIA WEBSOCKET
        try:
            print(f"DEBUG: About to call notify_chat_file_complete")
            await notify_chat_file_complete(room_id, message)
            print(f"DEBUG: WebSocket notification sent successfully")
        except Exception as ws_error:
            print(f"ERROR: WebSocket notification failed: {type(ws_error).__name__}: {ws_error}")
            # Continue even if WebSocket fails
        
        result = {
            "message_id": message["id"],
            "file_info": completed_file,
            "status": "completed"
        }
        print(f"DEBUG: Returning result: {result}")
        return result
        
    except HTTPException as he:
        print(f"DEBUG: HTTPException in complete_chat_file_upload: {he.status_code} - {he.detail}")
        raise he
    except Exception as e:
        print(f"DEBUG: Exception in complete_chat_file_upload: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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