require("@nomicfoundation/hardhat-toolbox");

module.exports = {
  solidity: "0.8.20",
  networks: {
    sepolia: {
      url: "https://mainnet.infura.io/v3/1b75c910618e4487aecb40f0ecd6f208",
      accounts: ["346e8343266da8aa42c2200dd5771d0f69cdea5130e294e7343ff4d978f6be00"]
    }
  }
};
