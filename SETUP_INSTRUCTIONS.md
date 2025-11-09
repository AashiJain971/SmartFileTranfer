# 🚀 Blockchain Setup - What You Need To Do

## ✅ Already Configured
- ✅ Alchemy Sepolia RPC URL
- ✅ Alchemy API Key
- ✅ Python dependencies (installing...)
- ✅ Node.js dependencies (installed)

## ⚠️ YOU NEED TO DO (5 minutes):

### Step 1: Get MetaMask Private Key (2 min)

1. **Install MetaMask** (if not installed):
   - Go to https://metamask.io/
   - Install browser extension
   - Create new wallet

2. **Switch to Sepolia Network:**
   - Open MetaMask
   - Click network dropdown (top left)
   - Enable "Show test networks"
   - Select **"Sepolia test network"**

3. **Export Private Key:**
   ```
   MetaMask → Click account icon → Account Details → Export Private Key
   → Enter password → Copy key (starts with 0x)
   ```

4. **Add to .env file:**
   ```bash
   # Edit backend/.env
   BLOCKCHAIN_PRIVATE_KEY=0xyour_private_key_paste_here
   ```

### Step 2: Get FREE Sepolia ETH (2 min)

1. **Copy your MetaMask address:**
   - Click address at top of MetaMask (0x1234...5678)
   - It will copy automatically

2. **Get free test ETH:**
   - Go to: https://sepoliafaucet.com/
   - Paste your address
   - Click "Send Me ETH"
   - Wait 1 minute
   - You get 0.5 ETH (FREE!)

3. **Verify:**
   - Check MetaMask → Should show "0.5 ETH" on Sepolia network

### Step 3: Deploy Smart Contract (1 min)

Run this command:

```bash
cd blockchain
npm run deploy:sepolia
```

**Expected output:**
```
✅ FileRegistry deployed to: 0xABC123...
🔗 View on Etherscan: https://sepolia.etherscan.io/address/0xABC123...
💾 Contract address saved to: ../backend/blockchain_config.json
```

The contract address will be **automatically added** to your `.env` file!

### Step 4: Test It! (1 min)

```bash
cd ../backend
python3 test_blockchain.py
```

**Expected output:**
```
✅ Blockchain service initialized
✅ Transfer recorded successfully!
🎉 All tests passed!
```

---

## 🎯 After Setup Complete

Start your backend:
```bash
cd backend
python3 main.py
```

**You'll see:**
```
✅ Connected to Ethereum Sepolia (Chain ID: 11155111)
📝 Blockchain account: 0x1234...
💰 Account balance: 0.5 ETH
✅ FileRegistry contract loaded (v1.0.0)
📍 Contract address: 0xABC123...
```

Then upload a file → See **"🔗 Blockchain Verified"** badge!

---

## 📋 Summary Checklist

- [ ] MetaMask installed
- [ ] MetaMask switched to Sepolia network
- [ ] Private key exported and added to `.env`
- [ ] Sepolia ETH received (0.5 ETH)
- [ ] Dependencies installed (npm install)
- [ ] Smart contract deployed (npm run deploy:sepolia)
- [ ] Test passed (python3 test_blockchain.py)
- [ ] Backend started (python3 main.py)
- [ ] File uploaded → Blockchain verified!

---

## ❓ Troubleshooting

### "Account has zero balance"
→ Get more ETH from: https://sepoliafaucet.com/

### "Cannot connect to Sepolia"
→ Check `.env` has: `ALCHEMY_SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/bkqXxbUL4ebssbCs7TxP2`

### "Private key invalid"
→ Make sure it starts with `0x` and is 66 characters long

### "Contract not deployed"
→ Run: `cd blockchain && npm run deploy:sepolia`

---

## 💰 Cost

- Alchemy RPC: **FREE** (100k requests/day)
- Sepolia ETH: **FREE** (from faucets)
- Smart Contract Deploy: **FREE** (uses test ETH)
- Each File Transfer: **FREE** (uses test ETH)

**Total Cost: $0.00** 💚

---

## 🎉 What You Get

Every uploaded file will have:
- 🔗 Permanent blockchain record
- 📄 PDF proof certificate
- ✅ Public verification on Etherscan
- 🌐 Optional IPFS decentralized storage

**This is enterprise-grade blockchain verification for FREE!**

---

**Time to complete**: 5-10 minutes
**Difficulty**: Easy (just follow steps)
**Support**: Check BLOCKCHAIN_SETUP.md for detailed guide
