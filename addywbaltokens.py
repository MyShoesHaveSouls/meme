import csv
import time
from web3 import Web3
from concurrent.futures import ThreadPoolExecutor, as_completed

# === Public BNB Full Node ===
RPC_URL = "https://bsc-dataseed.binance.org"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

if not w3.is_connected():
    raise ConnectionError("❌ Could not connect to BSC node")

print("✅ Connected to BNB Chain")

# === Token Contracts to Check (Add more if desired) ===
TOKENS = {
    "BNB": None,
    "USDT": "0x55d398326f99059fF775485246999027B3197955",
    "BUSD": "0xe9e7cea3dedca5984780bafc599bd69add087d56",
    "WBNB": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
    "CAKE": "0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82",
    "FLOKI": "0xfb5b838b6cfeedc2873ab27866079ac55363d37e",
    "SHIB": "0x285e61a616e5a43c127670f7aa085e8dcec14754",
    "SAFEMOON": "0x42981d0bfbaf196529376ee702f2a9eb9092fcb5",
}

# === ERC20 ABI ===
ERC20_ABI = [{
    "constant": True,
    "inputs": [{"name": "_owner", "type": "address"}],
    "name": "balanceOf",
    "outputs": [{"name": "balance", "type": "uint256"}],
    "type": "function",
}]

# === Setup CSV Output ===
csv_file = open("holders.csv", "w", newline="")
csv_writer = csv.writer(csv_file)
csv_writer.writerow(["Address"] + list(TOKENS.keys()))

# === Address cache to avoid rechecking ===
seen_addresses = set()

# === Helper: Check token balances for a single address ===
def check_address(addr):
    if addr in seen_addresses:
        return None

    seen_addresses.add(addr)
    results = [addr]

    try:
        # Check native BNB
        bnb = w3.from_wei(w3.eth.get_balance(addr), 'ether')
        results.append(bnb)
    except:
        results.append(0)

    found = bnb > 0.01

    # Check ERC20s
    for token, contract_address in TOKENS.items():
        if token == "BNB":
            continue
        try:
            contract = w3.eth.contract(address=w3.to_checksum_address(contract_address), abi=ERC20_ABI)
            balance = contract.functions.balanceOf(addr).call()
            bal = balance / 1e18
            results.append(bal)
            if bal > 0.01:
                found = True
        except:
            results.append(0)

    if found:
        return results
    return None

# === Monitor Loop ===
print("🚀 Scanning new blocks as they arrive...")

executor = ThreadPoolExecutor(max_workers=10)
current_block = w3.eth.block_number

try:
    while True:
        latest_block = w3.eth.block_number
        if latest_block > current_block:
            for blk_num in range(current_block + 1, latest_block + 1):
                block = w3.eth.get_block(blk_num, full_transactions=True)
                print(f"📦 Scanning block: {blk_num} — {len(block.transactions)} txs")
                addrs = set()

                # Extract all 'from' and 'to' addresses
                for tx in block.transactions:
                    if tx['from']:
                        addrs.add(tx['from'].lower())
                    if tx['to']:
                        addrs.add(tx['to'].lower())

                # Run address checks in threads
                futures = [executor.submit(check_address, addr) for addr in addrs]
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        print(f"💰 Found active wallet: {result[0]}")
                        csv_writer.writerow(result)
                        csv_file.flush()

            current_block = latest_block
        time.sleep(3)
except KeyboardInterrupt:
    print("\n🛑 Stopped by user.")
finally:
    csv_file.close()
