"""
IPFS Service for decentralized file storage
Supports both Alchemy IPFS and public gateways
"""

import aiohttp
import asyncio
import os
import json
from typing import Optional, Dict, Any
from pathlib import Path
import hashlib

class IPFSService:
    """Service for uploading and retrieving files from IPFS"""
    
    def __init__(self):
        """Initialize IPFS service"""
        # Alchemy IPFS API (if available)
        self.alchemy_api_key = os.getenv("ALCHEMY_IPFS_API_KEY")
        self.alchemy_api_secret = os.getenv("ALCHEMY_IPFS_API_SECRET")
        
        # Pinata IPFS API (alternative) - supports both old API keys and new JWT
        self.pinata_api_key = os.getenv("PINATA_API_KEY")
        self.pinata_secret_key = os.getenv("PINATA_SECRET_KEY")
        self.pinata_jwt = os.getenv("PINATA_JWT")  # NEW: JWT token
        
        # DEBUG: Print what we got
        print(f"🔍 DEBUG: PINATA_API_KEY = {self.pinata_api_key[:10] + '...' if self.pinata_api_key else 'NOT SET'}")
        print(f"🔍 DEBUG: PINATA_SECRET_KEY = {self.pinata_secret_key[:10] + '...' if self.pinata_secret_key else 'NOT SET'}")
        print(f"🔍 DEBUG: PINATA_JWT = {self.pinata_jwt[:20] + '...' if self.pinata_jwt else 'NOT SET'}")
        
        # IPFS endpoints
        self.alchemy_upload_url = "https://ipfs.sftproject.io/api/v0/add"
        self.pinata_upload_url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
        self.public_gateways = [
            "https://ipfs.io/ipfs/",
            "https://gateway.pinata.cloud/ipfs/",
            "https://cloudflare-ipfs.com/ipfs/",
            "https://dweb.link/ipfs/"
        ]
        
        # Check which IPFS provider is configured
        if self.pinata_jwt or (self.pinata_api_key and self.pinata_secret_key):
            self.use_pinata = True
            self.use_alchemy = False
            if self.pinata_jwt:
                print("✅ Pinata IPFS configured (JWT)")
            else:
                print("✅ Pinata IPFS configured (API Key - may have scope issues)")
        elif self.alchemy_api_key and self.alchemy_api_secret:
            self.use_alchemy = True
            self.use_pinata = False
            print("✅ Alchemy IPFS configured")
        else:
            self.use_alchemy = False
            self.use_pinata = False
            print("⚠️ IPFS WARNING: No IPFS provider configured")
            print("   Files won't be uploaded to IPFS (using local storage only)")
            print("   To enable: Set PINATA_JWT or (PINATA_API_KEY + PINATA_SECRET_KEY)")
    
    async def upload_file(
        self,
        file_path: str,
        file_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload file to IPFS
        
        Args:
            file_path: Path to the file
            file_name: Optional custom filename
            
        Returns:
            dict: Upload result with CID and gateway URLs
        """
        if self.use_pinata:
            return await self._upload_to_pinata(file_path, file_name)
        elif self.use_alchemy:
            return await self._upload_to_alchemy(file_path, file_name)
        else:
            # Return mock CID if IPFS not configured
            print("⚠️ IPFS upload skipped (not configured)")
            return {
                'success': False,
                'cid': None,
                'error': 'IPFS not configured',
                'gateway_urls': []
            }
    
    async def _upload_to_pinata(
        self,
        file_path: str,
        file_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload file to Pinata IPFS using streaming for large files"""
        try:
            print(f"\n📤 Uploading to Pinata IPFS: {file_name or file_path}")
            
            # Get file size without reading entire file
            file_size = os.path.getsize(file_path)
            print(f"   File size: {file_size / 1024 / 1024:.2f} MB")
            print(f"   File path: {file_path}")
            print(f"   File exists: {os.path.exists(file_path)}")
            
            # ✅ Stream file instead of loading into memory (crucial for large files)
            file_handle = open(file_path, 'rb')
            print("   ✅ File handle opened successfully")
            
            # Prepare multipart form data for Pinata
            form_data = aiohttp.FormData()
            form_data.add_field(
                'file',
                file_handle,  # ✅ Pass file handle for streaming
                filename=file_name or Path(file_path).name,
                content_type='application/octet-stream'
            )
            
            # Pinata headers - use JWT if available (recommended), otherwise use API keys
            if self.pinata_jwt:
                headers = {
                    'Authorization': f'Bearer {self.pinata_jwt}'
                }
                print("   Using Pinata JWT authentication")
            else:
                headers = {
                    'pinata_api_key': self.pinata_api_key,
                    'pinata_secret_api_key': self.pinata_secret_key
                }
                print("   Using Pinata API Key authentication (legacy)")
            
            # ✅ Dynamic timeout based on file size
            # Base 120s + 90s per 100MB (min 120s, max 30 minutes)
            # For 163MB: 120 + (1.63 * 90) = 267s (~4.5 min)
            # For 1GB: 120 + (10 * 90) = 1020s (~17 min)
            mb_size = file_size / (1024 * 1024)
            timeout_seconds = max(120, min(1800, int(120 + (mb_size / 100) * 90)))
            print(f"   Upload timeout: {timeout_seconds}s ({timeout_seconds/60:.1f} min)")
            
            async with aiohttp.ClientSession() as session:
                print("   Uploading to Pinata IPFS...")
                
                try:
                    async with session.post(
                        self.pinata_upload_url,
                        data=form_data,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=timeout_seconds)
                    ) as response:
                        
                        if response.status != 200:
                            error_text = await response.text()
                            print(f"   ❌ Upload failed: {error_text}")
                            return {
                                'success': False,
                                'error': error_text,
                                'status_code': response.status
                            }
                        
                        result = await response.json()
                        cid = result.get('IpfsHash')
                        
                        if not cid:
                            print(f"   ❌ No CID in response: {result}")
                            return {
                                'success': False,
                                'error': 'No CID returned',
                                'response': result
                            }
                        
                        print(f"   ✅ Uploaded to IPFS: {cid}")
                        
                        # Generate gateway URLs
                        gateway_urls = [f"{gateway}{cid}" for gateway in self.public_gateways]
                        
                        return {
                            'success': True,
                            'cid': cid,
                            'size': file_size,
                            'gateway_urls': gateway_urls,
                            'primary_url': gateway_urls[1],  # Use Pinata gateway as primary
                            'file_name': file_name or Path(file_path).name,
                            'pinata_url': f"https://gateway.pinata.cloud/ipfs/{cid}"
                        }
                finally:
                    # ✅ Always close file handle
                    file_handle.close()
                    
        except asyncio.TimeoutError:
            print(f"   ❌ IPFS upload timeout ({timeout_seconds}s exceeded)")
            return {
                'success': False,
                'error': f'Upload timeout ({timeout_seconds}s)',
                'cid': None
            }
        except Exception as e:
            print(f"   ❌ Pinata IPFS upload failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'cid': None
            }
    
    async def _upload_to_alchemy(
        self,
        file_path: str,
        file_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload file to Alchemy IPFS (legacy support)"""
        if not self.use_alchemy:
            return {
                'success': False,
                'cid': None,
                'error': 'IPFS not configured',
                'gateway_urls': []
            }
        
        try:
            print(f"\n📤 Uploading to IPFS: {file_name or file_path}")
            
            # Read file
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            file_size = len(file_data)
            print(f"   File size: {file_size / 1024 / 1024:.2f} MB")
            
            # Prepare multipart form data
            form_data = aiohttp.FormData()
            form_data.add_field(
                'file',
                file_data,
                filename=file_name or Path(file_path).name,
                content_type='application/octet-stream'
            )
            
            # Upload to Alchemy IPFS with authentication
            auth = aiohttp.BasicAuth(
                login=self.alchemy_api_key,
                password=self.alchemy_api_secret
            )
            
            async with aiohttp.ClientSession() as session:
                print("   Uploading to Alchemy IPFS...")
                
                async with session.post(
                    self.alchemy_upload_url,
                    data=form_data,
                    auth=auth,
                    timeout=aiohttp.ClientTimeout(total=300)  # 5 minute timeout
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"   ❌ Upload failed: {error_text}")
                        return {
                            'success': False,
                            'error': error_text,
                            'status_code': response.status
                        }
                    
                    result = await response.json()
                    cid = result.get('Hash') or result.get('IpfsHash')
                    
                    if not cid:
                        print(f"   ❌ No CID in response: {result}")
                        return {
                            'success': False,
                            'error': 'No CID returned',
                            'response': result
                        }
                    
                    print(f"   ✅ Uploaded to IPFS: {cid}")
                    
                    # Generate gateway URLs
                    gateway_urls = [f"{gateway}{cid}" for gateway in self.public_gateways]
                    
                    return {
                        'success': True,
                        'cid': cid,
                        'size': file_size,
                        'gateway_urls': gateway_urls,
                        'primary_url': gateway_urls[0],
                        'file_name': file_name or Path(file_path).name
                    }
                    
        except asyncio.TimeoutError:
            print("   ❌ IPFS upload timeout (file too large or slow connection)")
            return {
                'success': False,
                'error': 'Upload timeout',
                'cid': None
            }
        except Exception as e:
            print(f"   ❌ IPFS upload failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'cid': None
            }
    
    async def upload_metadata(
        self,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Upload JSON metadata to IPFS
        
        Args:
            metadata: Dictionary to upload as JSON
            
        Returns:
            dict: Upload result with CID
        """
        if self.use_pinata:
            return await self._upload_metadata_to_pinata(metadata)
        elif self.use_alchemy:
            return await self._upload_metadata_to_alchemy(metadata)
        else:
            return {
                'success': False,
                'cid': None,
                'error': 'IPFS not configured'
            }
    
    async def _upload_metadata_to_pinata(
        self,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Upload JSON metadata to Pinata"""
        try:
            # Pinata JSON upload endpoint
            url = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
            
            headers = {
                'pinata_api_key': self.pinata_api_key,
                'pinata_secret_api_key': self.pinata_secret_key,
                'Content-Type': 'application/json'
            }
            
            payload = {
                'pinataContent': metadata
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        return {
                            'success': False,
                            'error': error_text
                        }
                    
                    result = await response.json()
                    cid = result.get('IpfsHash')
                    
                    return {
                        'success': True,
                        'cid': cid,
                        'gateway_urls': [f"{gateway}{cid}" for gateway in self.public_gateways]
                    }
                    
        except Exception as e:
            print(f"❌ Pinata metadata upload failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _upload_metadata_to_alchemy(
        self,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Upload JSON metadata to Alchemy IPFS (legacy)"""
        if not self.use_alchemy:
            return {
                'success': False,
                'cid': None,
                'error': 'IPFS not configured'
            }
        
        try:
            # Convert metadata to JSON
            json_data = json.dumps(metadata, indent=2).encode('utf-8')
            
            # Prepare form data
            form_data = aiohttp.FormData()
            form_data.add_field(
                'file',
                json_data,
                filename='metadata.json',
                content_type='application/json'
            )
            
            # Upload
            auth = aiohttp.BasicAuth(
                login=self.alchemy_api_key,
                password=self.alchemy_api_secret
            )
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.alchemy_upload_url,
                    data=form_data,
                    auth=auth,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        return {
                            'success': False,
                            'error': error_text
                        }
                    
                    result = await response.json()
                    cid = result.get('Hash') or result.get('IpfsHash')
                    
                    return {
                        'success': True,
                        'cid': cid,
                        'gateway_urls': [f"{gateway}{cid}" for gateway in self.public_gateways]
                    }
                    
        except Exception as e:
            print(f"❌ IPFS metadata upload failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_gateway_url(self, cid: str, gateway_index: int = 0) -> str:
        """Get gateway URL for a CID"""
        if gateway_index >= len(self.public_gateways):
            gateway_index = 0
        return f"{self.public_gateways[gateway_index]}{cid}"
    
    async def verify_availability(self, cid: str) -> bool:
        """Check if file is available on IPFS"""
        try:
            async with aiohttp.ClientSession() as session:
                # Try first gateway with HEAD request
                url = self.get_gateway_url(cid, 0)
                async with session.head(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    return response.status == 200
        except:
            return False


# Singleton instance
_ipfs_service = None

def get_ipfs_service() -> IPFSService:
    """Get singleton IPFS service instance"""
    global _ipfs_service
    if _ipfs_service is None:
        _ipfs_service = IPFSService()
    return _ipfs_service
