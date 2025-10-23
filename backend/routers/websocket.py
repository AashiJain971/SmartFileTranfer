from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from typing import Dict, Set, Optional
import json
import asyncio
from datetime import datetime
from services.auth_service import AuthService

router = APIRouter()

class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        # Store active connections by file_id with user info
        self.active_connections: Dict[str, Dict[WebSocket, dict]] = {}
        self.auth_service = AuthService()
    
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

# Global connection manager
manager = ConnectionManager()

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
        payload = manager.auth_service.verify_token(token)
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
    
    await manager.connect(websocket, file_id, user_info)
    
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
        manager.disconnect(websocket, file_id)
    except Exception as e:
        print(f"WebSocket error for {file_id}: {e}")
        manager.disconnect(websocket, file_id)