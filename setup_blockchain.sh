#!/bin/bash

# SmartFileTransfer Blockchain Setup Script
# This script automates the entire blockchain setup process

set -e  # Exit on error

echo "🚀 SmartFileTransfer Blockchain Setup"
echo "====================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running from project root
if [ ! -d "blockchain" ] || [ ! -d "backend" ]; then
    echo -e "${RED}❌ Error: Please run this script from the project root directory${NC}"
    exit 1
fi

echo "📦 Step 1: Installing Python dependencies..."
cd backend
if command -v pip3 &> /dev/null; then
    pip3 install -r requirements.txt
elif command -v pip &> /dev/null; then
    pip install -r requirements.txt
else
    echo -e "${RED}❌ Error: pip not found. Please install Python first.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python dependencies installed${NC}"
echo ""

echo "📦 Step 2: Installing Node.js dependencies..."
cd ../blockchain
if command -v npm &> /dev/null; then
    npm install
else
    echo -e "${RED}❌ Error: npm not found. Please install Node.js first.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Node.js dependencies installed${NC}"
echo ""

echo "🔧 Step 3: Checking environment configuration..."
cd ../backend

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️ .env file not found. Creating from template...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}📝 Please edit backend/.env and add your configuration:${NC}"
    echo "   - ALCHEMY_SEPOLIA_RPC_URL"
    echo "   - BLOCKCHAIN_PRIVATE_KEY"
    echo ""
    echo -e "${YELLOW}To continue setup, run this script again after updating .env${NC}"
    exit 0
fi

# Check if required variables are set
source .env

if [ -z "$ALCHEMY_SEPOLIA_RPC_URL" ]; then
    echo -e "${RED}❌ Error: ALCHEMY_SEPOLIA_RPC_URL not set in .env${NC}"
    echo "   Get free RPC URL from: https://www.alchemy.com/"
    exit 1
fi

if [ -z "$BLOCKCHAIN_PRIVATE_KEY" ]; then
    echo -e "${RED}❌ Error: BLOCKCHAIN_PRIVATE_KEY not set in .env${NC}"
    echo "   Export private key from MetaMask"
    exit 1
fi

echo -e "${GREEN}✅ Environment configured${NC}"
echo ""

echo "🔨 Step 4: Compiling smart contracts..."
cd ../blockchain
npm run compile
echo -e "${GREEN}✅ Contracts compiled${NC}"
echo ""

echo "🚀 Step 5: Deploying to Sepolia testnet..."
echo -e "${YELLOW}⚠️ Make sure you have Sepolia ETH in your wallet!${NC}"
echo "   Get free ETH from: https://sepoliafaucet.com/"
echo ""
read -p "Press Enter to continue with deployment..."

npm run deploy:sepolia

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Deployment successful!${NC}"
    echo ""
    
    # Extract contract address from deployment output
    if [ -f "../backend/blockchain_config.json" ]; then
        CONTRACT_ADDRESS=$(grep -o '"contractAddress": "[^"]*"' ../backend/blockchain_config.json | cut -d'"' -f4)
        
        echo "📋 Deployment Summary:"
        echo "   Contract Address: $CONTRACT_ADDRESS"
        echo "   View on Etherscan: https://sepolia.etherscan.io/address/$CONTRACT_ADDRESS"
        echo ""
        
        # Update .env with contract address
        cd ../backend
        if ! grep -q "BLOCKCHAIN_CONTRACT_ADDRESS=" .env; then
            echo "BLOCKCHAIN_CONTRACT_ADDRESS=$CONTRACT_ADDRESS" >> .env
            echo -e "${GREEN}✅ Contract address added to .env${NC}"
        else
            sed -i.bak "s|BLOCKCHAIN_CONTRACT_ADDRESS=.*|BLOCKCHAIN_CONTRACT_ADDRESS=$CONTRACT_ADDRESS|" .env
            echo -e "${GREEN}✅ Contract address updated in .env${NC}"
        fi
    fi
else
    echo -e "${RED}❌ Deployment failed. Check the errors above.${NC}"
    exit 1
fi

echo ""
echo "🎉 Blockchain setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Start the backend server: cd backend && python3 main.py"
echo "2. Open websocket_test.html in browser"
echo "3. Upload a file and see blockchain verification!"
echo ""
echo "🔍 Useful links:"
echo "   - Your contract: https://sepolia.etherscan.io/address/$CONTRACT_ADDRESS"
echo "   - Get more Sepolia ETH: https://sepoliafaucet.com/"
echo "   - Alchemy dashboard: https://dashboard.alchemy.com/"
echo ""
