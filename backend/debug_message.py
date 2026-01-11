#!/usr/bin/env python3
"""Debug specific message status"""

from supabase import create_client
from config import settings

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

message_id = "22065a41-09b5-405f-a019-fd9e92f0bd25"
user_id = "0c6d7eea-5048-424b-85ce-a6ba3eff048b"  # AashiJain123

print(f"🔍 Checking message {message_id[:8]}...")
print(f"   User: {user_id[:8]}... (AashiJain123)")
print()

# Check if message exists
print("1️⃣ Message details:")
msg_result = supabase.table("messages").select("*").eq("id", message_id).execute()
if msg_result.data:
    msg = msg_result.data[0]
    print(f"   ✅ Message exists")
    print(f"   Room: {msg['room_id']}")
    print(f"   Sender: {msg['sender_id']}")
    print(f"   File: {msg.get('file_name', 'N/A')}")
else:
    print(f"   ❌ Message NOT found!")

print()

# Check message_status for this specific user
print("2️⃣ Message status for user:")
status_result = supabase.table("message_status")\
    .select("*")\
    .eq("message_id", message_id)\
    .eq("user_id", user_id)\
    .execute()

if status_result.data:
    print(f"   ✅ Status exists: {status_result.data[0]['status']}")
else:
    print(f"   ❌ NO status entry for this user!")

print()

# Check ALL message_status entries for this message
print("3️⃣ All status entries for this message:")
all_status = supabase.table("message_status")\
    .select("*")\
    .eq("message_id", message_id)\
    .execute()

if all_status.data:
    print(f"   Found {len(all_status.data)} status entries:")
    for status in all_status.data:
        print(f"   - User: {status['user_id'][:8]}..., Status: {status['status']}")
else:
    print(f"   ❌ NO status entries at all!")

print()

# Check room membership
if msg_result.data:
    room_id = msg_result.data[0]['room_id']
    print(f"4️⃣ Room membership for room {room_id[:8]}...:")
    members_result = supabase.table("chat_room_members")\
        .select("user_id")\
        .eq("room_id", room_id)\
        .execute()
    
    if members_result.data:
        member_ids = [m['user_id'] for m in members_result.data]
        print(f"   Found {len(member_ids)} members:")
        for mid in member_ids:
            is_target = "← TARGET USER" if mid == user_id else ""
            print(f"   - {mid[:8]}... {is_target}")
            
        if user_id in member_ids:
            print(f"\n   ✅ User IS a member of this room")
        else:
            print(f"\n   ❌ User is NOT a member of this room!")
    else:
        print(f"   ❌ NO members found!")

print()
print("=" * 60)

# If status doesn't exist, create it
if not status_result.data and msg_result.data:
    print("\n🔧 Creating missing status entry...")
    
    sender_id = msg_result.data[0]['sender_id']
    status = "sent" if user_id == sender_id else "delivered"
    
    try:
        insert_result = supabase.table("message_status").insert({
            "message_id": message_id,
            "user_id": user_id,
            "status": status
        }).execute()
        
        if insert_result.data:
            print(f"   ✅ Created status entry: {status}")
        else:
            print(f"   ❌ Failed to create status entry")
    except Exception as e:
        print(f"   ❌ Error creating status: {e}")
