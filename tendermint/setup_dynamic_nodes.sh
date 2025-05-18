#!/bin/bash

NODE_COUNT=8

for i in $(seq 0 $((NODE_COUNT - 1)))
do
    docker run --rm \
    -v $(pwd)/node$i:/tendermint \
    tendermint/tendermint:v0.34.24 init
done


# 3. Copy genesis.json to all nodes from node0
for i in $(seq 1 $((NODE_COUNT - 1)))
do
    cp node0/config/genesis.json node$i/config/genesis.json
done

# 4. Get node IDs and build persistent_peers string
PERSISTENT_PEERS=""
for i in $(seq 0 $((NODE_COUNT - 1)))
do
    NODE_ID=$(docker run --rm -v $(pwd)/node$i:/tendermint tendermint/tendermint:v0.34.24 show-node-id)
    NODE_IP="172.30.0.$((i+2))"
    PEER="$NODE_ID@$NODE_IP:26656"
    if [ -z "$PERSISTENT_PEERS" ]; then
        PERSISTENT_PEERS="$PEER"
    else
        PERSISTENT_PEERS="$PERSISTENT_PEERS,$PEER"
    fi
done

# 5. Configure persistent_peers for each node
for i in $(seq 0 $((NODE_COUNT - 1)))
do
    echo "Setting peers for node$i..."
    CONFIG_FILE=node$i/config/config.toml
    sed -i '' "s/^persistent_peers = \".*\"/persistent_peers = \"$PERSISTENT_PEERS\"/" $CONFIG_FILE
done

# 6. Done!
echo "✅ Tendermint $NODE_COUNT-node network setup complete."
echo "👉 Now run: docker-compose up --build"

echo "⚡ To inject chaos, exec into a container and use 'tc netem' commands."

echo "Example: docker exec -it node0 sh"
