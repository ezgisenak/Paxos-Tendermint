#!/bin/bash

NODE_COUNT=8
NETWORK_NAME="tendermintnet"

echo "version: '3.7'

services:" > docker-compose.yml

for i in $(seq 0 $((NODE_COUNT - 1)))
do
    NODE_IP="172.30.0.$((i+2))"
    PORT_P2P=$((26656 + i * 10))
    PORT_RPC=$((PORT_P2P + 1))
    PORT_METRICS=$((PORT_P2P + 2))

    cat <<EOF >> docker-compose.yml
  node$i:
    container_name: node$i
    image: tendermint/tendermint:v0.34.24
    command: ["node", "--proxy_app=kvstore"]
    cap_add:
      - NET_ADMIN
    ports:
      - "${PORT_P2P}:26656"
      - "${PORT_RPC}:26657"
      - "${PORT_METRICS}:26660"
    volumes:
      - ./node$i:/tendermint
    networks:
      $NETWORK_NAME:
        ipv4_address: $NODE_IP

EOF
done

cat <<EOF >> docker-compose.yml
networks:
  $NETWORK_NAME:
    external: true
EOF

echo "✅ docker-compose.yml generated with $NODE_COUNT nodes."
