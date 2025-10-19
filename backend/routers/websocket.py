from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import asyncio
from datetime import datetime

router = APIRouter()

class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        # Store active connections by file_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, file_id: str):
        """Accept WebSocket connection for a specific file upload"""
        await websocket.accept()
        
        if file_id not in self.active_connections:
            self.active_connections[file_id] = set()
        
        self.active_connections[file_id].add(websocket)
        print(f"📡 WebSocket connected for file: {file_id}")
    
    def disconnect(self, websocket: WebSocket, file_id: str):
        """Remove WebSocket connection"""
        if file_id in self.active_connections:
            self.active_connections[file_id].discard(websocket)
            
            # Remove empty sets
            if not self.active_connections[file_id]:
                del self.active_connections[file_id]
        
        print(f"📡 WebSocket disconnected for file: {file_id}")
    
    async def send_progress_update(self, file_id: str, data: dict):
        """Send progress update to all clients watching this file"""
        if file_id not in self.active_connections:
            return
        
        # Add timestamp to data
        data["timestamp"] = datetime.utcnow().isoformat()
        message = json.dumps(data)
        
        # Send to all connected clients for this file
        disconnected = set()
        for websocket in self.active_connections[file_id].copy():
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
async def websocket_upload_progress(websocket: WebSocket, file_id: str):
    """WebSocket endpoint for real-time upload progress"""
    await manager.connect(websocket, file_id)
    
    try:
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connected",
            "file_id": file_id,
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