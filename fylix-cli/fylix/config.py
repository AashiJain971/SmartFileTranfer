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
        self.download_history_file = self.config_dir / "download_history.json"
        
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def save_credentials(self, email: str, access_token: str, refresh_token: str, user_id: str, username: str):
        """Store authentication credentials locally"""
        # Get download history from separate persistent file (survives logout)
        download_history = self.get_download_history()
        downloaded_files = download_history.get("downloaded_files", [])
        sent_files = download_history.get("sent_files", [])
        
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
        """Remove stored credentials (logout) - preserves download history"""
        # Save download history before clearing credentials
        creds = self.get_credentials()
        if creds:
            self.save_download_history(
                creds.get("downloaded_files", []),
                creds.get("sent_files", [])
            )
        
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
    
    def get_download_history(self) -> Dict[str, Any]:
        """Get persistent download history (survives logout/login)"""
        if not self.download_history_file.exists():
            return {"downloaded_files": [], "sent_files": []}
        
        try:
            with open(self.download_history_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {"downloaded_files": [], "sent_files": []}
    
    def save_download_history(self, downloaded_files: list, sent_files: list):
        """Save download history to persistent file"""
        history = {
            "downloaded_files": downloaded_files,
            "sent_files": sent_files,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        with open(self.download_history_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    def add_downloaded_file(self, message_id: str):
        """Add a file to download history"""
        history = self.get_download_history()
        downloaded_files = history.get("downloaded_files", [])
        
        if message_id not in downloaded_files:
            downloaded_files.append(message_id)
            self.save_download_history(downloaded_files, history.get("sent_files", []))
            
            # Also update credentials if logged in
            creds = self.get_credentials()
            if creds:
                creds["downloaded_files"] = downloaded_files
                with open(self.credentials_file, 'w') as f:
                    json.dump(creds, f, indent=2)
    
    def add_sent_file(self, message_id: str):
        """Add a file to sent history"""
        history = self.get_download_history()
        sent_files = history.get("sent_files", [])
        
        if message_id not in sent_files:
            sent_files.append(message_id)
            self.save_download_history(history.get("downloaded_files", []), sent_files)
            
            # Also update credentials if logged in
            creds = self.get_credentials()
            if creds:
                creds["sent_files"] = sent_files
                with open(self.credentials_file, 'w') as f:
                    json.dump(creds, f, indent=2)


# Global config instance
config = Config()
