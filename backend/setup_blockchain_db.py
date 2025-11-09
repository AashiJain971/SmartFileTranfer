"""
Quick script to create blockchain_records table in Supabase
Run this once to set up the database schema
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERROR: SUPABASE_URL or SUPABASE_KEY not set in .env")
    exit(1)

print(f"📡 Connecting to Supabase...")
print(f"   URL: {SUPABASE_URL}")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Connected to Supabase!")
    
    # Note: The SQL schema needs to be executed in Supabase SQL Editor
    # This script verifies the table exists and shows sample queries
    
    print("\n" + "="*60)
    print("📋 BLOCKCHAIN RECORDS TABLE SETUP")
    print("="*60)
    
    print("\n🔧 TO CREATE THE TABLE:")
    print("   1. Go to Supabase Dashboard → SQL Editor")
    print("   2. Copy and run the SQL from: backend/blockchain_schema.sql")
    print("")
    print("   OR use Supabase CLI:")
    print("   $ supabase db push")
    
    # Check if table exists by trying to query it
    print("\n🔍 Checking if blockchain_records table exists...")
    
    try:
        result = supabase.table("blockchain_records").select("id").limit(1).execute()
        print("✅ Table 'blockchain_records' already exists!")
        print(f"   Records found: {len(result.data)}")
        
        # Get count
        count_result = supabase.table("blockchain_records").select("id", count='exact').execute()
        print(f"   Total blockchain records: {count_result.count}")
        
        # Show sample record if any exist
        if result.data and len(result.data) > 0:
            sample = supabase.table("blockchain_records").select("*").limit(1).execute()
            if sample.data:
                record = sample.data[0]
                print(f"\n   Sample record:")
                print(f"   - Transaction Hash: {record.get('tx_hash', 'N/A')}")
                print(f"   - Block Number: {record.get('block_number', 'N/A')}")
                print(f"   - File Name: {record.get('file_name', 'N/A')}")
                print(f"   - IPFS CID: {record.get('ipfs_cid', 'N/A')}")
        
    except Exception as e:
        error_msg = str(e).lower()
        if 'does not exist' in error_msg or 'relation' in error_msg or 'table' in error_msg:
            print("❌ Table 'blockchain_records' does NOT exist yet")
            print("\n📝 EXECUTE THIS SQL IN SUPABASE DASHBOARD:")
            print("-" * 60)
            
            with open("blockchain_schema.sql", "r") as f:
                sql_content = f.read()
                print(sql_content)
            
            print("-" * 60)
            print("\n🌐 Or go to:")
            print(f"   {SUPABASE_URL}/project/_/sql")
            
        else:
            print(f"⚠️ Error checking table: {e}")
    
    print("\n" + "="*60)
    print("✅ Setup check complete!")
    print("="*60)
    
except Exception as e:
    print(f"❌ Failed to connect to Supabase: {e}")
    exit(1)
