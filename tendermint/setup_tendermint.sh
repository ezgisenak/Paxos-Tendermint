#!/bin/bash

# Setup for Tendermint Chaos Lab (macOS M1/M2 Compatible)

set -e  # exit if any command fails

# 1. Create working directories
mkdir -p node0 node1 node2 node3

# 2. Initialize Tendermint nodes
for i in 0 1 2 3
  do
    echo "Initializing node$i..."
    docker run --rm \
      -v $(pwd)/node$i:/tendermint \
      tendermint/tendermint:v0.34.24 init
  done

# 3. Copy genesis.json to all nodes
cp node0/config/genesis.json node1/config/genesis.json
cp node0/config/genesis.json node2/config/genesis.json
cp node0/config/genesis.json node3/config/genesis.json

# 4. Get node0 ID (needed for persistent_peers)
NODE0_ID=$(docker run --rm -v $(pwd)/node0:/tendermint tendermint/tendermint:v0.34.24 show-node-id)
NODE1_ID=$(docker run --rm -v $(pwd)/node1:/tendermint tendermint/tendermint:v0.34.24 show-node-id)
NODE2_ID=$(docker run --rm -v $(pwd)/node2:/tendermint tendermint/tendermint:v0.34.24 show-node-id)
NODE3_ID=$(docker run --rm -v $(pwd)/node3:/tendermint tendermint/tendermint:v0.34.24 show-node-id)

# 5. Configure persistent_peers for each node
PERSISTENT_PEERS="$NODE0_ID@172.30.0.2:26656,$NODE1_ID@172.30.0.3:26656,$NODE2_ID@172.30.0.4:26656,$NODE3_ID@172.30.0.5:26656"

for i in 0 1 2 3
  do
    echo "Setting peers for node$i..."
    CONFIG_FILE=node$i/config/config.toml
    # macOS compatible sed (needs backup extension)
    sed -i '' "s/^persistent_peers = \".*\"/persistent_peers = \"$PERSISTENT_PEERS\"/" $CONFIG_FILE
  done

# 6. Done!
echo "✅ Tendermint network setup complete."
echo "👉 Now run: docker-compose up --build"

echo "⚡ To inject chaos, exec into a container and use 'tc netem' commands."

echo "Example: docker exec -it <container_name> bash"
