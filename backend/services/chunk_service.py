import hashlib
import asyncio
import aiofiles
from pathlib import Path
from typing import List, Optional, Dict, Set
from fastapi import UploadFile, HTTPException
import time
import os
import tempfile

from config import settings
from services.network_monitor import network_monitor
from utils.hash_utils import compute_file_hash

class ChunkService:
    def __init__(self):
        self.active_uploads: Dict[str, Set[int]] = {}
        self.chunk_locks: Dict[str, asyncio.Lock] = {}
    
    async def save_chunk_with_verification(
        self, 
        file_id: str, 
        chunk_number: int, 
        chunk_data: bytes,
        expected_hash: str,
        max_retries: int = 3
    ) -> bool:
        """Save chunk with integrity verification and retry logic"""
        
        try:
            print(f"Starting chunk save: file_id={file_id}, chunk_number={chunk_number}, size={len(chunk_data)}")
            
            # Get or create lock for this file
            if file_id not in self.chunk_locks:
                self.chunk_locks[file_id] = asyncio.Lock()
            
            async with self.chunk_locks[file_id]:
                # Verify chunk hash immediately
                computed_hash = hashlib.sha256(chunk_data).hexdigest()
                if computed_hash != expected_hash:
                    raise ValueError(f"Chunk {chunk_number} hash mismatch. Expected: {expected_hash}, Got: {computed_hash}")
                
                # Prepare paths
                file_dir = settings.TEMP_DIR / file_id
                print(f"Creating directory: {file_dir}")
                file_dir.mkdir(exist_ok=True)
                chunk_path = file_dir / f"chunk_{chunk_number}"
                temp_chunk_path = file_dir / f"chunk_{chunk_number}.tmp"
            
            # Clean up any existing incomplete chunks
            await self._cleanup_incomplete_chunk(chunk_path, temp_chunk_path)
            
            # Attempt to save with retries
            for attempt in range(max_retries):
                try:
                    start_time = time.time()
                    
                    # Atomic write operation
                    async with aiofiles.open(temp_chunk_path, 'wb') as f:
                        await f.write(chunk_data)
                        # Force write to disk (aiofiles doesn't support fsync directly)
                        await f.flush()
                    
                    # Verify written data
                    if not await self._verify_chunk_integrity(temp_chunk_path, chunk_data, expected_hash):
                        raise ValueError(f"Chunk {chunk_number} failed post-write verification")
                    
                    # Atomic rename
                    temp_chunk_path.rename(chunk_path)
                    
                    # Record successful upload metrics
                    upload_time = time.time() - start_time
                    network_monitor.record_upload(len(chunk_data), upload_time, True)
                    
                    # Track active upload
                    if file_id not in self.active_uploads:
                        self.active_uploads[file_id] = set()
                    self.active_uploads[file_id].add(chunk_number)
                    
                    return True
                    
                except Exception as e:
                    print(f"Chunk save attempt {attempt + 1} failed: {str(e)}")
                    # Record failed attempt
                    upload_time = time.time() - start_time
                    network_monitor.record_upload(len(chunk_data), upload_time, False)
                    
                    # Clean up failed attempt
                    await self._cleanup_incomplete_chunk(chunk_path, temp_chunk_path)
                    
                    if attempt == max_retries - 1:
                        raise HTTPException(
                            status_code=500,
                            detail=f"Failed to save chunk {chunk_number} after {max_retries} attempts: {str(e)}"
                        )
                    
                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)
                    
            return False
        
        except Exception as e:
            print(f"Critical error in save_chunk_with_verification: {str(e)}")
            raise
    
    async def _cleanup_incomplete_chunk(self, chunk_path: Path, temp_chunk_path: Path):
        """Remove any incomplete or corrupted chunk files"""
        try:
            if temp_chunk_path.exists():
                temp_chunk_path.unlink()
            
            # Check if existing chunk is complete and valid
            if chunk_path.exists():
                # If chunk exists but is corrupted/incomplete, remove it
                stat = chunk_path.stat()
                if stat.st_size == 0:  # Empty file
                    chunk_path.unlink()
                    
        except Exception as e:
            print(f"Warning: Could not clean up chunk files: {e}")
    
    async def _verify_chunk_integrity(self, file_path: Path, original_data: bytes, expected_hash: str) -> bool:
        """Verify chunk integrity after writing to disk"""
        try:
            # Check file exists and has correct size
            if not file_path.exists():
                return False
            
            stat = file_path.stat()
            if stat.st_size != len(original_data):
                return False
            
            # Verify hash of written data
            async with aiofiles.open(file_path, 'rb') as f:
                written_data = await f.read()
            
            written_hash = hashlib.sha256(written_data).hexdigest()
            return written_hash == expected_hash
            
        except Exception:
            return False
    
    async def get_uploaded_chunks(self, file_id: str) -> List[int]:
        """Get list of successfully uploaded chunks"""
        file_dir = settings.TEMP_DIR / file_id
        if not file_dir.exists():
            return []
        
        uploaded_chunks = []
        for chunk_file in file_dir.glob("chunk_*"):
            if chunk_file.suffix != ".tmp":  # Ignore temporary files
                try:
                    chunk_number = int(chunk_file.name.split("_")[1])
                    
                    # Verify chunk is complete (not zero bytes)
                    if chunk_file.stat().st_size > 0:
                        uploaded_chunks.append(chunk_number)
                except (ValueError, IndexError):
                    continue
        
        return sorted(uploaded_chunks)
    
    async def merge_chunks_with_verification(
        self, 
        file_id: str, 
        total_chunks: int, 
        expected_file_hash: str,
        filename: str
    ) -> tuple[Optional[Path], str]:
        """Merge chunks and verify final file integrity"""
        
        # Verify all chunks are present
        uploaded_chunks = await self.get_uploaded_chunks(file_id)
        expected_chunks = set(range(total_chunks))
        
        if set(uploaded_chunks) != expected_chunks:
            missing_chunks = expected_chunks - set(uploaded_chunks)
            raise HTTPException(
                status_code=400,
                detail=f"Missing chunks: {sorted(missing_chunks)}"
            )
        
        # Merge chunks
        output_path = settings.UPLOAD_DIR / filename
        temp_output_path = settings.UPLOAD_DIR / f"{filename}.tmp"
        
        try:
            async with aiofiles.open(temp_output_path, 'wb') as outfile:
                for chunk_number in range(total_chunks):
                    chunk_path = settings.TEMP_DIR / file_id / f"chunk_{chunk_number}"
                    
                    if not chunk_path.exists():
                        raise ValueError(f"Chunk {chunk_number} not found during merge")
                    
                    async with aiofiles.open(chunk_path, 'rb') as chunk_file:
                        chunk_data = await chunk_file.read()
                        await outfile.write(chunk_data)
            
            # Verify merged file hash
            computed_hash = await compute_file_hash(temp_output_path)
            if computed_hash != expected_file_hash:
                temp_output_path.unlink()
                raise HTTPException(
                    status_code=400,
                    detail=f"File integrity check failed. Expected: {expected_file_hash}, Got: {computed_hash}"
                )
            
            # Atomic rename to final location
            temp_output_path.rename(output_path)
            
            # Clean up chunks
            await self.cleanup_chunks(file_id)
            
            return output_path, computed_hash
            
        except Exception as e:
            # Clean up temp file on error
            if temp_output_path.exists():
                temp_output_path.unlink()
            raise e
    
    async def cleanup_chunks(self, file_id: str):
        """Clean up temporary chunks and tracking data"""
        try:
            file_dir = settings.TEMP_DIR / file_id
            if file_dir.exists():
                # Remove all chunk files
                for chunk_file in file_dir.iterdir():
                    chunk_file.unlink()
                file_dir.rmdir()
            
            # Clean up tracking data
            if file_id in self.active_uploads:
                del self.active_uploads[file_id]
            if file_id in self.chunk_locks:
                del self.chunk_locks[file_id]
                
        except Exception as e:
            print(f"Warning: Could not fully clean up chunks for {file_id}: {e}")
    
    async def cleanup_stale_uploads(self, max_age_hours: int = 24):
        """Clean up old incomplete uploads"""
        try:
            current_time = time.time()
            cutoff_time = current_time - (max_age_hours * 3600)
            
            for file_dir in settings.TEMP_DIR.iterdir():
                if file_dir.is_dir():
                    # Check if directory is old
                    if file_dir.stat().st_mtime < cutoff_time:
                        file_id = file_dir.name
                        await self.cleanup_chunks(file_id)
                        print(f"Cleaned up stale upload: {file_id}")
                        
        except Exception as e:
            print(f"Error during stale upload cleanup: {e}")

# Global chunk service instance
chunk_service = ChunkService()
