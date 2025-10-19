# Smart File Transfer Backend - Installation & Usage

## 🚀 Quick Setup

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy your Supabase credentials to `.env`:
```bash
# Your actual Supabase credentials
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_key_here

# Optional: Database URL for advanced configurations
DATABASE_URL=postgresql://your_db_url_here

# Network & Performance Settings (already configured)
MAX_CHUNK_SIZE=2097152
MIN_CHUNK_SIZE=262144
DEFAULT_CHUNK_SIZE=1048576
MAX_RETRIES=3
CHUNK_TIMEOUT=30
CONCURRENT_UPLOADS=3
```

### 3. Setup Database Tables
Run the SQL commands from `database_schema.sql` in your Supabase SQL editor.

### 4. Start the Server
```bash
python main.py
```
or
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 📡 API Endpoints

### Start Upload Session
```http
POST /upload/start
Content-Type: multipart/form-data

file_id: unique_file_id
filename: example.pdf
total_chunks: 100
file_size: 10485760
file_hash: sha256_hash_of_original_file
```

### Upload Chunk
```http
POST /upload/chunk
Content-Type: multipart/form-data

file_id: unique_file_id
chunk_number: 0
total_chunks: 100
chunk_hash: sha256_hash_of_this_chunk
chunk: [binary_data]
```

### Check Upload Status
```http
GET /upload/status/{file_id}
```

### Complete Upload
```http
POST /upload/complete
Content-Type: multipart/form-data

file_id: unique_file_id
expected_hash: sha256_hash_of_original_file
```

### Cancel Upload
```http
DELETE /upload/cancel/{file_id}
```

## 🛡️ Security Features

- **No Hardcoded Credentials**: All sensitive data in environment variables
- **Chunk Integrity Verification**: Each chunk verified with SHA256 hash
- **File Integrity Verification**: Complete file verified after merge
- **Automatic Cleanup**: Incomplete/failed uploads cleaned automatically

## 🌐 Network Resilience Features

- **Adaptive Chunk Sizing**: Automatically adjusts chunk size based on network performance
- **Retry Logic**: Failed chunks retry with exponential backoff
- **Incomplete Chunk Detection**: Detects and removes corrupted partial chunks
- **Concurrent Uploads**: Smart detection of when to use parallel transfers
- **Network Monitoring**: Tracks upload performance and adapts accordingly

## 📊 Monitoring & Health

### Health Check
```http
GET /health
```

### API Information
```http
GET /
```

## 🧹 Background Tasks

The system automatically:
- Cleans up stale uploads older than 24 hours
- Removes incomplete/corrupted chunks
- Optimizes performance based on network conditions
- Updates database session status

## 🔧 Configuration

All settings can be adjusted via environment variables:

- `MAX_CHUNK_SIZE`: Maximum chunk size (default: 2MB)
- `MIN_CHUNK_SIZE`: Minimum chunk size (default: 256KB)
- `DEFAULT_CHUNK_SIZE`: Starting chunk size (default: 1MB)
- `MAX_RETRIES`: Maximum retry attempts per chunk (default: 3)
- `CHUNK_TIMEOUT`: Upload timeout in seconds (default: 30)
- `CONCURRENT_UPLOADS`: Max concurrent chunk uploads (default: 3)

## 🚨 Error Handling

The system provides detailed error responses with:
- Specific error messages
- Retry recommendations
- Suggested chunk sizes for unstable networks
- Upload attempt tracking

## 📈 Performance Features

- **Asynchronous Operations**: Non-blocking I/O for better performance
- **Memory Efficient**: Streams large files without loading entirely in memory
- **Database Indexing**: Optimized queries for fast status checks
- **Background Processing**: Cleanup and maintenance tasks run in background