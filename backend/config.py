import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    # Database
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    
    # File handling
    MAX_CHUNK_SIZE: int = int(os.getenv("MAX_CHUNK_SIZE", "2097152"))  # 2MB
    MIN_CHUNK_SIZE: int = int(os.getenv("MIN_CHUNK_SIZE", "262144"))   # 256KB
    DEFAULT_CHUNK_SIZE: int = int(os.getenv("DEFAULT_CHUNK_SIZE", "1048576"))  # 1MB
    
    # Network resilience
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    CHUNK_TIMEOUT: int = int(os.getenv("CHUNK_TIMEOUT", "30"))
    CONCURRENT_UPLOADS: int = int(os.getenv("CONCURRENT_UPLOADS", "3"))
    
    # Paths
    TEMP_DIR: Path = Path("temp_chunks")
    UPLOAD_DIR: Path = Path("uploaded_files")
    
    def __init__(self):
        # Validate required settings
        if not self.SUPABASE_URL or not self.SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        
        # Create directories
        self.TEMP_DIR.mkdir(exist_ok=True)
        self.UPLOAD_DIR.mkdir(exist_ok=True)

settings = Settings()