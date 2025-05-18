const { ethers } = require("hardhat");

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log("Deploying contracts with:", deployer.address);

  const Token = await ethers.getContractFactory("TestToken");

  const tokens = [
    { name: "Wrapped Ether", symbol: "WETH", supply: 1_000_000 },
    { name: "USD Coin", symbol: "USDC", supply: 1_000_000 },
    { name: "Pepe", symbol: "PEPE", supply: 1_000_000 },
    { name: "Floki", symbol: "FLOKI", supply: 1_000_000 },
    { name: "Shiba Inu", symbol: "SHIB", supply: 1_000_000 },
    { name: "BabyDoge", symbol: "BDOGE", supply: 1_000_000 },
    { name: "Bonk", symbol: "BONK", supply: 1_000_000 },
    { name: "Kishu", symbol: "KISHU", supply: 1_000_000 },
    { name: "Hoppy", symbol: "HOPPY", supply: 1_000_000 },
    { name: "Volt", symbol: "VOLT", supply: 1_000_000 },
    { name: "Snek", symbol: "SNEK", supply: 1_000_000 },
  ];

  for (const t of tokens) {
    const token = await Token.deploy(t.name, t.symbol, t.supply);
    await token.deployed();
    console.log(`${t.symbol} deployed at: ${token.address}`);
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

