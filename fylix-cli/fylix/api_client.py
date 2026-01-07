"""
API client for FYLIX backend
Handles all HTTP/REST communication with FastAPI server
"""

import httpx
from typing import Dict, Any, Optional
from fylix.config import config


class APIClient:
    """HTTP client for FYLIX backend REST APIs"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        # Use 60s timeout - balance between speed and reliability
        self.client = httpx.AsyncClient(timeout=60.0)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authorization token"""
        headers = {"Content-Type": "application/json"}
        token = config.get_access_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    # ==================== AUTH ENDPOINTS ====================
    
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """Login to FYLIX backend"""
        response = await self.client.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password}
        )
        response.raise_for_status()
        return response.json()
    
    async def signup(self, email: str, username: str, password: str) -> Dict[str, Any]:
        """Sign up for FYLIX account"""
        response = await self.client.post(
            f"{self.base_url}/auth/signup",
            json={
                "email": email,
                "username": username,
                "password": password
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def get_me(self) -> Dict[str, Any]:
        """Get current user info"""
        response = await self.client.get(
            f"{self.base_url}/auth/me",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    # ==================== CHAT ROOM ENDPOINTS ====================
    
    async def get_user_rooms(self) -> Dict[str, Any]:
        """Get all chat rooms for current user"""
        response = await self.client.get(
            f"{self.base_url}/chat/rooms",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def create_direct_room(self, recipient_email: str) -> Dict[str, Any]:
        """Create or get direct chat room with recipient"""
        response = await self.client.post(
            f"{self.base_url}/chat/rooms",
            headers=self._get_headers(),
            json={
                "type": "direct",
                "members": [recipient_email]  # Backend expects list of user IDs/emails
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def get_room_messages(self, room_id: str, limit: int = 50) -> Dict[str, Any]:
        """Get messages from a chat room (includes file transfers)"""
        response = await self.client.get(
            f"{self.base_url}/chat/rooms/{room_id}/messages?limit={limit}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    # ==================== FILE TRANSFER ENDPOINTS ====================
    
    async def start_file_upload(
        self,
        room_id: str,
        filename: str,
        file_size: int,
        file_hash: str,
        total_chunks: int
    ) -> Dict[str, Any]:
        """Initialize chunked file upload"""
        response = await self.client.post(
            f"{self.base_url}/chat/rooms/{room_id}/files/start",
            headers=self._get_headers(),
            json={
                "filename": filename,
                "total_chunks": total_chunks,
                "file_size": file_size,
                "file_hash": file_hash
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def upload_chunk(
        self,
        room_id: str,
        file_id: str,
        chunk_number: int,
        total_chunks: int,
        chunk_data: bytes,
        chunk_hash: str
    ) -> Dict[str, Any]:
        """Upload a single file chunk"""
        files = {"chunk": (f"chunk_{chunk_number}", chunk_data)}
        data = {
            "file_id": file_id,
            "chunk_number": str(chunk_number),
            "total_chunks": str(total_chunks),
            "chunk_hash": chunk_hash
        }
        
        response = await self.client.post(
            f"{self.base_url}/chat/rooms/{room_id}/files/chunk",
            headers={"Authorization": f"Bearer {config.get_access_token()}"},
            data=data,
            files=files
        )
        response.raise_for_status()
        return response.json()
    
    async def complete_upload(
        self,
        room_id: str,
        file_id: str,
        file_hash: str,
        recipient_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mark upload as complete and trigger IPFS + blockchain"""
        # Backend expects Form data, not JSON (like websocket_test.html)
        data = {
            "file_id": file_id,
            "expected_hash": file_hash
        }
        if recipient_id:
            data["reply_to_id"] = recipient_id
        
        # Get auth token directly (avoid double "Bearer Bearer")
        token = config.get_access_token()
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        response = await self.client.post(
            f"{self.base_url}/chat/rooms/{room_id}/files/complete",
            headers=headers,
            data=data  # Use form data, not JSON
        )
        response.raise_for_status()
        return response.json()
    
    async def download_file(self, message_id: str) -> bytes:
        """Download file from a message"""
        response = await self.client.get(
            f"{self.base_url}/chat/files/{message_id}/download",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.content
    
    async def get_blockchain_proof(self, file_hash: str) -> Dict[str, Any]:
        """Get blockchain proof for file integrity verification"""
        response = await self.client.get(
            f"{self.base_url}/chat/api/blockchain/transaction/{file_hash}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()


# Global API client instance
api_client = APIClient()
