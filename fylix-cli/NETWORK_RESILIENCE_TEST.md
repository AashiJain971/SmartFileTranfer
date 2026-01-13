# Network Resilience Testing Guide

## ✅ Auto-Resume Feature Implemented

The FYLIX CLI now includes **automatic network resilience** with pause/resume capabilities.

## 🎯 Key Features

### 1. **Automatic Pause on Network Loss**
- Detects network disconnection automatically
- Pauses upload immediately
- Shows clear status: `⏸️ PAUSED - Network disconnected`

### 2. **Auto-Resume on Network Restore**
- Automatically resumes when network returns
- Queries server for last successful chunk
- Continues from exact point of failure
- Shows: `✓ Network restored - resuming upload`

### 3. **Visual Indicators**
- **Red**: `⏸️ PAUSED - Network disconnected (chunk X/Y)`
- **Yellow**: `⚠️ Network unstable - checking connection...`
- **Green**: `✓ Network restored - resuming upload`
- **Cyan**: `🔄 Syncing with server state...`

### 4. **Smart Retry Logic**
- Up to 100 retry attempts for network errors
- Exponential backoff (2 seconds between retries)
- Separate handling for:
  - Network errors (auto-resume)
  - Server errors (show helpful messages)
  - Other errors (limited retries)

## 🧪 How to Test

### Test 1: WiFi Toggle During Upload

```bash
# Terminal 1: Start backend (if not running)
cd /Users/adityajain/SmartFileTransfer/backend
python3 main.py

# Terminal 2: Activate venv and send large file
cd /Users/adityajain/SmartFileTransfer/fylix-cli
source venv/bin/activate
fylix send /path/to/large/file.mp4 recipient@email.com

# During upload: Turn OFF WiFi
# Expected: See "⏸️ PAUSED - Network disconnected"
# Expected: Upload pauses, waiting message shown

# Turn WiFi back ON
# Expected: See "✓ Network restored - resuming upload"
# Expected: Upload continues from last successful chunk
```

### Test 2: Network Simulation with pfctl (Advanced)

```bash
# Block outgoing connections to localhost:8000
sudo pfctl -e
echo "block drop proto tcp from any to 127.0.0.1 port 8000" | sudo pfctl -f -

# Start upload - should pause immediately
fylix send file.txt user@example.com

# Restore network
sudo pfctl -d

# Upload should auto-resume
```

### Test 3: Server Restart During Upload

```bash
# Start upload
fylix send largefile.mp4 user@example.com

# In another terminal: Kill backend
pkill -f "python3 main.py"

# Expected: Upload pauses with network error
# Expected: Shows "⏸️ PAUSED - Network disconnected"

# Restart backend
cd /Users/adityajain/SmartFileTransfer/backend
python3 main.py

# Expected: Upload auto-resumes
```

## 📊 What You Should See

### Normal Upload (Good Network)
```
📤 Preparing to send: video.mp4
Size: 18.0 MB
...
📦 Uploading 18 chunks...
Network: Monitoring connection for auto-resume
Uploading video.mp4 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:05
✓ File sent successfully!
```

### Network Loss During Upload
```
📤 Preparing to send: video.mp4
Size: 18.0 MB
...
📦 Uploading 18 chunks...
Network: Monitoring connection for auto-resume
Uploading video.mp4 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  45% 0:00:08

⚠️  Network unstable - checking connection...
⏸️  Upload paused - Network disconnected
Waiting for network... (will auto-resume when connected)
⏸️ PAUSED - Network disconnected (chunk 8/18) ━━━━━━━━━━━━━━━━━━━━  45%
⏸️  Upload paused - Network disconnected
Waiting for network... (will auto-resume when connected)
```

### Network Restored
```
↻ Network available, retrying chunk 8...
✓ Network restored - resuming upload
Uploading video.mp4 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  50% 0:00:10
...
✓ File sent successfully!
```

## 🔍 Server State Sync

When network returns, the CLI:
1. **Queries server**: `GET /upload/uploaded_chunks/{fileId}`
2. **Compares state**: Local chunks vs server chunks
3. **Syncs if needed**: Shows `🔄 Syncing with server state...`
4. **Resumes upload**: From `lastChunk + 1`

## ⚠️ Important Notes

### What IS Supported ✅
- Auto-pause on WiFi toggle
- Auto-resume when WiFi returns
- Survives server restarts
- Network instability handling
- Server state synchronization

### What is NOT Supported ❌
- Resume after CLI process crash (use `fylix resume <id>` for manual resume)
- Resume after file object is lost (need to reupload)
- Resume after tab/terminal closed (need manual resume)

## 🐛 Troubleshooting

### "Send failed: Server error 500"
**Cause**: Backend not running or database timeout

**Fix**:
```bash
# Check if backend is running
ps aux | grep "python3 main.py"

# If not running, start it
cd /Users/adityajain/SmartFileTransfer/backend
python3 main.py
```

### Upload Stuck at "PAUSED"
**Cause**: Server is down or unreachable

**Check**:
```bash
# Test backend health
curl http://localhost:8000/

# If no response, restart backend
```

### "Could not find user" Error
**Cause**: Recipient email not registered

**Fix**:
```bash
# Make sure recipient has signed up
fylix signup
```

## 🎓 Implementation Details

### Network Detection
- Uses `httpx` to ping backend (`GET /`)
- 3-second timeout for quick detection
- Checks on every failed chunk upload

### Retry Strategy
```python
max_retries = 100  # Allow many retries for network issues
retry_delay = 2    # 2 seconds between attempts

# Network errors: Unlimited retries until success
# Server errors: Show helpful message, retry 3 times
# Other errors: Fail after 3 attempts
```

### Chunk State Persistence
```python
# Stored in ~/.fylix/credentials.json
{
  "transfers": {
    "file-id-xyz": {
      "uploaded_chunks": [0, 1, 2, 3, 4],  # Which chunks succeeded
      "last_chunk": 4,                     # Last successful chunk
      "status": "uploading"                # Current state
    }
  }
}
```

## 🚀 Next Steps

### Recommended Tests
1. ✅ Upload 100MB file, toggle WiFi 3 times during upload
2. ✅ Upload with unstable network (coffee shop WiFi)
3. ✅ Restart backend mid-upload
4. ✅ Verify chunks resume from correct position

### Future Enhancements
- WebSocket for real-time network status
- Browser API integration (`navigator.onLine`)
- Visual network quality indicator
- Adaptive chunk sizing based on network quality

---

**Status**: ✅ Feature Complete and Ready for Testing

**Last Updated**: January 13, 2026
