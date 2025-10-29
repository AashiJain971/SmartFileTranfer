import os
import shutil
from typing import Optional
from fastapi import UploadFile

def save_upload_file(upload_file: UploadFile, destination: str) -> str:
    """
    Save an uploaded file to the specified destination.
    
    Args:
        upload_file: The FastAPI UploadFile object
        destination: The full path where the file should be saved
        
    Returns:
        str: The path where the file was saved
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    
    # Save the file
    with open(destination, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    
    return destination

def get_file_extension(filename: str) -> str:
    """
    Get the file extension from a filename.
    
    Args:
        filename: The name of the file
        
    Returns:
        str: The file extension (including the dot)
    """
    return os.path.splitext(filename)[1]

def ensure_directory_exists(directory_path: str) -> None:
    """
    Ensure that a directory exists, creating it if necessary.
    
    Args:
        directory_path: Path to the directory
    """
    os.makedirs(directory_path, exist_ok=True)

def get_file_size(file_path: str) -> Optional[int]:
    """
    Get the size of a file in bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        int: File size in bytes, or None if file doesn't exist
    """
    try:
        return os.path.getsize(file_path)
    except OSError:
        return None

def delete_file_if_exists(file_path: str) -> bool:
    """
    Delete a file if it exists.
    
    Args:
        file_path: Path to the file to delete
        
    Returns:
        bool: True if file was deleted, False if it didn't exist
    """
    try:
        os.remove(file_path)
        return True
    except OSError:
        return False
