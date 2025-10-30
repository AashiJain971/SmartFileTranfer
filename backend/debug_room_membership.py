#!/usr/bin/env python3
"""
Debug script to check room membership and visibility issues
"""
import asyncio
import sys
sys.path.append("/Users/adityajain/SmartFileTransfer/backend")

from db.chat_crud import ChatCRUD
from db.auth_crud import get_user_by_username

async def debug_room_membership():
    """Debug room membership issues"""
    print("🔍 Debugging Room Membership and Visibility Issues")
    print("=" * 60)
    
    # Get test users
    try:
        user1 = await get_user_by_username("AashiJain")
        user2 = await get_user_by_username("AnwesaMondal")
        
        if not user1:
            print("❌ User AashiJain not found")
            return
        if not user2:
            print("❌ User AnwesaMondal not found")
            return
            
        print(f"✅ Found users:")
        print(f"   User 1: {user1['username']} (ID: {user1['id']})")
        print(f"   User 2: {user2['username']} (ID: {user2['id']})")
        
    except Exception as e:
        print(f"❌ Error getting users: {e}")
        return
    
    print()
    
    # Check rooms for each user
    print("📋 Checking rooms for each user...")
    
    try:
        rooms1 = await ChatCRUD.get_user_chat_rooms(user1['id'])
        rooms2 = await ChatCRUD.get_user_chat_rooms(user2['id'])
        
        print(f"🏠 Rooms for {user1['username']}: {len(rooms1)}")
        for i, room in enumerate(rooms1, 1):
            print(f"   {i}. {room['name']} (ID: {room['id'][:8]}...)")
            print(f"      Type: {room['type']}, Members: {len(room.get('members', []))}")
            print(f"      Created by: {room.get('users', {}).get('username', 'Unknown')}")
            
        print(f"🏠 Rooms for {user2['username']}: {len(rooms2)}")
        for i, room in enumerate(rooms2, 1):
            print(f"   {i}. {room['name']} (ID: {room['id'][:8]}...)")
            print(f"      Type: {room['type']}, Members: {len(room.get('members', []))}")
            print(f"      Created by: {room.get('users', {}).get('username', 'Unknown')}")
            
    except Exception as e:
        print(f"❌ Error getting rooms: {e}")
        return
    
    print()
    
    # Check if there are shared rooms
    room_ids1 = {room['id'] for room in rooms1}
    room_ids2 = {room['id'] for room in rooms2}
    shared_rooms = room_ids1.intersection(room_ids2)
    
    print(f"🔗 Shared rooms: {len(shared_rooms)}")
    if shared_rooms:
        for room_id in shared_rooms:
            room1 = next(r for r in rooms1 if r['id'] == room_id)
            print(f"   ✅ {room1['name']} (ID: {room_id[:8]}...)")
    else:
        print("   ❌ No shared rooms found!")
    
    print()
    
    # Check specific room membership manually
    if rooms1:
        test_room = rooms1[0]
        print(f"🔍 Detailed check of room: {test_room['name']}")
        print(f"   Room ID: {test_room['id']}")
        
        try:
            members = await ChatCRUD.get_room_members_detailed(test_room['id'])
            print(f"   Members ({len(members)}):")
            for member in members:
                print(f"     - {member['username']} (Role: {member['role']})")
                
            # Check if user2 is in this room
            is_user2_member = await ChatCRUD.is_user_in_room(user2['id'], test_room['id'])
            print(f"   Is {user2['username']} a member? {is_user2_member}")
            
        except Exception as e:
            print(f"   ❌ Error checking room details: {e}")

async def debug_database_tables():
    """Check database tables directly"""
    print("\n🗃️  Direct Database Table Check")
    print("=" * 40)
    
    try:
        from db.chat_crud import supabase
        
        # Check chat_rooms table
        rooms_result = supabase.table("chat_rooms").select("*").limit(5).execute()
        print(f"📁 chat_rooms table: {len(rooms_result.data)} rooms (showing first 5)")
        for room in rooms_result.data:
            print(f"   {room['name']} (ID: {room['id'][:8]}..., Type: {room['type']})")
        
        print()
        
        # Check chat_room_members table
        members_result = supabase.table("chat_room_members").select("*").limit(10).execute()
        print(f"👥 chat_room_members table: {len(members_result.data)} memberships (showing first 10)")
        for member in members_result.data:
            print(f"   Room: {member['room_id'][:8]}..., User: {member['user_id'][:8]}..., Role: {member['role']}")
            
    except Exception as e:
        print(f"❌ Error checking database tables: {e}")

async def main():
    """Run all debugging checks"""
    await debug_room_membership()
    await debug_database_tables()

if __name__ == "__main__":
    asyncio.run(main())