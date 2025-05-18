# Paxos Simulation and Analysis Toolkit

Based on [Essential Paxos by Tom Cocagne](https://github.com/cocagne/paxos)  
Project version: 1.0  
May 2025

---

## Overview

This repository builds on the original [Essential Paxos](https://github.com/cocagne/paxos) implementation by Tom Cocagne to provide an extended environment for **simulating**, **visualizing**, and **evaluating Paxos consensus performance** under varying network conditions and configurations.

The original Paxos implementation provides a clean, minimal, and domain-agnostic Paxos core, which we preserve. On top of this, we've developed a modular analysis suite under `paxos_analysis/` that includes:

- 📁 `paxos_analysis/`: Main analysis scripts
  - `paxos_simulation.py`: Core simulation engine
  - `plot_analysis.py`: Automated experiment runner + matplotlib/seaborn plots
  - `metrics.py`: Utility functions to track consensus time, retries, quorum behavior
  - `paxos_visualizer_qt.py`: Live visualization of messages and node states (optional)
  
- 📁 `img/`: Output plots for experiments (e.g. delay vs. consensus time, retry rates)

- 📁 `test/`: Original test suite for core Paxos logic (lightly modified)

---

## Getting Started

### Requirements

Install the minimal dependencies:

```bash
pip install -r paxos_analysis/requirements.txt
```

### Running a Simulation

To run a baseline Paxos simulation:

```bash
python paxos_analysis/plot_analysis.py
```

This will:
- Run multiple simulations with varied proposer/acceptor counts
- Measure retry behavior and consensus times
- Generate plots in `img/` folder

---

## Original Implementation

The original Paxos logic lives in the `paxos/` directory and remains close to the structure described by [Tom Cocagne](https://github.com/cocagne/paxos):

- `essential.py`: Minimal Paxos logic
- `practical.py`, `functional.py`, etc. (if included): Additional reliability layers
- `test/`: Unit tests for all modules

---

## Credits

- **Tom Cocagne** – [Essential Paxos](https://github.com/cocagne/paxos)
- **Ezgi Sena Karabacak** , ** Mehmet Oguz Arslan** – Paxos simulation and performance analysis extensions

---

## License

This project inherits the original MIT license from Essential Paxos. Feel free to reuse, modify, and cite.
