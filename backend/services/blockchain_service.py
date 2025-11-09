"""
Mock Blockchain Service for File Transfer Audit Trail
Simulates Ethereum blockchain behavior without requiring real ETH
Perfect for demos and development - generates realistic transaction records
"""

from typing import Optional, Dict, Any
from datetime import datetime
import hashlib
import secrets
import os
from supabase import create_client, Client

class BlockchainService:
    """Mock blockchain service - simulates Ethereum without requiring ETH"""
    
    def __init__(self):
        """Initialize mock blockchain service"""
        # Supabase for storing "blockchain" records
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            print("⚠️ BLOCKCHAIN WARNING: Supabase not configured")
            self.enabled = False
            return
        
        try:
            self.supabase = create_client(supabase_url, supabase_key)
            self.enabled = True
            self.network = "Simulated Ethereum Sepolia"
            self.chain_id = 11155111  # Real Sepolia chain ID
            
            # Simulate starting block number
            self.current_block = 7234567  # Realistic Sepolia block number
            
            print(f"✅ Mock Blockchain Service initialized")
            print(f"📍 Network: {self.network}")
            print(f"🔢 Current block: #{self.current_block}")
            print(f"💡 Mode: Simulated (no ETH required)")
            
        except Exception as e:
            print(f"❌ BLOCKCHAIN INITIALIZATION ERROR: {e}")
            self.enabled = False
    
    def _generate_transaction_hash(self, file_hash: str, timestamp: str) -> str:
        """Generate realistic-looking transaction hash"""
        # Combine inputs for uniqueness
        data = f"{file_hash}{timestamp}{secrets.token_hex(8)}"
        tx_hash = hashlib.sha256(data.encode()).hexdigest()
        return f"0x{tx_hash}"
    
    def _generate_block_number(self) -> int:
        """Generate realistic block number"""
        # Increment from current block
        self.current_block += secrets.randbelow(3) + 1  # +1 to +3 blocks
        return self.current_block
    
    async def record_transfer(
        self,
        file_hash: str,
        file_name: str,
        sender_id: str,
        receiver_id: str,
        ipfs_cid: str,
        file_size: int
    ) -> Dict[str, Any]:
        """
        Record file transfer on mock blockchain
        
        Args:
            file_hash: SHA-256 hash of the file
            file_name: Original filename
            sender_id: User ID of sender
            receiver_id: User ID of receiver (or room ID)
            ipfs_cid: IPFS Content Identifier (REAL!)
            file_size: File size in bytes
            
        Returns:
            dict: Transaction details with realistic format
        """
        if not self.enabled:
            return {
                'success': False,
                'error': 'Blockchain service not enabled',
                'reason': 'Supabase not configured'
            }
        
        try:
            print(f"\n🔗 Recording transfer on mock blockchain...")
            print(f"   File: {file_name}")
            print(f"   Hash: {file_hash[:16]}...")
            print(f"   IPFS: {ipfs_cid}")
            
            # Generate realistic transaction details
            timestamp = datetime.now().isoformat()
            tx_hash = self._generate_transaction_hash(file_hash, timestamp)
            block_number = self._generate_block_number()
            gas_used = secrets.randbelow(50000) + 120000  # Realistic gas: 120k-170k
            
            # Check if transfer already exists
            try:
                existing = self.supabase.table("blockchain_records")\
                    .select("*")\
                    .eq("file_hash", file_hash)\
                    .execute()
                
                if existing.data and len(existing.data) > 0:
                    print("⚠️ Transfer already recorded on blockchain")
                    record = existing.data[0]
                    return {
                        'success': True,
                        'already_exists': True,
                        'transaction_hash': record['tx_hash'],
                        'block_number': record['block_number'],
                        'existing_timestamp': record['timestamp']
                    }
            except Exception as check_error:
                print(f"   Could not check existence: {check_error}")
            
            # Store in database (our "blockchain")
            record = {
                'tx_hash': tx_hash,
                'file_hash': file_hash,
                'file_name': file_name,
                'sender_id': sender_id,
                'receiver_id': receiver_id,
                'ipfs_cid': ipfs_cid,
                'file_size': file_size,
                'block_number': block_number,
                'gas_used': gas_used,
                'network': self.network,
                'chain_id': self.chain_id,
                'timestamp': timestamp
            }
            
            result = self.supabase.table("blockchain_records")\
                .insert(record)\
                .execute()
            
            if not result.data:
                raise Exception("Failed to insert blockchain record")
            
            print(f"   ✅ Transaction confirmed: {tx_hash[:16]}...")
            print(f"   📦 Block number: #{block_number}")
            print(f"   ⛽ Gas used: {gas_used}")
            
            # Generate explorer URL (to your own explorer page)
            explorer_url = f"/blockchain/explorer/tx/{tx_hash}"
            
            return {
                'success': True,
                'transaction_hash': tx_hash,
                'block_number': block_number,
                'gas_used': gas_used,
                'network': self.network,
                'chain_id': self.chain_id,
                'contract_address': "0x" + hashlib.sha256(b"SmartFileTransfer").hexdigest()[:40],
                'explorer_url': explorer_url,
                'timestamp': timestamp,
                'ipfs_cid': ipfs_cid,  # Include REAL IPFS CID in response
                'mode': 'simulated'
            }
                
        except Exception as e:
            print(f"   ❌ Blockchain recording failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    async def get_transfer(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Get transfer details from blockchain"""
        if not self.enabled:
            return None
        
        try:
            result = self.supabase.table("blockchain_records")\
                .select("*")\
                .eq("file_hash", file_hash)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
            
        except Exception as e:
            print(f"❌ Failed to get transfer: {e}")
            return None
    
    async def get_transaction(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Get transaction by hash"""
        if not self.enabled:
            return None
        
        try:
            result = self.supabase.table("blockchain_records")\
                .select("*")\
                .eq("tx_hash", tx_hash)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
            
        except Exception as e:
            print(f"❌ Failed to get transaction: {e}")
            return None
    
    async def verify_transfer(self, file_hash: str) -> bool:
        """Check if transfer exists on blockchain"""
        if not self.enabled:
            return False
        
        try:
            result = self.supabase.table("blockchain_records")\
                .select("id")\
                .eq("file_hash", file_hash)\
                .execute()
            
            return result.data and len(result.data) > 0
            
        except:
            return False
    
    def get_explorer_url(self, tx_hash: str) -> str:
        """Get explorer URL for transaction"""
        return f"/blockchain/explorer/tx/{tx_hash}"
    
    def get_contract_explorer_url(self) -> str:
        """Get explorer URL for contract"""
        contract_address = "0x" + hashlib.sha256(b"SmartFileTransfer").hexdigest()[:40]
        return f"/blockchain/explorer/address/{contract_address}"
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get blockchain statistics"""
        if not self.enabled:
            return {
                'total_transfers': 0,
                'current_block': 0
            }
        
        try:
            result = self.supabase.table("blockchain_records")\
                .select("id", count='exact')\
                .execute()
            
            return {
                'total_transfers': result.count or 0,
                'current_block': self.current_block,
                'network': self.network,
                'chain_id': self.chain_id
            }
        except:
            return {
                'total_transfers': 0,
                'current_block': self.current_block
            }


# Singleton instance
_blockchain_service = None

def get_blockchain_service() -> BlockchainService:
    """Get singleton blockchain service instance"""
    global _blockchain_service
    if _blockchain_service is None:
        _blockchain_service = BlockchainService()
    return _blockchain_service
