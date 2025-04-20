import asyncio
import aiohttp
import json
from eth_account import Account
from mnemonic import Mnemonic
import os

API_ETH = "YOUR_ETHERSCAN_KEY"
API_BSC = "YOUR_BSCSCAN_KEY"
file_path = "data.json"

semaphore = asyncio.Semaphore(10)  # adjust based on API rate limits

# Save found wallet
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

# ETH checker
async def check_eth(session, address):
    async with semaphore:
        url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&sort=asc&apikey={API_ETH}"
        try:
            async with session.get(url, timeout=10) as resp:
                data = await resp.json()
                return data.get("status") == "1" and len(data["result"]) > 0
        except:
            return False

# BSC checker
async def check_bsc(session, address):
    async with semaphore:
        url = f"https://api.bscscan.com/api?module=account&action=txlist&address={address}&sort=asc&apikey={API_BSC}"
        try:
            async with session.get(url, timeout=10) as resp:
                data = await resp.json()
                return data.get("status") == "1" and len(data["result"]) > 0
        except:
            return False

# Check one wallet
async def check_wallet(session, i):
    acct, phrase = Account.create_with_mnemonic(num_words=24)
    address = acct.address
    print(f"🔍 Attempt {i}: {address[:10]}...")

    eth = await check_eth(session, address)
    if eth:
        print(f"🎯 FOUND on ETH: {address}")
        append_to_json({"phrase": phrase, "address": address, "chain": "ETH"})
        return True

    bsc = await check_bsc(session, address)
    if bsc:
        print(f"🎯 FOUND on BSC: {address}")
        append_to_json({"phrase": phrase, "address": address, "chain": "BSC"})
        return True

    return False

# Main loop
async def main():
    Account.enable_unaudited_hdwallet_features()
    async with aiohttp.ClientSession() as session:
        i = 1
        while True:
            # Check 10 wallets in parallel
            tasks = [check_wallet(session, i + j) for j in range(10)]
            results = await asyncio.gather(*tasks)

            if any(results):
                break  # stop if any wallet has transactions

            i += 10

# Run it
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user.")
