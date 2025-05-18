const { ethers } = require("hardhat");

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log("Deploying contracts with:", deployer.address);

  const ERC20 = await ethers.getContractFactory("ERC20Mock");

  const weth = await ERC20.deploy("Wrapped Ether", "WETH", 1000000);
  await weth.deployed();
  console.log("WETH deployed to:", weth.address);

  const usdc = await ERC20.deploy("USD Coin", "USDC", 1000000);
  await usdc.deployed();
  console.log("USDC deployed to:", usdc.address);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
