import hashlib
import aiofiles
from pathlib import Path
from typing import Union

async def compute_file_hash(file_path: Union[str, Path], algorithm: str = "sha256") -> str:
    """Compute file hash asynchronously with memory efficiency"""
    hash_obj = hashlib.new(algorithm)
    
    async with aiofiles.open(file_path, 'rb') as f:
        # Read in chunks to handle large files efficiently
        while chunk := await f.read(8192):  # 8KB chunks
            hash_obj.update(chunk)
    
    return hash_obj.hexdigest()

def compute_chunk_hash(chunk_data: bytes, algorithm: str = "sha256") -> str:
    """Compute hash for a chunk of data"""
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(chunk_data)
    return hash_obj.hexdigest()

async def verify_file_integrity(
    file_path: Union[str, Path], 
    expected_hash: str, 
    algorithm: str = "sha256"
) -> bool:
    """Verify file integrity against expected hash"""
    try:
        computed_hash = await compute_file_hash(file_path, algorithm)
        return computed_hash.lower() == expected_hash.lower()
    except Exception:
        return False

# Alias for backward compatibility
calculate_file_hash = compute_file_hash