import asyncio
import aiohttp
import json
from eth_account import Account
from mnemonic import Mnemonic
import bip32utils
import os
import random

API_ETH = "JPPXZJ51MRYMKWBXMPCU266M6DNK8J5MXR"
API_BSC = "QQVKPQFWG7X2NU67549KEEH2RMVJS3KCPW"
file_path = 'data.json'

# Increase concurrency limit!
semaphore = asyncio.Semaphore(20)

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

def btc_address_from_mnemonic(phrase):
    mnemo = Mnemonic('english')
    seed = mnemo.to_seed(phrase)
    root_key = bip32utils.BIP32Key.fromEntropy(seed)
    child_key = root_key.ChildKey(0).ChildKey(0)
    return child_key.Address()

async def check_eth(session, address, phrase):
    async with semaphore:
        url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&sort=asc&apikey={API_ETH}"
        try:
            async with session.get(url) as resp:
                data = await resp.json()
                if data.get("status") == "1" and data["result"]:
                    print(f"[ETH] {address} has txs")
                    append_to_json({"phrase": phrase, "address": address, "chain": "ETH"})
        except Exception as e:
            print(f"[ETH ERROR] {e}")

async def check_bsc(session, address, phrase):
    async with semaphore:
        url = f"https://api.bscscan.com/api?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&sort=asc&apikey={API_BSC}"
        try:
            async with session.get(url) as resp:
                data = await resp.json()
                if data.get("status") == "1" and data["result"]:
                    print(f"[BSC] {address} has txs")
                    append_to_json({"phrase": phrase, "address": address, "chain": "BSC"})
        except Exception as e:
            print(f"[BSC ERROR] {e}")

async def check_btc(session, address, phrase):
    async with semaphore:
        url = f"https://blockstream.info/api/address/{address}/txs"
        try:
            async with session.get(url) as resp:
                data = await resp.json()
                if isinstance(data, list) and data:
                    print(f"[BTC] {address} has txs")
                    append_to_json({"phrase": phrase, "address": address, "chain": "BTC"})
        except Exception as e:
            print(f"[BTC ERROR] {e}")

async def generate_and_check(session, index):
    Account.enable_unaudited_hdwallet_features()
    acct, phrase = Account.create_with_mnemonic(num_words=24)
    eth_bsc_address = acct.address
    btc_address = btc_address_from_mnemonic(phrase)

    print(f"🔍 Checking wallet {index}")
    return await asyncio.gather(
        check_eth(session, eth_bsc_address, phrase),
        check_bsc(session, eth_bsc_address, phrase),
        check_btc(session, btc_address, phrase)
    )

async def main(loop_count=100):
    async with aiohttp.ClientSession() as session:
        tasks = [generate_and_check(session, i+1) for i in range(loop_count)]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main(loop_count=200))  # adjust to 500+ if needed
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user.")

