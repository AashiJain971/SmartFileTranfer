#!/usr/bin/env python3
"""
Quick script to fix room membership issue
"""

import asyncio
import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.chat_crud import ChatCRUD
from db.auth_crud import get_user_by_email

async def fix_room_membership():
    """Add AnwesaMondal to the existing room"""
    
    room_id = "e224244f-e9f1-46d9-8282-8c27198ac878"
    
    print(f"🔧 Fixing room membership for room: {room_id}")
    
    try:
        # Get AnwesaMondal's user ID - try different email formats
        anwesa_user = await get_user_by_email("mondaianwesa0@gmail.com")
        if not anwesa_user:
            anwesa_user = await get_user_by_email("mondalanwesa0@gmail.com")
        if not anwesa_user:
            # Try to get by username instead
            from db.auth_crud import get_user_by_username
            anwesa_user = await get_user_by_username("AnwesaMondal")
        if not anwesa_user:
            print("❌ AnwesaMondal user not found")
            return
            
        user_id = anwesa_user["id"]
        print(f"✅ Found user AnwesaMondal: {user_id}")
        
        # Check current membership
        is_member = await ChatCRUD.is_user_in_room(user_id, room_id)
        print(f"Current membership status: {is_member}")
        
        if not is_member:
            # Add user to room
            success = await ChatCRUD.add_single_room_member(room_id, user_id, "member")
            if success:
                print("✅ Successfully added AnwesaMondal to the room")
            else:
                print("❌ Failed to add user to room")
        else:
            print("✅ User is already a member of the room")
            
        # Verify membership
        final_check = await ChatCRUD.is_user_in_room(user_id, room_id)
        print(f"Final membership status: {final_check}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(fix_room_membership())