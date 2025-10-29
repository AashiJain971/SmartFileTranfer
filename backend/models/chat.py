from pydantic import BaseModel, Field
from typing import Optional, List, Union
from datetime import datetime
from enum import Enum

class MessageType(str, Enum):
    TEXT = "text"
    FILE = "file"
    IMAGE = "image"

class ChatRoomType(str, Enum):
    DIRECT = "direct"
    GROUP = "group"

class MessageStatus(str, Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"

class UserRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"

# ✅ REQUEST MODELS FOR CHAT OPERATIONS

class CreateChatRoomRequest(BaseModel):
    """Request to create a new chat room"""
    name: Optional[str] = None
    type: ChatRoomType
    members: List[str] = Field(..., description="List of user IDs or emails to add to the room")

class SendTextMessageRequest(BaseModel):
    """Request to send a text message"""
    content: str = Field(..., min_length=1, max_length=4000)
    reply_to_id: Optional[str] = None

class SendFileMessageRequest(BaseModel):
    """Request to send a file message (for small files)"""
    file_name: str
    file_size: int
    file_hash: str
    reply_to_id: Optional[str] = None

class StartChatFileUploadRequest(BaseModel):
    """Request to start chunked file upload for chat"""
    filename: str
    total_chunks: int
    file_size: int
    file_hash: str
    reply_to_id: Optional[str] = None

class MarkMessageStatusRequest(BaseModel):
    """Request to mark message status (read/delivered)"""
    message_id: str
    status: MessageStatus

class TypingIndicatorRequest(BaseModel):
    """Request to send typing indicator"""
    is_typing: bool

# ✅ RESPONSE MODELS FOR API ENDPOINTS

class UserSummary(BaseModel):
    """Summary user information for chat"""
    id: str
    username: str
    email: str
    is_online: Optional[bool] = False

class ChatRoomMember(BaseModel):
    """Chat room member information"""
    user_id: str
    username: str
    role: UserRole
    joined_at: datetime

class MessageResponse(BaseModel):
    """Complete message response"""
    id: str
    room_id: str
    sender_id: str
    sender_username: str
    message_type: MessageType
    content: Optional[str] = None
    
    # File-related fields
    file_session_id: Optional[int] = None
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    file_hash: Optional[str] = None
    
    # Reply information
    reply_to: Optional['MessageResponse'] = None
    
    created_at: datetime
    updated_at: datetime
    
    # User's status for this message
    status: Optional[MessageStatus] = None

class ChatRoomResponse(BaseModel):
    """Complete chat room information"""
    id: str
    name: Optional[str]
    type: ChatRoomType
    created_by: str
    created_by_username: str
    members: List[ChatRoomMember]
    last_message: Optional[MessageResponse] = None
    unread_count: Optional[int] = 0
    created_at: datetime
    updated_at: datetime

class ChatRoomListResponse(BaseModel):
    """List of chat rooms"""
    rooms: List[ChatRoomResponse]
    total: int

class MessagesResponse(BaseModel):
    """List of messages in a room"""
    messages: List[MessageResponse]
    total: int
    limit: int
    offset: int
    room_id: str

class FileUploadResponse(BaseModel):
    """Response for file upload operations"""
    file_id: str
    upload_url: str
    chunk_size: int
    message_id: Optional[str] = None

class MessageStatusResponse(BaseModel):
    """Response for message status operations"""
    message_id: str
    status: MessageStatus
    timestamp: datetime

# ✅ WEBSOCKET MESSAGE MODELS

class WebSocketMessage(BaseModel):
    """Base WebSocket message"""
    type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ChatWebSocketMessage(WebSocketMessage):
    """Chat-specific WebSocket message"""
    room_id: str

class NewMessageWebSocket(ChatWebSocketMessage):
    """New message notification"""
    type: str = "new_message"
    message: MessageResponse

class TypingWebSocket(ChatWebSocketMessage):
    """Typing indicator"""
    type: str = "typing"
    user_id: str
    username: str
    is_typing: bool

class UserJoinedWebSocket(ChatWebSocketMessage):
    """User joined room notification"""
    type: str = "user_joined"
    user_id: str
    username: str

class UserLeftWebSocket(ChatWebSocketMessage):
    """User left room notification"""
    type: str = "user_left"
    user_id: str
    username: str

class MessageStatusWebSocket(ChatWebSocketMessage):
    """Message status update"""
    type: str = "message_status"
    message_id: str
    user_id: str
    status: MessageStatus

class FileUploadProgressWebSocket(ChatWebSocketMessage):
    """File upload progress in chat"""
    type: str = "file_upload_progress"
    file_id: str
    sender_id: str
    progress: float
    chunk_number: int
    total_chunks: int
    file_name: str

class FileUploadCompleteWebSocket(ChatWebSocketMessage):
    """File upload completed in chat"""
    type: str = "file_upload_complete"
    file_id: str
    message: MessageResponse

# ✅ ERROR MODELS

class ChatError(BaseModel):
    """Chat-specific error response"""
    error_code: str
    message: str
    details: Optional[dict] = None

# Enable forward references for reply_to field
MessageResponse.model_rebuild()