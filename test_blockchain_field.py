#!/usr/bin/env python3
"""Quick test to check if blockchain_tx_hash is in database"""

import os
import sys
from supabase import create_client

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from config import SUPABASE_URL, SUPABASE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Query a recent message
result = supabase.table("messages")\
    .select("id, file_name, blockchain_tx_hash, ipfs_cid")\
    .eq("message_type", "file")\
    .order("created_at", desc=True)\
    .limit(5)\
    .execute()

print("\n🔍 Recent file messages from database:\n")
for msg in result.data:
    print(f"ID: {msg['id'][:8]}...")
    print(f"File: {msg.get('file_name', 'N/A')}")
    print(f"Blockchain TX: {msg.get('blockchain_tx_hash', 'MISSING')}")
    print(f"IPFS CID: {msg.get('ipfs_cid', 'MISSING')}")
    print("-" * 60)
