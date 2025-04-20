import asyncio
import aiohttp
import json
from eth_account import Account
from mnemonic import Mnemonic
import bip32utils
import os

# File to store results
file_path = 'data.json'

# Your API keys
API_ETH = "JPPXZJ51MRYMKWBXMPCU266M6DNK8J5MXR"
API_BSC = "QQVKPQFWG7X2NU67549KEEH2RMVJS3KCPW"

# Max concurrent requests to avoid rate-limits
semaphore = asyncio.Semaphore(3)

# Append new data safely
def append_to_json(data):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                existing = json.load(f)
        except json.JSONDecodeError:
            existing = []
    else:
        existing = []

    existing.append(data)
    with open(file_path, 'w') as f:
        json.dump(existing, f, indent=4)

# Generate a BTC address from mnemonic
def btc_address_from_mnemonic(phrase):
    mnemo = Mnemonic('english')
    seed = mnemo.to_seed(phrase)
    root_key = bip32utils.BIP32Key.fromEntropy(seed)
    child_key = root_key.ChildKey(0).ChildKey(0)
    return child_key.Address()

# ETH transaction checker
async def check_eth(session, address, phrase):
    async with semaphore:
        url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&sort=asc&apikey={API_ETH}"
        try:
            async with session.get(url) as resp:
                data = await resp.json()
                if data.get("status") == "1" and len(data["result"]) > 0:
                    print(f"[ETH] {address} has {len(data['result'])} txs")
                    append_to_json({"phrase": phrase, "address": address, "chain": "ETH"})
        except Exception as e:
            print(f"[ETH ERROR] {e}")

# BSC transaction checker
async def check_bsc(session, address, phrase):
    async with semaphore:
        url = f"https://api.bscscan.com/api?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&sort=asc&apikey={API_BSC}"
        try:
            async with session.get(url) as resp:
                data = await resp.json()
                if data.get("status") == "1" and len(data["result"]) > 0:
                    print(f"[BSC] {address} has {len(data['result'])} txs")
                    append_to_json({"phrase": phrase, "address": address, "chain": "BSC"})
        except Exception as e:
            print(f"[BSC ERROR] {e}")

# BTC transaction checker
async def check_btc(session, address, phrase):
    async with semaphore:
        url = f"https://blockstream.info/api/address/{address}/txs"
        try:
            async with session.get(url) as resp:
                data = await resp.json()
                if isinstance(data, list) and len(data) > 0:
                    print(f"[BTC] {address} has {len(data)} txs")
                    append_to_json({"phrase": phrase, "address": address, "chain": "BTC"})
        except Exception as e:
            print(f"[BTC ERROR] {e}")

# Main loop
async def main(loop_count=100):
    Account.enable_unaudited_hdwallet_features()
    async with aiohttp.ClientSession() as session:
        tasks = []

        for i in range(loop_count):
            print(f"\n🔁 Loop {i+1}/{loop_count}")
            acct, phrase = Account.create_with_mnemonic(num_words=24)
            eth_bsc_address = acct.address
            btc_address = btc_address_from_mnemonic(phrase)

            tasks.extend([
                check_eth(session, eth_bsc_address, phrase),
                check_bsc(session, eth_bsc_address, phrase),
                check_btc(session, btc_address, phrase)
            ])

            await asyncio.sleep(0.3)  # prevent API bans

        await asyncio.gather(*tasks)

# Run the script
if __name__ == "__main__":
    try:
        asyncio.run(main(loop_count=100))
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user.")
