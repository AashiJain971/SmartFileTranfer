const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("🚀 Starting deployment to Sepolia testnet...\n");

  // Get deployer account
  const [deployer] = await hre.ethers.getSigners();
  console.log("📝 Deploying contracts with account:", deployer.address);
  
  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log("💰 Account balance:", hre.ethers.formatEther(balance), "ETH\n");

  if (balance === 0n) {
    console.error("❌ ERROR: Account has zero balance!");
    console.log("💡 Get free Sepolia ETH from:");
    console.log("   - https://sepoliafaucet.com/");
    console.log("   - https://faucet.quicknode.com/ethereum/sepolia");
    console.log("   - https://www.infura.io/faucet/sepolia\n");
    process.exit(1);
  }

  // Deploy FileRegistry contract
  console.log("📦 Deploying FileRegistry contract...");
  const FileRegistry = await hre.ethers.getContractFactory("FileRegistry");
  const fileRegistry = await FileRegistry.deploy();
  
  await fileRegistry.waitForDeployment();
  const contractAddress = await fileRegistry.getAddress();

  console.log("✅ FileRegistry deployed to:", contractAddress);
  console.log("🔗 View on Etherscan:", `https://sepolia.etherscan.io/address/${contractAddress}\n`);

  // Test contract functionality
  console.log("🧪 Testing contract...");
  const version = await fileRegistry.version();
  console.log("   Contract version:", version);
  
  const totalTransfers = await fileRegistry.getTotalTransfers();
  console.log("   Initial transfers:", totalTransfers.toString());
  console.log("✅ Contract is functional!\n");

  // Save deployment info
  const deploymentInfo = {
    network: "sepolia",
    contractName: "FileRegistry",
    contractAddress: contractAddress,
    deployerAddress: deployer.address,
    deploymentTime: new Date().toISOString(),
    blockNumber: await hre.ethers.provider.getBlockNumber(),
    chainId: 11155111,
    etherscanUrl: `https://sepolia.etherscan.io/address/${contractAddress}`,
    version: version
  };

  // Save to backend config
  const backendConfigPath = path.join(__dirname, "../../backend/blockchain_config.json");
  fs.writeFileSync(
    backendConfigPath,
    JSON.stringify(deploymentInfo, null, 2)
  );
  console.log("💾 Deployment info saved to:", backendConfigPath);

  // Save contract ABI
  const artifactPath = path.join(__dirname, "../artifacts/contracts/FileRegistry.sol/FileRegistry.json");
  const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
  const abiPath = path.join(__dirname, "../../backend/blockchain_abi.json");
  fs.writeFileSync(
    abiPath,
    JSON.stringify(artifact.abi, null, 2)
  );
  console.log("💾 Contract ABI saved to:", abiPath);

  console.log("\n🎉 Deployment completed successfully!");
  console.log("\n📋 Next steps:");
  console.log("1. Verify contract on Etherscan:");
  console.log(`   npx hardhat verify --network sepolia ${contractAddress}`);
  console.log("2. Update backend .env with:");
  console.log(`   BLOCKCHAIN_CONTRACT_ADDRESS=${contractAddress}`);
  console.log("3. Restart backend server to use blockchain features\n");

  // Wait for block confirmations
  console.log("⏳ Waiting for 5 block confirmations...");
  const deployTx = fileRegistry.deploymentTransaction();
  if (deployTx) {
    await deployTx.wait(5);
    console.log("✅ Contract confirmed on blockchain!\n");
  }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("❌ Deployment failed:", error);
    process.exit(1);
  });
