// flashbots/bundle_send.js

const path = require("path");
require("dotenv").config({ path: path.join(__dirname, "..", ".env") });

const { ethers } = require("ethers");
const { FlashbotsBundleProvider } = require("@flashbots/ethers-provider-bundle");

const PRIVATE_KEY = process.env.PRIVATE_KEY;
const RPC_URL = process.env.RPC_URL;

async function main() {
    const provider = new ethers.providers.JsonRpcProvider(RPC_URL);
    const wallet = new ethers.Wallet(PRIVATE_KEY, provider);

    const flashbotsProvider = await FlashbotsBundleProvider.create(
        provider,
        wallet,
        "https://relay-sepolia.flashbots.net" // Sepolia-Testnet Relay
    );

    const blockNumber = await provider.getBlockNumber();

    const bundle = [
        {
            signer: wallet,
            transaction: {
                to: wallet.address,
                gasLimit: 21000,
                value: ethers.utils.parseEther("0.0001"),
                nonce: await provider.getTransactionCount(wallet.address),
                type: 2,
                maxFeePerGas: ethers.utils.parseUnits("40", "gwei"),
                maxPriorityFeePerGas: ethers.utils.parseUnits("2", "gwei"),
                chainId: 11155111 // Sepolia
            }
        }
    ];

    const simulation = await flashbotsProvider.simulate(bundle, blockNumber + 1);
    if ("error" in simulation) {
        console.warn("❌ Simulation failed:", simulation.error.message);
    } else {
        console.log("✅ Simulation successful:", simulation);
    }
}

main();

