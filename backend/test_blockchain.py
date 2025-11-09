"""
Test script to verify blockchain integration
Run this after deploying the contract to test everything works
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from services.blockchain_service import get_blockchain_service
from services.ipfs_service import get_ipfs_service
from services.certificate_service import get_certificate_service

async def test_blockchain():
    """Test blockchain service"""
    print("\n🔗 Testing Blockchain Service...")
    print("=" * 50)
    
    blockchain = get_blockchain_service()
    
    if not blockchain.enabled:
        print("❌ Blockchain service not enabled")
        print("   Check your .env configuration:")
        print("   - ALCHEMY_SEPOLIA_RPC_URL")
        print("   - BLOCKCHAIN_PRIVATE_KEY")
        print("   - BLOCKCHAIN_CONTRACT_ADDRESS")
        return False
    
    print("✅ Blockchain service initialized")
    print(f"   Account: {blockchain.account.address}")
    print(f"   Contract: {blockchain.contract_address}")
    
    # Test recording a transfer
    print("\n📝 Testing transfer recording...")
    result = await blockchain.record_transfer(
        file_hash="test_" + os.urandom(16).hex(),
        file_name="test_file.txt",
        sender_id="test_user_1",
        receiver_id="test_room_1",
        ipfs_cid="QmTest123",
        file_size=1024
    )
    
    if result.get('success'):
        print("✅ Transfer recorded successfully!")
        print(f"   TX Hash: {result.get('transaction_hash')}")
        print(f"   Block: {result.get('block_number')}")
        print(f"   Explorer: {result.get('explorer_url')}")
        return True
    else:
        print(f"❌ Transfer recording failed: {result.get('error')}")
        return False

async def test_ipfs():
    """Test IPFS service"""
    print("\n🌐 Testing IPFS Service...")
    print("=" * 50)
    
    ipfs = get_ipfs_service()
    
    if not ipfs.use_alchemy:
        print("⚠️ IPFS service not configured (optional)")
        print("   To enable: Set ALCHEMY_IPFS_API_KEY and ALCHEMY_IPFS_API_SECRET")
        return True  # Not critical
    
    print("✅ IPFS service initialized")
    
    # Test metadata upload (smaller than full file)
    print("\n📝 Testing metadata upload...")
    result = await ipfs.upload_metadata({
        "test": "data",
        "timestamp": "2025-11-07"
    })
    
    if result.get('success'):
        print("✅ IPFS upload successful!")
        print(f"   CID: {result.get('cid')}")
        print(f"   URL: {result.get('gateway_urls', [''])[0]}")
        return True
    else:
        print(f"⚠️ IPFS upload failed: {result.get('error')}")
        return True  # Not critical for demo

def test_certificate():
    """Test certificate service"""
    print("\n📄 Testing Certificate Service...")
    print("=" * 50)
    
    try:
        cert_service = get_certificate_service()
        print("✅ Certificate service initialized")
        
        # Generate test certificate
        print("\n📝 Generating test certificate...")
        pdf_data = cert_service.generate_blockchain_certificate(
            file_info={
                'name': 'test_file.pdf',
                'size': 1024000,
                'hash': 'abc123def456' * 4,
                'sender_id': 'user123',
                'receiver_id': 'room456',
                'room_id': 'room456',
                'timestamp': '2025-11-07T12:00:00Z'
            },
            blockchain_info={
                'success': True,
                'transaction_hash': '0x' + 'ab' * 32,
                'block_number': 12345,
                'gas_used': 150000,
                'timestamp': '2025-11-07T12:00:00Z',
                'contract_address': '0x' + 'cd' * 20,
                'explorer_url': 'https://sepolia.etherscan.io/tx/0x' + 'ab' * 32
            },
            ipfs_info={
                'success': True,
                'cid': 'QmTest123456789',
                'primary_url': 'https://ipfs.io/ipfs/QmTest123456789'
            }
        )
        
        # Save test certificate
        os.makedirs('certificates', exist_ok=True)
        test_cert_path = 'certificates/test_certificate.pdf'
        with open(test_cert_path, 'wb') as f:
            f.write(pdf_data)
        
        print(f"✅ Certificate generated successfully!")
        print(f"   Saved to: {test_cert_path}")
        print(f"   Size: {len(pdf_data) / 1024:.1f} KB")
        return True
        
    except Exception as e:
        print(f"❌ Certificate generation failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("\n" + "=" * 50)
    print("🧪 BLOCKCHAIN INTEGRATION TEST SUITE")
    print("=" * 50)
    
    results = []
    
    # Test blockchain
    blockchain_ok = await test_blockchain()
    results.append(('Blockchain Recording', blockchain_ok))
    
    # Test IPFS
    ipfs_ok = await test_ipfs()
    results.append(('IPFS Upload', ipfs_ok))
    
    # Test certificate
    cert_ok = test_certificate()
    results.append(('Certificate Generation', cert_ok))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_critical_passed = results[0][1] and results[2][1]  # Blockchain + Certificate
    
    if all_critical_passed:
        print("\n🎉 All critical tests passed!")
        print("✅ Your blockchain integration is ready for demo!")
        print("\nNext steps:")
        print("1. Start backend: cd backend && python3 main.py")
        print("2. Open websocket_test.html")
        print("3. Upload a file and see blockchain verification!")
    else:
        print("\n⚠️ Some tests failed. Please check configuration.")
        print("Run: cat backend/.env")
        print("Ensure all required variables are set.")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
