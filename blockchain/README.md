# Blockchain Smart Contracts

This directory contains Ethereum smart contracts for the SmartFileTransfer blockchain audit trail.

## 📁 Directory Structure

```
blockchain/
├── contracts/           # Solidity smart contracts
│   └── FileRegistry.sol # Main contract for recording transfers
├── scripts/            # Deployment and utility scripts
│   └── deploy.js       # Deployment script for Sepolia testnet
├── test/              # Contract tests (optional)
├── hardhat.config.js  # Hardhat configuration
├── package.json       # Node.js dependencies
└── README.md         # This file
```

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Compile contracts
npm run compile

# Deploy to Sepolia testnet
npm run deploy:sepolia

# Run local blockchain node (for testing)
npm run node
```

## 📋 Contract Overview

### FileRegistry.sol

The main smart contract that records file transfers on the blockchain.

**Key Functions:**

- `recordTransfer()` - Record a new file transfer
- `getTransfer()` - Get transfer details by file hash
- `transferExists()` - Check if transfer exists
- `getTotalTransfers()` - Get total number of transfers
- `getUserTransfers()` - Get transfers for a specific user
- `verifyTransfer()` - Emit verification event

**Events:**

- `TransferRecorded` - Emitted when new transfer is recorded
- `TransferVerified` - Emitted when transfer is verified

## 🔧 Configuration

Edit `hardhat.config.js` to configure networks:

```javascript
networks: {
  sepolia: {
    url: process.env.ALCHEMY_SEPOLIA_RPC_URL,
    accounts: [process.env.BLOCKCHAIN_PRIVATE_KEY],
    chainId: 11155111
  }
}
```

## 📊 Deployment Info

After deployment, the following files are automatically created in `backend/`:

- `blockchain_config.json` - Deployment details (address, block, etc.)
- `blockchain_abi.json` - Contract ABI for Python integration

## 🧪 Testing

```bash
# Run contract tests
npm test

# Run with gas reporting
REPORT_GAS=true npm test
```

## 🔍 Verify Contract on Etherscan

```bash
npx hardhat verify --network sepolia DEPLOYED_CONTRACT_ADDRESS
```

## 📱 Gas Costs (Sepolia Testnet)

| Operation | Gas Used | Cost (ETH) |
|-----------|----------|------------|
| Contract deployment | ~1,200,000 | FREE (testnet) |
| Record transfer | ~150,000 | FREE (testnet) |
| Get transfer | 0 (read-only) | FREE |

## 🌐 Supported Networks

### Testnets (FREE)
- ✅ Sepolia (Ethereum)
- ✅ Mumbai (Polygon)
- ✅ Goerli (deprecated)

### Mainnets (PAID)
- 💰 Ethereum Mainnet (~$2-5 per tx)
- 💰 Polygon Mainnet (~$0.01 per tx) ⭐ **RECOMMENDED**
- 💰 Arbitrum (~$0.10 per tx)
- 💰 Optimism (~$0.10 per tx)

## 📚 Additional Resources

- [Hardhat Documentation](https://hardhat.org/docs)
- [Ethereum Sepolia Testnet](https://sepolia.etherscan.io/)
- [OpenZeppelin Contracts](https://docs.openzeppelin.com/contracts)
- [Solidity Documentation](https://docs.soliditylang.org/)

## 🔒 Security

- Never commit `.env` file or private keys
- Always test on testnet before mainnet
- Use OpenZeppelin libraries for security
- Get contract audited before mainnet deployment

## 📄 License

MIT License - See LICENSE file for details
