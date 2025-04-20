import csv
from web3 import Web3
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Connect to public BNB RPC
bsc_rpc = "https://bsc-dataseed.binance.org/"
web3 = Web3(Web3.HTTPProvider(bsc_rpc))

if not web3.is_Connected():
    print("❌ Unable to connect to BNB Chain RPC")
    exit()

print("✅ Connected to BNB Chain")

# Load addresses from file
with open("addresses.txt", "r") as f:
    addresses = [line.strip() for line in f if web3.isAddress(line.strip())]

print(f"🔍 Loaded {len(addresses)} addresses")

# Set your balance threshold here (in BNB)
BALANCE_THRESHOLD = 0.01

# Output CSV
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"bnb_balances_{timestamp}.csv"

# Define worker
def check_balance(address):
    try:
        balance_wei = web3.eth.get_balance(address)
        balance_bnb = web3.fromWei(balance_wei, 'ether')
        if balance_bnb > BALANCE_THRESHOLD:
            return address, float(balance_bnb)
    except Exception as e:
        print(f"⚠️ Error with {address}: {e}")
    return None

results = []
with ThreadPoolExecutor(max_workers=50) as executor:
    future_to_address = {executor.submit(check_balance, addr): addr for addr in addresses}
    for future in as_completed(future_to_address):
        result = future.result()
        if result:
            results.append(result)
            print(f"💰 {result[0]} → {result[1]} BNB")

# Save to CSV
with open(output_file, "w", newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["Wallet Address", "Balance (BNB)"])
    writer.writerows(results)

print(f"\n✅ Done! {len(results)} wallets with > {BALANCE_THRESHOLD} BNB saved to {output_file}")
