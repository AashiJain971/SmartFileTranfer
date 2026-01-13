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
        # Use 60s timeout to handle slow free-tier databases (Supabase, etc.)
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
    
    async def signup(self, email: str, username: str, password: str, first_name: str = None, last_name: str = None) -> Dict[str, Any]:
        """Sign up for FYLIX account"""
        payload = {
            "email": email,
            "username": username,
            "password": password
        }
        if first_name:
            payload["first_name"] = first_name
        if last_name:
            payload["last_name"] = last_name
            
        response = await self.client.post(
            f"{self.base_url}/auth/signup",
            json=payload
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
    
    async def delete_account(self, password: str) -> Dict[str, Any]:
        """Permanently delete account"""
        response = await self.client.delete(
            f"{self.base_url}/auth/account",
            params={"password": password},
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
    
    async def create_group_chat(self, name: str, members: list = None) -> Dict[str, Any]:
        """Create a group chat"""
        payload = {
            "type": "group",
            "name": name,
            "members": members if members else []  # Backend requires this field
        }
        
        response = await self.client.post(
            f"{self.base_url}/chat/rooms",
            headers=self._get_headers(),
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    async def get_room_details(self, room_id: str) -> Dict[str, Any]:
        """Get room details including members"""
        response = await self.client.get(
            f"{self.base_url}/chat/rooms/{room_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def add_room_member(self, room_id: str, user_identifier: str) -> Dict[str, Any]:
        """Add member to room (admin only) - user_identifier can be email, username, or user_id"""
        # Backend endpoint accepts user_id in URL and should handle email/username lookup
        response = await self.client.post(
            f"{self.base_url}/chat/rooms/{room_id}/members/{user_identifier}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def delete_room(self, room_id: str) -> Dict[str, Any]:
        """Delete a room (admin only, group chats only)"""
        response = await self.client.delete(
            f"{self.base_url}/chat/rooms/{room_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def remove_room_member(self, room_id: str, user_id: str) -> Dict[str, Any]:
        """Remove member from room or leave room"""
        response = await self.client.delete(
            f"{self.base_url}/chat/rooms/{room_id}/members/{user_id}",
            headers=self._get_headers()
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
    
    async def get_uploaded_chunks(self, file_id: str) -> Dict[str, Any]:
        """Query server for list of uploaded chunks (for resume after network loss)"""
        try:
            response = await self.client.get(
                f"{self.base_url}/upload/uploaded_chunks/{file_id}",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            # If endpoint doesn't exist or server is down, return empty
            return {"uploaded_chunks": []}
    
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
        
        # Use extended timeout for blockchain/IPFS verification (130s)
        # Backend waits up to 120s for small files (<50MB)
        import httpx
        async with httpx.AsyncClient(timeout=130.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/rooms/{room_id}/files/complete",
                headers=headers,
                data=data  # Use form data, not JSON
            )
        
            # Better error handling
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                error_body = ""
                try:
                    error_body = e.response.text
                except:
                    pass
                raise Exception(f"HTTP {e.response.status_code}: {error_body or e}") from e
            
            return response.json()
    
    async def download_file(self, message_id: str) -> bytes:
        """Download file from a message - uses extended timeout for large files"""
        # Use extended timeout for file downloads (5 minutes for very large files)
        download_timeout = httpx.Timeout(300.0, connect=30.0)
        
        response = await self.client.get(
            f"{self.base_url}/chat/files/{message_id}/download",
            headers=self._get_headers(),
            timeout=download_timeout
        )
        response.raise_for_status()
        return response.content
    
    async def search_message_by_id(self, message_id_prefix: str) -> Dict[str, Any]:
        """Search for a message by ID prefix - FAST direct query"""
        response = await self.client.get(
            f"{self.base_url}/chat/messages/search/{message_id_prefix}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
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
