from web3 import Web3

w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
print("Node verbunden:", w3.is_connected())
