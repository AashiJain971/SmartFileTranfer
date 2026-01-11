#!/usr/bin/env python3
"""Check if messages have blockchain_tx_hash in database"""
import os
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), 'backend', '.env')
load_dotenv(env_path)

# Create Supabase client directly
from supabase import create_client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Get recent file messages
result = supabase.table("messages")\
    .select("id, file_name, blockchain_tx_hash, ipfs_cid, created_at")\
    .eq("message_type", "file")\
    .order("created_at", desc=True)\
    .limit(5)\
    .execute()

print("\n🔍 Recent 5 file messages from database:\n")
for msg in result.data:
    msg_id = msg['id'][:8]
    fname = (msg.get('file_name') or 'N/A')[:30]
    btx = msg.get('blockchain_tx_hash')
    ipfs = msg.get('ipfs_cid')
    
    print(f"ID: {msg_id}... | File: {fname}")
    if btx:
        print(f"  ✅ Blockchain TX: {btx[:20]}...")
    else:
        print(f"  ❌ Blockchain TX: NULL")
    
    if ipfs:
        print(f"  ✅ IPFS CID: {ipfs[:20]}...")
    else:
        print(f"  ❌ IPFS CID: NULL")
    print()
