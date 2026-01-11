#!/usr/bin/env python3
"""
Emergency Migration: Backfill message_status for old messages
This creates message_status entries for all messages that don't have them.
"""

import asyncio
from supabase import create_client
from config import settings
from datetime import datetime

# Initialize Supabase client
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

async def backfill_message_status():
    """Create message_status entries for all messages without them"""
    
    print("🔧 Starting message_status backfill migration...")
    print("=" * 60)
    
    # Step 1: Get all messages
    print("\n📋 Step 1: Fetching all messages...")
    messages_result = supabase.table("messages").select("id, room_id, sender_id").execute()
    all_messages = messages_result.data
    print(f"   Found {len(all_messages)} total messages")
    
    # Step 2: Get all existing message_status entries
    print("\n📋 Step 2: Fetching existing message_status entries...")
    status_result = supabase.table("message_status").select("message_id, user_id").execute()
    existing_status = {(s["message_id"], s["user_id"]) for s in status_result.data}
    print(f"   Found {len(existing_status)} existing status entries")
    
    # Step 3: Get all room memberships
    print("\n📋 Step 3: Fetching room memberships...")
    members_result = supabase.table("chat_room_members").select("room_id, user_id").execute()
    room_members = {}
    for member in members_result.data:
        room_id = member["room_id"]
        if room_id not in room_members:
            room_members[room_id] = []
        room_members[room_id].append(member["user_id"])
    print(f"   Found {len(room_members)} rooms with members")
    
    # Step 4: Create missing message_status entries
    print("\n📋 Step 4: Creating missing message_status entries...")
    missing_entries = []
    skipped_no_room = 0
    
    for msg in all_messages:
        message_id = msg["id"]
        sender_id = msg["sender_id"]
        room_id = msg["room_id"]
        
        # Get all members of this room
        members = room_members.get(room_id, [])
        if not members:
            skipped_no_room += 1
            continue
        
        # Check each member
        for member_id in members:
            # Skip if status already exists
            if (message_id, member_id) in existing_status:
                continue
            
            # Determine status
            if member_id == sender_id:
                status = "sent"
            else:
                status = "delivered"
            
            missing_entries.append({
                "message_id": message_id,
                "user_id": member_id,
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    print(f"   ✅ Found {len(missing_entries)} missing status entries to create")
    print(f"   ⚠️  Skipped {skipped_no_room} messages with no room members")
    
    # Step 5: Batch insert missing entries
    if missing_entries:
        print(f"\n📋 Step 5: Inserting {len(missing_entries)} entries in batches...")
        
        # Insert in batches of 1000 to avoid timeout
        batch_size = 1000
        total_inserted = 0
        
        for i in range(0, len(missing_entries), batch_size):
            batch = missing_entries[i:i+batch_size]
            try:
                supabase.table("message_status").insert(batch).execute()
                total_inserted += len(batch)
                print(f"   ✅ Inserted batch {i//batch_size + 1}: {len(batch)} entries (total: {total_inserted})")
            except Exception as e:
                print(f"   ❌ Failed to insert batch {i//batch_size + 1}: {e}")
                # Try one by one for this batch
                for entry in batch:
                    try:
                        supabase.table("message_status").insert(entry).execute()
                        total_inserted += 1
                    except Exception as e2:
                        print(f"   ❌ Failed to insert individual entry: {e2}")
        
        print(f"\n✅ Migration complete! Inserted {total_inserted} new message_status entries")
    else:
        print("\n✅ No missing entries found - all messages already have status!")
    
    print("=" * 60)
    print("🎉 Message status backfill complete!")
    
    # Verify the problematic message
    print("\n🔍 Verifying message 22065a41...")
    verify_result = supabase.table("message_status")\
        .select("*")\
        .eq("message_id", "22065a41-09b5-405f-a019-fd9e92f0bd25")\
        .execute()
    
    if verify_result.data:
        print(f"   ✅ Found {len(verify_result.data)} status entries for message 22065a41:")
        for status in verify_result.data:
            print(f"      - User: {status['user_id'][:8]}..., Status: {status['status']}")
    else:
        print("   ⚠️  No status entries found for message 22065a41")

if __name__ == "__main__":
    asyncio.run(backfill_message_status())
