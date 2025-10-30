#!/usr/bin/env python3
"""
Comprehensive test for real-time chat system
Tests: Room creation, membership, real-time updates, message broadcasting
"""
import asyncio
import websockets
import requests
import json
import time

async def test_realtime_chat_system():
    """Test complete real-time chat functionality"""
    print("🚀 Testing Complete Real-Time Chat System")
    print("=" * 60)
    
    # Login both users
    login1 = {"email": "aashij971@gmail.com", "password": "AashiJain123@"}
    login2 = {"email": "mondalanwesa0@gmail.com", "password": "AnwesaMondal123@"}
    
    try:
        print("1️⃣ Logging in both users...")
        response1 = requests.post("http://localhost:8000/auth/login", json=login1, timeout=10)
        response2 = requests.post("http://localhost:8000/auth/login", json=login2, timeout=10)
        
        if response1.status_code != 200 or response2.status_code != 200:
            print("❌ Login failed")
            return
        
        token1 = response1.json()["access_token"]
        token2 = response2.json()["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        print("✅ Both users logged in")
        
        # Check existing rooms for both users
        print("\n2️⃣ Checking existing rooms...")
        rooms1 = requests.get("http://localhost:8000/chat/rooms", headers=headers1, timeout=10)
        rooms2 = requests.get("http://localhost:8000/chat/rooms", headers=headers2, timeout=10)
        
        if rooms1.status_code == 200 and rooms2.status_code == 200:
            rooms1_data = rooms1.json().get("rooms", [])
            rooms2_data = rooms2.json().get("rooms", [])
            
            print(f"📊 User1 has {len(rooms1_data)} rooms")
            print(f"📊 User2 has {len(rooms2_data)} rooms")
            
            # Check for shared rooms
            room_ids1 = {r["id"] for r in rooms1_data}
            room_ids2 = {r["id"] for r in rooms2_data}
            shared_rooms = room_ids1.intersection(room_ids2)
            
            print(f"🔗 Shared rooms: {len(shared_rooms)}")
            
            if shared_rooms:
                test_room_id = list(shared_rooms)[0]
                print(f"✅ Using existing shared room: {test_room_id[:8]}...")
            else:
                print("📝 Creating new direct chat...")
                # Create direct chat from User1 to User2
                room_data = {
                    "type": "direct", 
                    "name": None,
                    "members": ["mondalanwesa0@gmail.com"]
                }
                
                create_response = requests.post("http://localhost:8000/chat/rooms", json=room_data, headers=headers1, timeout=10)
                if create_response.status_code == 200:
                    room_info = create_response.json()
                    test_room_id = room_info["id"]
                    print(f"✅ Created room: {room_info.get('name', test_room_id[:8])}")
                    
                    # Wait a moment for room to propagate
                    time.sleep(2)
                    
                    # Check if User2 can see the room now
                    rooms2_after = requests.get("http://localhost:8000/chat/rooms", headers=headers2, timeout=10)
                    if rooms2_after.status_code == 200:
                        rooms2_after_data = rooms2_after.json().get("rooms", [])
                        room_ids2_after = {r["id"] for r in rooms2_after_data}
                        
                        if test_room_id in room_ids2_after:
                            print("✅ User2 can see the new room!")
                        else:
                            print("❌ User2 cannot see the new room")
                            print(f"   User2 rooms after: {[r['name'] for r in rooms2_after_data]}")
                else:
                    print(f"❌ Failed to create room: {create_response.status_code}")
                    return
        
        # Test WebSocket connections to the shared room
        print(f"\n3️⃣ Testing WebSocket connections to room {test_room_id[:8]}...")
        
        async def user1_websocket():
            ws_url = f"ws://localhost:8000/ws/chat/{test_room_id}?token={token1}"
            try:
                async with websockets.connect(ws_url) as ws1:
                    print("✅ User1 connected to room WebSocket")
                    
                    # Wait for connection confirmation
                    msg = await asyncio.wait_for(ws1.recv(), timeout=5)
                    data = json.loads(msg)
                    print(f"📥 User1 received: {data.get('type')}")
                    
                    # Send a test message after 3 seconds
                    await asyncio.sleep(3)
                    test_msg = {
                        "type": "text_message",
                        "content": "Hello from User1! Testing real-time chat."
                    }
                    await ws1.send(json.dumps(test_msg))
                    print("💬 User1 sent test message")
                    
                    # Wait for any responses
                    try:
                        response = await asyncio.wait_for(ws1.recv(), timeout=5)
                        response_data = json.loads(response)
                        print(f"📥 User1 received response: {response_data.get('type')}")
                    except asyncio.TimeoutError:
                        print("⏰ User1 no response received")
                    
                    await asyncio.sleep(10)  # Keep connection alive
                    
            except Exception as e:
                print(f"❌ User1 WebSocket error: {e}")
        
        async def user2_websocket():
            await asyncio.sleep(1)  # Connect slightly after user1
            
            ws_url = f"ws://localhost:8000/ws/chat/{test_room_id}?token={token2}"
            try:
                async with websockets.connect(ws_url) as ws2:
                    print("✅ User2 connected to room WebSocket")
                    
                    # Wait for connection confirmation
                    msg = await asyncio.wait_for(ws2.recv(), timeout=5)
                    data = json.loads(msg)
                    print(f"📥 User2 received: {data.get('type')}")
                    
                    # Listen for messages
                    for i in range(3):
                        try:
                            msg = await asyncio.wait_for(ws2.recv(), timeout=5)
                            data = json.loads(msg)
                            msg_type = data.get('type')
                            print(f"📥 User2 received message: {msg_type}")
                            
                            if msg_type == 'new_message':
                                content = data.get('message', {}).get('content', 'No content')
                                sender = data.get('message', {}).get('sender_username', 'Unknown')
                                print(f"   💬 Message from {sender}: {content}")
                                
                        except asyncio.TimeoutError:
                            print(f"⏰ User2 timeout {i+1}")
                            
            except Exception as e:
                print(f"❌ User2 WebSocket error: {e}")
        
        # Run both WebSocket connections concurrently
        await asyncio.gather(user1_websocket(), user2_websocket())
        
        print("\n🏁 Real-time chat system test completed!")
        
    except Exception as e:
        print(f"❌ Test error: {e}")

if __name__ == "__main__":
    asyncio.run(test_realtime_chat_system())