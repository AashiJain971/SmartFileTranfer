# Blockchain Integration Setup Guide

This guide will help you set up the blockchain audit trail feature for SmartFileTransfer.

## 📋 Prerequisites

- Node.js 18+ (for Hardhat)
- Python 3.10+
- MetaMask wallet
- Alchemy account (free tier)

## 🚀 Step-by-Step Setup

### Step 1: Install Dependencies

```bash
# Backend Python dependencies
cd backend
pip install -r requirements.txt

# Blockchain/Hardhat dependencies  
cd ../blockchain
npm install
```

### Step 2: Get Alchemy RPC URL (FREE)

1. Go to [https://www.alchemy.com/](https://www.alchemy.com/)
2. Sign up for free account
3. Create a new app:
   - **Chain**: Ethereum
   - **Network**: Sepolia (testnet)
4. Copy the HTTPS RPC URL (looks like: `https://eth-sepolia.g.alchemy.com/v2/YOUR_KEY`)

### Step 3: Create MetaMask Wallet

1. Install [MetaMask](https://metamask.io/) browser extension
2. Create new wallet or import existing
3. Switch network to **Sepolia Testnet**:
   - Click network dropdown → "Show test networks" → Select "Sepolia"
4. Export private key:
   - Click account menu → Account details → Export Private Key
   - **⚠️ NEVER SHARE THIS KEY!**

### Step 4: Get Free Sepolia ETH

You need test ETH to deploy contract and record transactions (it's FREE!):

1. Go to [https://sepoliafaucet.com/](https://sepoliafaucet.com/)
2. Enter your MetaMask wallet address
3. Click "Send Me ETH"
4. Wait 1-2 minutes for test ETH to arrive (0.5 ETH)

Alternative faucets:
- [https://faucet.quicknode.com/ethereum/sepolia](https://faucet.quicknode.com/ethereum/sepolia)
- [https://www.infura.io/faucet/sepolia](https://www.infura.io/faucet/sepolia)

### Step 5: Configure Environment Variables

```bash
cd backend
cp .env.example .env
```

Edit `.env` and add:

```bash
# Alchemy RPC URL (from Step 2)
ALCHEMY_SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_ALCHEMY_API_KEY

# MetaMask private key (from Step 3)
BLOCKCHAIN_PRIVATE_KEY=0x1234567890abcdef...  # Your private key

# Optional: Etherscan API key (for contract verification)
ETHERSCAN_API_KEY=your_etherscan_api_key  # Get from etherscan.io
```

### Step 6: Deploy Smart Contract

```bash
cd blockchain

# Compile contract
npm run compile

# Deploy to Sepolia testnet (uses FREE test ETH)
npm run deploy:sepolia
```

**Expected output:**
```
🚀 Starting deployment to Sepolia testnet...
📝 Deploying contracts with account: 0x1234...
💰 Account balance: 0.5 ETH
📦 Deploying FileRegistry contract...
✅ FileRegistry deployed to: 0xABC123...
🔗 View on Etherscan: https://sepolia.etherscan.io/address/0xABC123...
💾 Deployment info saved to: ../backend/blockchain_config.json
💾 Contract ABI saved to: ../backend/blockchain_abi.json
🎉 Deployment completed successfully!
```

### Step 7: Update Environment with Contract Address

The deployment automatically saves the contract address to `blockchain_config.json`, but you should also add it to `.env`:

```bash
# Add this to backend/.env
BLOCKCHAIN_CONTRACT_ADDRESS=0xABC123...  # From deployment output
```

### Step 8: Verify Installation

```bash
cd backend
python3

# In Python shell:
from services.blockchain_service import get_blockchain_service
blockchain = get_blockchain_service()

# Should see:
# ✅ Connected to Ethereum Sepolia (Chain ID: 11155111)
# 📝 Blockchain account: 0x1234...
# 💰 Account balance: 0.499 ETH
# ✅ FileRegistry contract loaded (v1.0.0)
# 📍 Contract address: 0xABC123...
```

### Step 9: Test Blockchain Recording

```bash
# Start backend server
python3 main.py

# Upload a file via websocket_test.html
# Check backend logs for:
# 🔗 Recording transfer on blockchain...
# ✅ Transaction sent: 0xtxhash...
# ✅ Transaction confirmed in block 12345
```

## 📊 Cost Breakdown

| Item | Cost | Notes |
|------|------|-------|
| Alchemy RPC (100k requests/day) | **FREE** | Sepolia testnet |
| MetaMask wallet | **FREE** | No subscription needed |
| Sepolia test ETH | **FREE** | From faucets |
| Smart contract deployment | **FREE** | Uses test ETH |
| Each file transfer recording | **FREE** | Uses test ETH (~0.0001 ETH per tx) |
| **TOTAL** | **$0.00** | Perfect for demo! |

## 🔍 Verify on Etherscan

Every transaction gets a permanent record on Sepolia:

1. Deploy transaction: `https://sepolia.etherscan.io/address/YOUR_CONTRACT`
2. File transfer: `https://sepolia.etherscan.io/tx/TRANSACTION_HASH`

## 🎓 Optional: IPFS Integration (Decentralized Storage)

To also upload files to IPFS:

### Option 1: Alchemy IPFS (Recommended - FREE)

1. In Alchemy dashboard → Create IPFS project
2. Get API Key and Secret
3. Add to `.env`:
   ```bash
   ALCHEMY_IPFS_API_KEY=your_key
   ALCHEMY_IPFS_API_SECRET=your_secret
   ```

### Option 2: Public IPFS Gateway (Simpler)

Files can still be accessed via public gateways without authentication:
- `https://ipfs.io/ipfs/CID`
- `https://cloudflare-ipfs.com/ipfs/CID`

## 🐛 Troubleshooting

### "Account has zero balance"

**Solution**: Get more Sepolia ETH from faucets (Step 4)

### "Cannot connect to Sepolia network"

**Solutions**:
1. Check `ALCHEMY_SEPOLIA_RPC_URL` in `.env`
2. Verify Alchemy app is active on dashboard
3. Check internet connection

### "Contract not found"

**Solutions**:
1. Run deployment: `npm run deploy:sepolia`
2. Copy contract address to `.env`
3. Restart backend server

### "Gas estimation failed"

**Solutions**:
1. Ensure you have enough Sepolia ETH (>0.001 ETH)
2. Check if contract function parameters are valid
3. Try again after a few seconds

## 📱 Frontend Integration

The blockchain verification will automatically appear in the UI:

```html
<!-- Blockchain proof badge -->
<div class="blockchain-proof">
  <span class="badge">🔗 Blockchain Verified</span>
  <a href="https://sepolia.etherscan.io/tx/0x..." target="_blank">
    View on Etherscan
  </a>
  <a href="/certificates/file_id_proof.pdf" download>
    📄 Download Certificate
  </a>
</div>
```

## 🎯 For Production (Moving from Testnet to Mainnet)

When ready to deploy for real:

1. **Option 1: Ethereum Mainnet** (expensive - $2-5 per tx)
   ```bash
   ALCHEMY_MAINNET_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/KEY
   ```

2. **Option 2: Polygon Mainnet** (cheap - $0.01 per tx) ⭐ **RECOMMENDED**
   ```bash
   ALCHEMY_POLYGON_RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/KEY
   ```

3. Update `hardhat.config.js` network to mainnet
4. Get REAL ETH/MATIC (from exchange)
5. Deploy contract to mainnet: `npm run deploy:mainnet`

## 🎉 Success Indicators

You'll know it's working when you see:

1. ✅ Green "Blockchain Verified" badge on uploaded files
2. ✅ "View on Etherscan" link that opens to transaction
3. ✅ PDF certificate with QR code generated
4. ✅ Transaction visible on Sepolia Etherscan
5. ✅ Backend logs showing blockchain recording

## 📚 Next Steps

- Add quantum-resistant encryption (fully free!)
- Customize certificate design
- Add more blockchain analytics
- Implement batch recording for multiple files

## 💡 Pro Tips

1. **Save test ETH**: Each transaction costs ~0.0001 ETH, so 0.5 ETH = 5000 transactions!
2. **Use Polygon**: For production, Polygon is 200x cheaper than Ethereum
3. **Cache certificates**: Generate PDF once, serve from cache
4. **Batch transactions**: Record multiple small files in one transaction to save gas

## 🆘 Need Help?

- Check backend logs: `tail -f backend/logs/blockchain.log`
- View Etherscan: All transactions are public
- Test locally: Run `hardhat node` for local blockchain
- Join Discord: Ask in #blockchain-help channel

---

**You're all set!** 🚀 Your file transfers are now blockchain-verified and legally binding!
