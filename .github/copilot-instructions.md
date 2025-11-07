# SmartFileTransfer AI Development Guide

## Project Architecture

**Smart File Transfer** is a real-time file upload system with chat capabilities, built as a full-stack application:

- **Backend**: FastAPI (Python) with WebSocket support for real-time updates
- **Frontend**: Next.js 15 (React 19) with Tailwind CSS
- **Database**: Supabase (PostgreSQL) for file sessions, auth, and chat
- **Testing**: `backend/websocket_test.html` - comprehensive standalone test suite

### Core Components

```
backend/
  ├── routers/          # API endpoints (upload.py, auth.py, chat.py, websocket.py)
  ├── services/         # Business logic (chunk_service.py, network_predictor.py, cache_service.py)
  ├── db/              # Database layer (crud.py, database.py)
  ├── models/          # Pydantic schemas
  ├── dependencies/    # Auth middleware
  └── temp_chunks/     # Temporary chunk storage before merge

frontend/
  └── src/
      ├── app/         # Next.js App Router pages
      ├── components/  # Reusable UI components
      ├── contexts/    # React contexts
      ├── hooks/       # Custom React hooks
      └── utils/       # API clients and helpers
```

## Critical Upload Architecture

### Chunked Upload System
Files are split into chunks (256KB-2MB) and uploaded sequentially:
1. **Client**: Splits file → uploads chunks with `fileId`, `chunkNumber`, `totalChunks`
2. **Backend**: Saves to `temp_chunks/{fileId}/chunk_{n}`, tracks in Supabase
3. **Merge**: After all chunks uploaded, merges into `uploaded_files/` and cleans temp chunks
4. **Resume**: Client queries `/upload/uploaded_chunks/{fileId}` to resume from last successful chunk

**Key Files**:
- `backend/services/chunk_service.py` - `save_chunk()`, `merge_chunks()`, `cleanup_chunks()`
- `backend/routers/upload.py` - `/upload/` POST endpoint, `/uploaded_chunks/{fileId}` GET endpoint
- `backend/websocket_test.html` - Client-side chunk upload logic (lines 3300-3500)

### Auto-Resume Logic (In-Memory State)
- **File object** stored only in JavaScript memory (not localStorage/IndexedDB)
- **On network loss**: Pause upload, listen for `online` event
- **On reconnect**: Query server for last uploaded chunk index, resume from `lastIndex + 1`
- **Tab closed**: Cannot resume automatically - requires "Reupload" with file reselection

**Do NOT**:
- Store File objects in localStorage (not possible)
- Restart from chunk 0 on network reconnect
- Implement manual Resume/Cancel buttons (auto-resume only)

## WebSocket Communication

### Upload Progress WebSocket
- **Endpoint**: `ws://localhost:8000/ws/upload/{fileId}?token={accessToken}`
- **Purpose**: Real-time progress updates during upload
- **Message Format**: `{"uploaded": int, "total": int}`
- **Reconnection**: Auto-retry with exponential backoff (3 attempts, 5s timeout)

### Chat WebSocket
- **Endpoint**: `ws://localhost:8000/ws/chat/{roomId}?token={accessToken}`
- **Auth**: JWT token in query string
- **Heartbeat**: Ping every 30s to keep connection alive
- **Auto-reconnect**: Exponential backoff on disconnect

## Configuration & Environment

### Backend (`backend/config.py`)
```python
SUPABASE_URL, SUPABASE_KEY    # Required env vars
MAX_CHUNK_SIZE = 2MB          # Dynamic chunk sizing
DEFAULT_CHUNK_SIZE = 1MB
TEMP_DIR = "temp_chunks"
UPLOAD_DIR = "uploaded_files"
```

### Frontend
- API Base: `http://localhost:8000`
- WebSocket: `ws://localhost:8000`
- No `.env` - configuration in code

## Development Workflow

### Running the Application
```bash
# Backend (from /backend)
python main.py  # FastAPI on port 8000

# Frontend (from /frontend)
npm run dev     # Next.js on port 3000
```

