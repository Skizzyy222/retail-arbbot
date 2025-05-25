from web3 import Web3
import time

# === SETTINGS (anpassen!) ===
RPC_URL = "https://sepolia.infura.io/v3/1b75c910618e4487aecb40f0ecd6f208"  # Oder Alchemy etc.
PRIVATE_KEY = "0x346e8343266da8aa42c2200dd5771d0f69cdea5130e294e7343ff4d978f6be00"
TOKEN_ADDRESS = Web3.to_checksum_address("0x442B9Ed15d1Bef29C180e5AF6D94403803609386")
ROUTER_ADDRESS = Web3.to_checksum_address("0x1b02da8cb0d097eb8d57a175b88c7d8b47997506")
MY_ADDRESS = Web3.to_checksum_address("0x05B0C9Ff10E3D599Ca4386Bc316672C2b5643461")
WETH_ADDRESS = "0x4200000000000000000000000000000000000006"
AMOUNT_TOKEN = 500  # Anzahl Token (nicht Wei!)
AMOUNT_ETH = 0.02  # ETH als Float

# === ABIs ===
ERC20_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    }
]
ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "token", "type": "address"},
            {"internalType": "uint256", "name": "amountTokenDesired", "type": "uint256"},
            {"internalType": "uint256", "name": "amountTokenMin", "type": "uint256"},
            {"internalType": "uint256", "name": "amountETHMin", "type": "uint256"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "addLiquidityETH",
        "outputs": [
            {"internalType": "uint256", "name": "amountToken", "type": "uint256"},
            {"internalType": "uint256", "name": "amountETH", "type": "uint256"},
            {"internalType": "uint256", "name": "liquidity", "type": "uint256"}
        ],
        "stateMutability": "payable",
        "type": "function"
    }
]

# === Initialisierung ===
web3 = Web3(Web3.HTTPProvider(RPC_URL))
account = web3.eth.account.from_key(PRIVATE_KEY)

# === Approve Token für Router ===
token = web3.eth.contract(address=Web3.to_checksum_address(TOKEN_ADDRESS), abi=ERC20_ABI)
router = web3.eth.contract(address=Web3.to_checksum_address(ROUTER_ADDRESS), abi=ROUTER_ABI)

AMOUNT_TOKEN_WEI = int(AMOUNT_TOKEN * 1e18)
AMOUNT_ETH_WEI = web3.to_wei(AMOUNT_ETH, "ether")

# 1. Approve Token
nonce = web3.eth.get_transaction_count(account.address)
approve_tx = token.functions.approve(
    ROUTER_ADDRESS,
    AMOUNT_TOKEN_WEI
).build_transaction({
    "from": account.address,
    "nonce": nonce,
    "gas": 100000,
    "gasPrice": web3.eth.gas_price,
    "chainId": web3.eth.chain_id
})
signed_add = web3.eth.account.sign_transaction(approve_tx, private_key=PRIVATE_KEY)
add_tx_hash = web3.eth.send_raw_transaction(signed_add.raw_transaction)
print(f"Approve TX gesendet: {web3.to_hex(add_tx_hash)}")
web3.eth.wait_for_transaction_receipt(add_tx_hash)
print("Approve bestätigt!")

# 2. addLiquidityETH ausführen
nonce += 1
deadline = int(time.time()) + 1200  # 20 Minuten

addliquidity_tx = router.functions.addLiquidityETH(
    TOKEN_ADDRESS,
    AMOUNT_TOKEN_WEI,
    AMOUNT_TOKEN_WEI,
    AMOUNT_ETH_WEI,
    MY_ADDRESS,
    deadline
).build_transaction({
    "from": account.address,
    "value": AMOUNT_ETH_WEI,
    "nonce": nonce,
    "gas": 300000,
    "gasPrice": web3.eth.gas_price,
    "chainId": web3.eth.chain_id
})
signed_add = web3.eth.account.sign_transaction(addliquidity_tx, private_key=PRIVATE_KEY)
add_tx_hash = web3.eth.send_raw_transaction(signed_add.raw_transaction)
print(f"addLiquidity TX gesendet: {web3.to_hex(add_tx_hash)}")
web3.eth.wait_for_transaction_receipt(add_tx_hash)
print("Pool wurde erfolgreich erstellt!")

