#!/usr/bin/env python3
"""
Test WebSocket connection fix
This test verifies that the username variable error is resolved and users can connect to room WebSockets.
"""
import asyncio
import aiohttp
import json
import os
import sys

# Ensure we can import from the backend modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

BASE_URL = "http://localhost:8000"

class WebSocketTester:
    def __init__(self):
        self.session = None
        self.test_users = [
            {"email": "aashij971@gmail.com", "password": "password123", "name": "AashiJain"},
            {"email": "mondalanwesa0@gmail.com", "password": "password123", "name": "AnwesaMondal"}
        ]
        
    async def setup_session(self):
        """Initialize HTTP session"""
        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(limit=100)
        self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        
    async def cleanup_session(self):
        """Cleanup HTTP session"""
        if self.session:
            await self.session.close()
            
    async def login_user(self, email, password):
        """Login user and return token"""
        try:
            login_data = {"email": email, "password": password}
            
            async with self.session.post(f"{BASE_URL}/auth/login", json=login_data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("access_token")
                else:
                    error_text = await response.text()
                    print(f"❌ Login failed for {email}: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            print(f"❌ Login exception for {email}: {e}")
            return None
    
    async def get_user_rooms(self, token):
        """Get user's chat rooms"""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            
            async with self.session.get(f"{BASE_URL}/chat/rooms", headers=headers) as response:
                if response.status == 200:
                    rooms = await response.json()
                    return rooms
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to get rooms: {response.status} - {error_text}")
                    return []
                    
        except Exception as e:
            print(f"❌ Exception getting rooms: {e}")
            return []
    
    async def test_websocket_connection(self, token, room_id, username):
        """Test WebSocket connection to a room"""
        try:
            # Test room-specific WebSocket connection
            ws_url = f"ws://localhost:8000/ws/chat/{room_id}?token={token}"
            print(f"🔗 Testing WebSocket connection for {username} to room {room_id[:8]}...")
            
            async with self.session.ws_connect(ws_url) as ws:
                print(f"✅ WebSocket connected successfully for {username}!")
                
                # Wait for connection message
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        print(f"📨 Received: {data.get('type')} for {username}")
                        
                        if data.get('type') == 'connected':
                            print(f"✅ {username} successfully connected to room {room_id[:8]}!")
                            return True
                            
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        print(f"❌ WebSocket error for {username}: {ws.exception()}")
                        return False
                        
                    # Only wait for first message (connection confirmation)
                    break
                    
        except Exception as e:
            print(f"❌ WebSocket connection failed for {username}: {e}")
            return False
            
        return False
    
    async def run_websocket_test(self):
        """Run comprehensive WebSocket connection test"""
        print("🧪 Testing WebSocket Connection Fix...")
        print("=" * 60)
        
        await self.setup_session()
        
        try:
            # Step 1: Login both users
            print("\n📋 Step 1: Login users...")
            tokens = {}
            
            for user_info in self.test_users:
                token = await self.login_user(user_info["email"], user_info["password"])
                if token:
                    tokens[user_info["name"]] = token
                    print(f"✅ {user_info['name']} logged in successfully")
                else:
                    print(f"❌ {user_info['name']} login failed")
                    return
            
            if len(tokens) != 2:
                print("❌ Failed to login both users")
                return
                
            # Step 2: Get rooms for both users
            print("\n📋 Step 2: Get chat rooms...")
            rooms_by_user = {}
            
            for username, token in tokens.items():
                rooms = await self.get_user_rooms(token)
                rooms_by_user[username] = rooms
                print(f"📂 {username} has {len(rooms)} rooms")
                
            # Step 3: Find a common room
            print("\n📋 Step 3: Find common rooms...")
            common_rooms = []
            
            if rooms_by_user.get("AashiJain") and rooms_by_user.get("AnwesaMondal"):
                aashi_room_ids = {room["id"] for room in rooms_by_user["AashiJain"]}
                anwesa_room_ids = {room["id"] for room in rooms_by_user["AnwesaMondal"]}
                common_room_ids = aashi_room_ids.intersection(anwesa_room_ids)
                
                for room_id in common_room_ids:
                    # Find room details
                    for room in rooms_by_user["AashiJain"]:
                        if room["id"] == room_id:
                            common_rooms.append(room)
                            break
                            
                print(f"🔗 Found {len(common_rooms)} common rooms")
                
                for room in common_rooms[:2]:  # Test first 2 rooms
                    print(f"   - {room['name']} ({room['id'][:8]}...)")
                    
            if not common_rooms:
                print("❌ No common rooms found for WebSocket testing")
                return
                
            # Step 4: Test WebSocket connections
            print("\n📋 Step 4: Test WebSocket connections...")
            test_room = common_rooms[0]
            room_id = test_room["id"]
            
            print(f"🎯 Testing room: {test_room['name']} ({room_id[:8]}...)")
            
            # Test connection for both users
            success_count = 0
            
            for username, token in tokens.items():
                success = await self.test_websocket_connection(token, room_id, username)
                if success:
                    success_count += 1
                    
            # Step 5: Results
            print("\n📋 Step 5: Results...")
            print("=" * 60)
            
            if success_count == 2:
                print("🎉 SUCCESS! Both users can connect to WebSocket rooms!")
                print("✅ The username variable error has been fixed!")
            elif success_count == 1:
                print("⚠️  PARTIAL SUCCESS: One user connected, one failed")
                print("🔧 The fix is working but there may be other issues")
            else:
                print("❌ FAILURE: Neither user could connect to WebSocket")
                print("🐛 The fix may not be complete or there are other issues")
                
        except Exception as e:
            print(f"❌ Test execution error: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            await self.cleanup_session()

async def main():
    """Main test runner"""
    tester = WebSocketTester()
    await tester.run_websocket_test()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()