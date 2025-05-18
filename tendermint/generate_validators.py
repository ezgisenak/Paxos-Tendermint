import os
import json

NODE_COUNT = 8
NODE_PREFIX = "node"
GENESIS_REL_PATH = "config/genesis.json"
VALIDATOR_KEY_PATH = "config/priv_validator_key.json"
OUTPUT_GENESIS = "genesis_updated.json"

validators = []

for i in range(NODE_COUNT):
    node_dir = f"{NODE_PREFIX}{i}"
    key_path = os.path.join(node_dir, VALIDATOR_KEY_PATH)

    with open(key_path, "r") as f:
        key_data = json.load(f)

    validators.append({
        "address": key_data["address"],
        "pub_key": key_data["pub_key"],
        "power": "1",  # Equal power for all
        "name": node_dir
    })

# Load base genesis (from node0)
with open(os.path.join(f"{NODE_PREFIX}0", GENESIS_REL_PATH), "r") as f:
    genesis = json.load(f)

# Replace validators
genesis["validators"] = validators

# Save updated genesis
with open(OUTPUT_GENESIS, "w") as f:
    json.dump(genesis, f, indent=2)

print(f"✅ Updated genesis with {NODE_COUNT} validators saved to {OUTPUT_GENESIS}")

# Overwrite each node's genesis.json
for i in range(NODE_COUNT):
    node_path = os.path.join(f"{NODE_PREFIX}{i}", GENESIS_REL_PATH)
    with open(node_path, "w") as f:
        json.dump(genesis, f, indent=2)

print("✅ Synced genesis.json to all nodes.")
