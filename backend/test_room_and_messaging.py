#!/usr/bin/env python3
"""
Test creating room with proper name and sending messages via REST API
"""
import requests
import json

def test_room_creation_and_messaging():
    """Test room creation with proper names and message sending"""
    print("🏠 Testing Room Creation with Proper Names and Messaging")
    print("=" * 60)
    
    # Login
    login_data = {"email": "aashij971@gmail.com", "password": "AashiJain123@"}
    
    try:
        response = requests.post("http://localhost:8000/auth/login", json=login_data, timeout=10)
        if response.status_code != 200:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return
        
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Login successful")
        
    except Exception as e:
        print(f"❌ Login error: {e}")
        return
    
    # Create a new room with proper name
    room_data = {
        "type": "direct",
        "name": "Test Chat Room",
        "members": ["mondalanwesa0@gmail.com"]  # Add other user by email
    }
    
    try:
        response = requests.post("http://localhost:8000/chat/rooms", json=room_data, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"❌ Room creation failed: {response.status_code} - {response.text}")
            return
        
        room = response.json()
        room_id = room["id"]
        print(f"✅ Room created successfully: {room['name']}")
        print(f"   Room ID: {room_id}")
        print(f"   Members: {len(room['members'])}")
        for member in room['members']:
            print(f"     - {member['username']} ({member['role']})")
            
    except Exception as e:
        print(f"❌ Room creation error: {e}")
        return
    
    # Send a test message via REST API
    message_data = {
        "content": "Hello! This is a test message sent via REST API to check WebSocket broadcasting."
    }
    
    try:
        response = requests.post(
            f"http://localhost:8000/chat/rooms/{room_id}/messages", 
            json=message_data, 
            headers=headers, 
            timeout=10
        )
        if response.status_code != 200:
            print(f"❌ Message sending failed: {response.status_code} - {response.text}")
            return
        
        message = response.json()
        print(f"✅ Message sent successfully via REST API:")
        print(f"   Full response: {message}")
        if 'id' in message:
            print(f"   Message ID: {message['id']}")
            print(f"   Content: {message['content']}")
            print(f"   Created at: {message['created_at']}")
        else:
            print(f"   Response format: {list(message.keys()) if isinstance(message, dict) else type(message)}")
        
    except Exception as e:
        print(f"❌ Message sending error: {e}")
        return
    
    # Get room messages to verify storage
    try:
        response = requests.get(f"http://localhost:8000/chat/rooms/{room_id}/messages", headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"❌ Message retrieval failed: {response.status_code} - {response.text}")
            return
        
        messages = response.json()["messages"]
        print(f"✅ Retrieved {len(messages)} messages from room:")
        for msg in messages:
            print(f"   - {msg['sender_username']}: {msg['content']}")
            
    except Exception as e:
        print(f"❌ Message retrieval error: {e}")

if __name__ == "__main__":
    test_room_creation_and_messaging()