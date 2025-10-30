#!/usr/bin/env python3
"""
Test message storage and retrieval directly
"""
import asyncio
import sys
sys.path.append("/Users/adityajain/SmartFileTransfer/backend")

from db.chat_crud import ChatCRUD

async def test_message_storage():
    """Test message storage and retrieval"""
    print("🧪 Testing Message Storage and Retrieval")
    print("=" * 50)
    
    # Use a known room ID from our tests
    room_id = "7fb5de8e-c262-4273-bcab-be6404650fb4"  # Latest created room
    
    try:
        messages = await ChatCRUD.get_room_messages(room_id)
        print(f"📨 Retrieved {len(messages)} messages")
        
        for i, msg in enumerate(messages):
            print(f"\nMessage {i + 1}:")
            print(f"  ID: {msg.get('id', 'N/A')}")
            print(f"  Content: {msg.get('content', 'N/A')}")
            print(f"  Sender ID: {msg.get('sender_id', 'N/A')}")
            print(f"  Sender Username: {msg.get('sender_username', 'N/A')}")
            print(f"  Created At: {msg.get('created_at', 'N/A')}")
            
            # Check raw sender data if available
            if 'sender' in msg:
                print(f"  Raw Sender Data: {msg['sender']}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_message_storage())