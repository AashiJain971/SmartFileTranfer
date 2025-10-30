#!/usr/bin/env python3
"""
Test script to verify WebSocket connection and database timeout fixes
"""
import asyncio
import websockets
import json
import time
from datetime import datetime

async def test_authentication():
    """Test database authentication with potential timeout"""
    print("🧪 Testing database authentication...")
    
    import requests
    
    # Test login
    login_data = {
        "email": "aashij971@gmail.com",
        "password": "AashiJain123@"
    }
    
    try:
        response = requests.post("http://localhost:8000/auth/login", json=login_data, timeout=10)
        if response.status_code == 200:
            data = response.json()
            access_token = data.get("access_token")
            print(f"✅ Login successful, token: {access_token[:20]}...")
            return access_token
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

async def test_websocket_connection(token, room_id="65871a3c-dfa0-4b43-a28a-47a5e61a4692"):
    """Test WebSocket connection with error handling"""
    print(f"🧪 Testing WebSocket connection to room: {room_id}")
    
    ws_url = f"ws://localhost:8000/ws/chat/{room_id}?token={token}"
    
    try:
        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10) as websocket:
            print("✅ WebSocket connected successfully")
            
            # Send a test message
            test_message = {
                "type": "text_message",
                "content": "Test message from connection fix verification",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await websocket.send(json.dumps(test_message))
            print("✅ Test message sent")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"✅ Received response: {response}")
            except asyncio.TimeoutError:
                print("⚠️  No response received (this might be expected)")
            
            # Send ping
            ping_message = {"type": "ping", "timestamp": datetime.utcnow().isoformat()}
            await websocket.send(json.dumps(ping_message))
            print("✅ Ping sent")
            
            # Wait for pong
            try:
                pong_response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                pong_data = json.loads(pong_response)
                if pong_data.get("type") == "pong":
                    print("✅ Pong received - connection is healthy")
                else:
                    print(f"ℹ️  Received: {pong_data}")
            except asyncio.TimeoutError:
                print("⚠️  No pong received")
            
    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ WebSocket connection closed: {e}")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")

async def test_database_retry():
    """Test database retry logic"""
    print("🧪 Testing database retry logic...")
    
    try:
        from db.auth_crud import get_user_by_id
        
        # Test with a known user ID (you might need to adjust this)
        user_id = "76e5f280-0ad4-4ecf-a4c1-f66d823e0dff"  # AashiJain's ID from logs
        
        start_time = time.time()
        user = await get_user_by_id(user_id)
        end_time = time.time()
        
        if user:
            print(f"✅ User retrieved successfully in {end_time - start_time:.2f}s")
            print(f"   Username: {user.get('username')}")
        else:
            print("❌ User not found or database error")
            
    except Exception as e:
        print(f"❌ Database test error: {e}")

async def main():
    """Run all tests"""
    print("🔧 Testing WebSocket and Database Connection Fixes")
    print("=" * 50)
    
    # Test authentication
    token = await test_authentication()
    if not token:
        print("❌ Cannot proceed without authentication")
        return
    
    print()
    
    # Test database retry
    await test_database_retry()
    
    print()
    
    # Test WebSocket connection
    await test_websocket_connection(token)
    
    print()
    print("🏁 Test complete!")

if __name__ == "__main__":
    asyncio.run(main())