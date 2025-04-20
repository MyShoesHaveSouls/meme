import asyncio
import aiohttp
import json
from eth_account import Account
import os

API_ETH = "JPPXZJ51MRYMKWBXMPCU266M6DNK8J5MXR"
API_BSC = "QQVKPQFWG7X2NU67549KEEH2RMVJS3KCPW"
file_path = 'data.json'

semaphore = asyncio.Semaphore(20)

# Append result to file
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

# Check Ethereum transactions
async def check_eth(session, address):
    url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&sort=asc&apikey={API_ETH}"
    async with semaphore:
        try:
            async with session.get(url) as resp:
                data = await resp.json()
                return data.get("status") == "1" and len(data["result"]) > 0
        except Exception as e:
            print(f"[ETH ERROR] {e}")
            return False

# Check BSC transactions
async def check_bsc(session, address):
    url = f"https://api.bscscan.com/api?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&sort=asc&apikey={API_BSC}"
    async with semaphore:
        try:
            async with session.get(url) as resp:
                data = await resp.json()
                return data.get("status") == "1" and len(data["result"]) > 0
        except Exception as e:
            print(f"[BSC ERROR] {e}")
            return False

# Keep checking until a wallet with txs is found
async def hunt_until_found():
    Account.enable_unaudited_hdwallet_features()
    async with aiohttp.ClientSession() as session:
        attempt = 0
        while True:
            attempt += 1
            acct, phrase = Account.create_with_mnemonic(num_words=24)
            address = acct.address
            print(f"🔍 Attempt {attempt}: {address[:10]}...")

            eth_result, bsc_result = await asyncio.gather(
                check_eth(session, address),
                check_bsc(session, address)
            )

            if eth_result or bsc_result:
                chain = "ETH" if eth_result else "BSC"
                print(f"🎯 FOUND on {chain}: {address}")
                append_to_json({"phrase": phrase, "address": address, "chain": chain})
                break  # Stop after finding one with txs

# Run it
if __name__ == "__main__":
    try:
        asyncio.run(hunt_until_found())
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user.")

        asyncio.run(main(loop_count=200))  # adjust to 500+ if needed
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user.")

