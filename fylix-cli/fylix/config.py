"""
Configuration management for FYLIX CLI
Handles credentials and transfer state persistence
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


class Config:
    """Manage CLI configuration and local storage"""
    
    def __init__(self):
        self.config_dir = Path.home() / ".fylix"
        self.credentials_file = self.config_dir / "credentials.json"
        self.transfers_file = self.config_dir / "transfers.json"
        
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def save_credentials(self, email: str, access_token: str, refresh_token: str, user_id: str, username: str):
        """Store authentication credentials locally"""
        # Preserve existing downloaded_files and sent_files if they exist
        existing_creds = self.get_credentials()
        downloaded_files = existing_creds.get("downloaded_files", []) if existing_creds else []
        sent_files = existing_creds.get("sent_files", []) if existing_creds else []
        
        credentials = {
            "email": email,
            "user_id": user_id,
            "username": username,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "logged_in_at": datetime.utcnow().isoformat(),
            "downloaded_files": downloaded_files,
            "sent_files": sent_files
        }
        
        with open(self.credentials_file, 'w') as f:
            json.dump(credentials, f, indent=2)
        
        # Secure the credentials file (Unix-like systems)
        if os.name != 'nt':  # Not Windows
            os.chmod(self.credentials_file, 0o600)
    
    def get_credentials(self) -> Optional[Dict[str, Any]]:
        """Retrieve stored credentials"""
        if not self.credentials_file.exists():
            return None
        
        try:
            with open(self.credentials_file, 'r') as f:
                return json.load(f)
        except Exception:
            return None
    
    def clear_credentials(self):
        """Remove stored credentials (logout)"""
        if self.credentials_file.exists():
            self.credentials_file.unlink()
    
    def get_access_token(self) -> Optional[str]:
        """Get the current access token"""
        creds = self.get_credentials()
        return creds.get("access_token") if creds else None
    
    def get_user_id(self) -> Optional[str]:
        """Get the current user ID"""
        creds = self.get_credentials()
        return creds.get("user_id") if creds else None
    
    def is_logged_in(self) -> bool:
        """Check if user is logged in"""
        return self.get_credentials() is not None
    
    def save_transfer_state(self, transfer_id: str, state: Dict[str, Any]):
        """
        Persist transfer state for resume capability
        Stores: file_path, recipient, uploaded_chunks, total_chunks, file_hash, etc.
        """
        transfers = self.get_all_transfers()
        transfers[transfer_id] = {
            **state,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        with open(self.transfers_file, 'w') as f:
            json.dump(transfers, f, indent=2)
    
    def get_transfer_state(self, transfer_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve transfer state for resume"""
        transfers = self.get_all_transfers()
        return transfers.get(transfer_id)
    
    def get_all_transfers(self) -> Dict[str, Dict[str, Any]]:
        """Get all stored transfers"""
        if not self.transfers_file.exists():
            return {}
        
        try:
            with open(self.transfers_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    
    def update_transfer_status(self, transfer_id: str, status: str, **kwargs):
        """Update transfer status and other fields"""
        state = self.get_transfer_state(transfer_id)
        if state:
            state["status"] = status
            state.update(kwargs)
            self.save_transfer_state(transfer_id, state)
    
    def remove_transfer(self, transfer_id: str):
        """Remove a transfer from local storage"""
        transfers = self.get_all_transfers()
        if transfer_id in transfers:
            del transfers[transfer_id]
            with open(self.transfers_file, 'w') as f:
                json.dump(transfers, f, indent=2)


# Global config instance
config = Config()