### Testing
- **Primary**: Open `backend/websocket_test.html` in browser
- **Features**: Auth, file upload, chat, WebSocket monitoring, network simulation
- **UI**: WhatsApp-inspired design with real-time indicators

### Database Schema
- Tables: `file_sessions`, `users`, `chat_rooms`, `messages` (in Supabase)
- Key tracking: `uploaded_chunks` count per `file_id`

## Code Conventions

### Backend Patterns
1. **Async/await**: All file I/O and database calls use async
2. **Error handling**: Raise `HTTPException` with status codes
3. **CRUD separation**: Database logic in `db/crud.py`, never in routers
4. **Type hints**: Pydantic models for request/response validation

### Frontend Patterns
1. **Client components**: All pages/components use `'use client'` directive
2. **State management**: Local state + React Context (no Redux)
3. **Storage**: `localStorage` for uploaded file metadata (name, size, date)
4. **Styling**: Tailwind utility classes with gradient designs

### Naming Conventions
- Files: `snake_case.py` (backend), `PascalCase.js` (frontend components)
- Functions: `snake_case` (backend), `camelCase` (frontend)
- Variables: `camelCase` everywhere
- Constants: `UPPER_SNAKE_CASE`

## Integration Points

### Supabase Integration
- **Client**: `supabase = create_client(SUPABASE_URL, SUPABASE_KEY)`
- **Usage**: Direct SQL-style queries via `supabase.table('name').select().execute()`
- **Auth**: JWT tokens generated/validated via Supabase Auth

### Frontend → Backend Communication
1. **REST**: Axios/fetch to `http://localhost:8000/upload`, `/auth`, etc.
2. **WebSocket**: Native WebSocket API for real-time features
3. **CORS**: Configured for `localhost:3000` in `backend/main.py`

## Network Resilience Features

### AI-Powered Chunk Sizing (Planned)
- `network_predictor.py` - ML model for adaptive chunk sizing
- Monitors: bandwidth, latency, packet loss
- Adjusts chunk size dynamically (256KB-2MB range)

### Connection Monitoring
- `navigator.onLine` + online/offline events
- Visual indicators: Green (online), Red (offline), Yellow (connecting)
- Auto-pause uploads on disconnect

## Testing Reference

### Key Test Files
- `backend/websocket_test.html` - Full integration test suite (7000+ lines)
- `backend/test_*.py` - Unit tests for auth, chat, upload logic

### Common Test Scenarios
1. Upload large file (>10MB) with network interruption
2. Close tab mid-upload, reopen, verify "Reupload" shows
3. WebSocket reconnection after server restart
4. Multiple concurrent uploads (max 3 by default)

## Important Notes

### Current User Request Context
You're implementing **automatic upload resume** with:
- In-memory state only (no persistent storage)
- Auto-pause on offline, auto-resume on online
- No manual Resume/Cancel buttons
- Render test UI in `websocket_test.html`

### Known Issues & Patterns
- Many routers (`auth.py`, `chat.py`, `websocket.py`) are empty placeholders
- `main.py` only includes `upload.router` - other routers not yet integrated
- Documentation files (`.md` in backend) are mostly empty
- Focus on `websocket_test.html` for testing, not frontend app

### File Structure Quirks
- Chunks stored as `temp_chunks/chat-{uuid}-{fileId}/chunk_{n}` (notice "chat-" prefix)
- Multiple similar functions in `websocket_test.html` (legacy + new implementations)
- Frontend uses `SafeStorage` wrapper around localStorage for error handling

## Quick Reference Commands

```bash
# Backend
uvicorn main:app --reload                    # Start with auto-reload
python -m pytest backend/test_*.py           # Run tests

# Frontend  
npm run dev                                  # Development server
npm run build && npm start                   # Production build

# Database
# Configure in Supabase dashboard, use connection string in .env
```

## Design Philosophy

- **WhatsApp-inspired UI**: Green gradients (#25d366), rounded corners, smooth animations
- **Real-time first**: WebSockets for all live updates
- **Resilient uploads**: Network-aware chunking with auto-resume
- **Developer-friendly**: Comprehensive test suite in single HTML file
