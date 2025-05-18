# Tendermint + Prometheus + Grafana (8-Node Setup)

This project sets up an 8-node Tendermint BFT network with full observability using **Prometheus** and **Grafana**.

---

## 🔧 Architecture Overview

- 8 Tendermint validator nodes (`node0` to `node7`)
- Each exposes:
  - ABCI (`26656`)
  - RPC (`26657`)
  - Prometheus metrics (`26660`)
- Prometheus scrapes each node on `26660`
- Grafana visualizes metrics like:
  - Consensus time
  - Proposer ID
  - Mempool size
  - Block interval
  - Throughput (TPS)

---


## 🧰 Prerequisites

- Docker + Docker Compose
- Python 3.7+
- `pip install toml requests`

---

## 🚀 Setup Steps

### 1. Generate node folders

```bash
./setup_dynamic_nodes.sh 8
```

This creates `node0` through `node7`, and sets up initial config and genesis.

---

### 2. Create a multi-validator genesis

```bash
python generate_validators.py
```

This:
- Collects all public validator keys
- Assigns equal voting power
- Injects into `genesis.json` for all nodes

---

### 3. Create Docker Compose (optional for faster tests)

```bash
./docker_compose_genrator.sh
```

This will create the docker compose file with 8 nodes.

---

### 4. Start the network

```bash
docker-compose up --build
```

This starts:
- 8 Tendermint nodes

---

### 5. Start the Prometheus and Grafana

```bash
docker-compose up -f docker-compose-observability.yml up
```

This will start Prometheus and Graphana

---

### 6. Send test transactions

```bash
python tx_spammer.py
```

Adjust `RATE_PER_SEC` and `DURATION_SEC` in the script for desired load.

---

### 7. View dashboards

- Open Grafana: `http://localhost:3000`
- Import the provided dashboard JSON
- Watch:
  - Block times
  - Proposers
  - Mempool size
  - TPS (throughput)

---

## 🔍 Metrics You Can Use

| Metric                                  | Meaning                          |
|-----------------------------------------|----------------------------------|
| `tendermint_consensus_block_interval_seconds` | Block-to-block time             |
| `tendermint_consensus_proposer_address` | Validator address of proposer   |
| `tendermint_consensus_round`           | Current round number             |
| `tendermint_mempool_size`              | Number of pending transactions   |
| `rate(tendermint_consensus_total_txs[1m])` | Transactions per second         |

---




