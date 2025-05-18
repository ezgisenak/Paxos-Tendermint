import requests
import time

# Configuration
NODE_RPC = "http://localhost:26657"
RATE_PER_SEC = 10000              # Transactions per second
DURATION_SEC = 60             # Total duration to spam in seconds

print(f"🚀 Starting Tendermint TX spammer for {DURATION_SEC} seconds at {RATE_PER_SEC} tx/sec...")

INTERVAL = 1.0 / RATE_PER_SEC
TOTAL_TX = DURATION_SEC * RATE_PER_SEC

for i in range(1, TOTAL_TX + 1):
    tx_data = f"test_tx_{int(time.time() * 1e9)}_{i}"
    try:
        requests.get(f"{NODE_RPC}/broadcast_tx_async?tx=\"{tx_data}\"", timeout=2)
    except requests.exceptions.RequestException as e:
        print(f"❗ Error sending TX {i}: {e}")


print("✅ TX spam complete.")
