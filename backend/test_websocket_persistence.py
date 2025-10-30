#!/usr/bin/env python3
"""
Test WebSocket connection persistence and message broadcasting
"""
import asyncio
import websockets
import json
import sys
sys.path.append("/Users/adityajain/SmartFileTransfer/backend")

from routers.websocket import chat_manager

async def test_websocket_persistence():
    """Test if WebSocket connections are staying active"""
    print("🧪 Testing WebSocket Connection Persistence")
    print("=" * 50)
    
    # Login to get tokens
    import requests
    
    # Get tokens for both users
    login_data1 = {"email": "aashij971@gmail.com", "password": "AashiJain123@"}
    login_data2 = {"email": "mondalanwesa0@gmail.com", "password": "AnwesaMondal123@"}
    
    try:
        response1 = requests.post("http://localhost:8000/auth/login", json=login_data1, timeout=10)
        response2 = requests.post("http://localhost:8000/auth/login", json=login_data2, timeout=10)
        
        if response1.status_code != 200 or response2.status_code != 200:
            print("❌ Failed to login users")
            return
            
        token1 = response1.json()["access_token"]
        token2 = response2.json()["access_token"]
        
        print("✅ Both users logged in successfully")
        
    except Exception as e:
        print(f"❌ Login error: {e}")
        return
    
    # Test room ID from debug (one of the shared rooms)
    room_id = "547bda7d-56f7-485f-8b26-88e2b14370e6"
    
    print(f"📱 Testing connections to room: {room_id}")
    
    # Check current connection state
    print(f"🔍 Current room connections: {len(chat_manager.room_connections.get(room_id, {}))}")
    print(f"🔍 Total rooms being managed: {len(chat_manager.room_connections)}")
    
    # Try connecting both users simultaneously
    async def connect_user1():
        ws_url1 = f"ws://localhost:8000/ws/chat/{room_id}?token={token1}"
        try:
            async with websockets.connect(ws_url1, ping_interval=20) as ws1:
                print("✅ User1 (AashiJain) connected")
                
                # Wait for connection confirmation
                response = await asyncio.wait_for(ws1.recv(), timeout=5)
                data = json.loads(response)
                print(f"📥 User1 received: {data.get('type', 'unknown')}")
                
                # Keep connection alive for 30 seconds
                for i in range(6):  # 6 * 5 seconds = 30 seconds
                    await asyncio.sleep(5)
                    # Send ping
                    await ws1.send(json.dumps({"type": "ping", "timestamp": "test"}))
                    print(f"🏓 User1 ping {i+1}")
                    
                print("📱 User1 connection test completed")
                
        except Exception as e:
            print(f"❌ User1 connection error: {e}")
    
    async def connect_user2():
        # Wait a bit before connecting user2
        await asyncio.sleep(2)
        
        ws_url2 = f"ws://localhost:8000/ws/chat/{room_id}?token={token2}"
        try:
            async with websockets.connect(ws_url2, ping_interval=20) as ws2:
                print("✅ User2 (AnwesaMondal) connected")
                
                # Wait for connection confirmation
                response = await asyncio.wait_for(ws2.recv(), timeout=5)
                data = json.loads(response)
                print(f"📥 User2 received: {data.get('type', 'unknown')}")
                
                # Send a test message after 10 seconds
                await asyncio.sleep(10)
                test_message = {
                    "type": "text_message",
                    "content": "Test message from User2 for broadcasting test",
                    "timestamp": "test"
                }
                await ws2.send(json.dumps(test_message))
                print("💬 User2 sent test message")
                
                # Keep connection alive
                for i in range(4):  # 4 * 5 seconds = 20 seconds
                    await asyncio.sleep(5)
                    await ws2.send(json.dumps({"type": "ping", "timestamp": "test"}))
                    print(f"🏓 User2 ping {i+1}")
                    
                print("📱 User2 connection test completed")
                
        except Exception as e:
            print(f"❌ User2 connection error: {e}")
    
    # Run both connections concurrently
    await asyncio.gather(connect_user1(), connect_user2())
    
    # Check final connection state
    print(f"\n🔍 Final room connections: {len(chat_manager.room_connections.get(room_id, {}))}")

if __name__ == "__main__":
    asyncio.run(test_websocket_persistence())