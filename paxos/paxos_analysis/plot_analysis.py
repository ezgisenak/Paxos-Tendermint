import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
import seaborn as sns
import time
import logging
from paxos_simulation import simulate_paxos, NetworkSimulator, PaxosProposer, PaxosAcceptor, PaxosLearner, ProposalID

# Set up logging
def setup_logging(enable_logs: bool = True):
    """Configure logging based on enable_logs parameter"""
    # Set root logger level
    if enable_logs:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Set specific logger levels
    loggers = [
        logging.getLogger('paxos_simulation'),
        logging.getLogger('NetworkSimulator'),
        logging.getLogger('PaxosProposer'),
        logging.getLogger('PaxosAcceptor'),
        logging.getLogger('PaxosLearner')
    ]
    
    for logger in loggers:
        logger.setLevel(logging.INFO if enable_logs else logging.WARNING)
    
    return logging.getLogger(__name__)

# Global logger instance
logger = True

def plot_message_stats(delay_ranges: List[Tuple[float, float]], failure_rates: List[float]):
    """Plot message statistics for different network conditions"""
    results = []
    total_sims = len(delay_ranges) * len(failure_rates)
    current_sim = 0
    
    print(f"Running {total_sims} simulations...")
    for delay in delay_ranges:
        for failure in failure_rates:
            current_sim += 1
            print(f"Simulation {current_sim}/{total_sims}: delay={delay}, failure_rate={failure}")
            
            success_rate, avg_time, message_count, dropped_count, _ = simulate_paxos(
                num_proposers=2,
                num_acceptors=2,
                num_learners=2,
                delay_range=delay,
                failure_rate=failure,
                timeout=30.0,  # Increased timeout for each simulation
                enable_logs=True
            )
            results.append({
                'delay': f"{delay[0]}-{delay[1]}s",
                'failure_rate': failure,
                'success_rate': success_rate,
                'avg_time': avg_time,
                'message_count': message_count,
                'dropped_count': dropped_count
            })
            print(f"  Results: success={success_rate}, latency={avg_time:.2f}s, messages={message_count}, dropped={dropped_count}")
    
    df = pd.DataFrame(results)
    
    # Create subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Paxos Simulation Analysis', fontsize=16)
    
    # Plot 1: Success Rate vs Failure Rate
    sns.barplot(data=df, x='failure_rate', y='success_rate', hue='delay', ax=ax1)
    ax1.set_title('Success Rate vs Failure Rate')
    ax1.set_xlabel('Failure Rate')
    ax1.set_ylabel('Success Rate')
    
    # Plot 2: Average Time vs Delay
    sns.boxplot(data=df, x='delay', y='avg_time', hue='failure_rate', ax=ax2)
    ax2.set_title('Average Consensus Time vs Network Delay')
    ax2.set_xlabel('Network Delay Range (s)')
    ax2.set_ylabel('Average Time (s)')
    
    # Plot 3: Message Count vs Failure Rate
    sns.barplot(data=df, x='failure_rate', y='message_count', hue='delay', ax=ax3)
    ax3.set_title('Total Messages vs Failure Rate')
    ax3.set_xlabel('Failure Rate')
    ax3.set_ylabel('Total Messages')
    
    # Plot 4: Dropped Messages vs Failure Rate
    sns.barplot(data=df, x='failure_rate', y='dropped_count', hue='delay', ax=ax4)
    ax4.set_title('Dropped Messages vs Failure Rate')
    ax4.set_xlabel('Failure Rate')
    ax4.set_ylabel('Dropped Messages')
    
    plt.tight_layout()
    plt.savefig('paxos_analysis.png')
    plt.close()

def plot_node_impact(num_proposers: int = 2,
                    num_acceptors: int = 2,
                    num_learners: int = 0,
                    delay_range: Tuple[float, float] = (0.0, 0.0),
                    failure_rate: float = 0.0,
                    enable_logs: bool = True):
    """Plot the impact of a single node configuration"""
    logger = setup_logging(enable_logs)
    
    print(f"Testing configuration: P{num_proposers}-A{num_acceptors}-L{num_learners}")
    wait_time, consensus_before, consensus_after, consensus_time, _ = simulate_paxos(
        num_proposers=num_proposers,
        num_acceptors=num_acceptors,
        num_learners=num_learners,
        delay_range=delay_range,
        failure_rate=failure_rate
    )
    
    print(f"\nConsensus timing:")
    print(f"Time to reach consensus: {consensus_time:.6f} seconds")
    
    # Create results for plotting
    results = [{
        'config': f'P{num_proposers}-A{num_acceptors}-L{num_learners}',
        'success_rate': float(consensus_before and consensus_after),
        'avg_time': consensus_time,  # Use consensus time instead of wait time
        'message_count': 0,  # These metrics are no longer tracked
        'dropped_count': 0   # These metrics are no longer tracked
    }]
    
    df = pd.DataFrame(results)
    
    # Create subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Node Configuration Analysis', fontsize=16)
    
    # Plot 1: Success Rate
    sns.barplot(data=df, x='config', y='success_rate', ax=ax1)
    ax1.set_title('Success Rate')
    ax1.set_xlabel('Configuration (P-Proposers, A-Acceptors, L-Learners)')
    ax1.set_ylabel('Success Rate')
    
    # Plot 2: Average Time
    sns.barplot(data=df, x='config', y='avg_time', ax=ax2)
    ax2.set_title('Average Consensus Time')
    ax2.set_xlabel('Configuration')
    ax2.set_ylabel('Average Time (s)')
    
    # Plot 3: Message Count
    sns.barplot(data=df, x='config', y='message_count', ax=ax3)
    ax3.set_title('Total Messages')
    ax3.set_xlabel('Configuration')
    ax3.set_ylabel('Total Messages')
    
    # Plot 4: Dropped Messages
    sns.barplot(data=df, x='config', y='dropped_count', ax=ax4)
    ax4.set_title('Dropped Messages')
    ax4.set_xlabel('Configuration')
    ax4.set_ylabel('Dropped Messages')
    
    plt.tight_layout()
    plt.savefig('node_config_analysis.png')
    plt.close()

def analyze_acceptor_impact(
    max_acceptors: int = 10, 
    num_proposers: int = 2,
    num_learners: int = 0,
    delay_range: Tuple[float, float] = (0.0, 0.0),
    failure_rate: float = 0.0,
    runs_per_config: int = 5
):
    """Analyze how the number of acceptors affects consensus time, with averaging and variance."""
    results = []
    print("\nAnalyzing impact of number of acceptors...")

    for num_acceptors in range(2, max_acceptors + 1, 2):
        print(f"\nTesting with {num_acceptors} acceptors...")
        times = []
        for _ in range(runs_per_config):
            wait_time, consensus_before, consensus_time, rounds, total_retries = simulate_paxos(
                num_proposers=num_proposers,
                num_acceptors=num_acceptors,
                num_learners=num_learners,
                delay_range=delay_range,
                failure_rate=failure_rate
            )
            if consensus_time is not None:
                times.append(consensus_time)
        if times:
            avg_time = np.mean(times)
            std_time = np.std(times)
            results.append({
                'num_acceptors': num_acceptors,
                'avg_consensus_time': avg_time,
                'std_consensus_time': std_time,
                'quorum_size': num_acceptors // 2 + 1
            })
            print(f"Consensus time: {avg_time:.4f}s ± {std_time:.4f}s (Quorum size: {num_acceptors // 2 + 1})")
        else:
            print(f"Consensus NOT reached (timeout)")

    # Plot results
    df = pd.DataFrame(results)
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.errorbar(
        df['num_acceptors'],
        df['avg_consensus_time'] * 1000,  # ms
        yerr=df['std_consensus_time'] * 1000,  # ms
        fmt='o-', color='#007acc', ecolor='gray', elinewidth=2, capsize=5, markersize=8, label='Avg Consensus Time'
    )
    ax.set_xlabel('Number of Acceptors', fontsize=14, fontweight='bold')
    ax.set_ylabel('Consensus Time (ms)', fontsize=14, fontweight='bold')
    ax.set_title('Impact of Number of Acceptors on Consensus Time', fontsize=16, fontweight='bold', pad=20)
    ax.grid(True, which='both', linestyle='--', linewidth=0.7, alpha=0.7)
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white')
    plt.tight_layout()
    plt.legend()
    plt.savefig('acceptor_impact_avg_var.png', dpi=150, bbox_inches='tight')
    plt.show()

def analyze_proposer_impact(
    max_proposers: int = 5,
    num_acceptors: int = 4,
    num_learners: int = 0,
    delay_range: Tuple[float, float] = (0.0, 0.0),
    failure_rate: float = 0.0,
    runs_per_config: int = 5
):
    """Analyze how the number of proposers affects consensus time, with averaging and variance."""
    results = []
    print("\nAnalyzing impact of number of proposers...")

    for num_proposers in range(1, max_proposers + 1):
        print(f"\nTesting with {num_proposers} proposers...")
        times = []
        for _ in range(runs_per_config):
            wait_time, consensus_before, consensus_time, rounds, total_retries = simulate_paxos(
                num_proposers=num_proposers,
                num_acceptors=num_acceptors,
                num_learners=num_learners,
                delay_range=delay_range,
                failure_rate=failure_rate
            )
            if consensus_time is not None:
                times.append(consensus_time)
        if times:
            avg_time = np.mean(times)
            std_time = np.std(times)
            results.append({
                'num_proposers': num_proposers,
                'avg_consensus_time': avg_time,
                'std_consensus_time': std_time
            })
            print(f"Consensus time: {avg_time:.4f}s ± {std_time:.4f}s")
        else:
            print(f"Consensus NOT reached (timeout)")

    # Plot results
    df = pd.DataFrame(results)
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.errorbar(
        df['num_proposers'],
        df['avg_consensus_time'] * 1000,  # ms
        yerr=df['std_consensus_time'] * 1000,  # ms
        fmt='o-', color='#e67e22', ecolor='gray', elinewidth=2, capsize=5, markersize=8, label='Avg Consensus Time'
    )
    ax.set_xlabel('Number of Proposers', fontsize=14, fontweight='bold')
    ax.set_ylabel('Consensus Time (ms)', fontsize=14, fontweight='bold')
    ax.set_title('Impact of Number of Proposers on Consensus Time', fontsize=16, fontweight='bold', pad=20)
    ax.grid(True, which='both', linestyle='--', linewidth=0.7, alpha=0.7)
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white')
    plt.tight_layout()
    plt.savefig('proposer_impact_avg_var.png', dpi=150, bbox_inches='tight')
    plt.legend()
    plt.show()

def analyze_network_conditions(
    delay_ranges: List[Tuple[float, float]] = [(0.01, 0.05), (0.1, 0.2), (0.3, 0.5)],
    failure_rates: List[float] = [0.0, 0.1, 0.2],
    num_proposers: int = 2,
    num_acceptors: int = 4,
    num_learners: int = 0,
    runs_per_config: int = 5
):
    """Analyze how network conditions affect consensus time, with averaging and variance."""
    results = []
    print("\nAnalyzing impact of network conditions...")

    for delay in delay_ranges:
        for failure in failure_rates:
            print(f"\nTesting with delay={delay}, failure_rate={failure}...")
            times = []
            for _ in range(runs_per_config):
                wait_time, consensus_before, consensus_time, rounds, total_retries = simulate_paxos(
                    num_proposers=num_proposers,
                    num_acceptors=num_acceptors,
                    num_learners=num_learners,
                    delay_range=delay,
                    failure_rate=failure
                )
                if consensus_time is not None:
                    times.append(consensus_time)
            if times:
                avg_time = np.mean(times)
                std_time = np.std(times)
                results.append({
                    'delay': f"{delay[0]}-{delay[1]}s",
                    'failure_rate': failure,
                    'avg_consensus_time': avg_time,
                    'std_consensus_time': std_time,
                    'total_retries': total_retries
                })
                print(f"Consensus time: {avg_time:.4f}s ± {std_time:.4f}s")
            else:
                print(f"Consensus NOT reached (timeout)")

    # Plot results
    df = pd.DataFrame(results)
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(14, 8))  # Increased figure size
    for delay in df['delay'].unique():
        delay_data = df[df['delay'] == delay]
        ax.errorbar(
            delay_data['failure_rate'],
            delay_data['avg_consensus_time'] * 1000,  # ms
            yerr=delay_data['std_consensus_time'] * 1000,  # ms
            fmt='o-', label=f'Network Delay: {delay}s', capsize=5, markersize=10  # Increased marker size
        )
    ax.set_xlabel('Message Failure Rate', fontsize=16, fontweight='bold')
    ax.set_ylabel('Consensus Time (ms)', fontsize=16, fontweight='bold')
    ax.set_title('Impact of Network Conditions on Consensus Time', fontsize=20, fontweight='bold', pad=20)
    ax.grid(True, which='both', linestyle='--', linewidth=0.7, alpha=0.7)
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white')
    # Increase tick label sizes
    ax.tick_params(axis='both', which='major', labelsize=14)
    plt.tight_layout()
    plt.legend(loc='best', fontsize=14)  # Increased legend font size
    plt.savefig('network_conditions_impact_avg_var.png', dpi=150, bbox_inches='tight')
    plt.show()

    # Plot retry attempts
    plt.figure(figsize=(14, 8))  # Increased figure size
    for delay in df['delay'].unique():
        delay_df = df[df['delay'] == delay]
        plt.plot(delay_df['failure_rate'], delay_df['total_retries'], marker='o', markersize=10, label=f'Network Delay: {delay}s')  # Increased marker size
    plt.xlabel('Message Failure Rate', fontsize=16, fontweight='bold')
    plt.ylabel('Total Retry Attempts', fontsize=16, fontweight='bold')
    plt.title('Retry Attempts vs Failure Rate under Different Network Delays', fontsize=20, fontweight='bold', pad=20)
    plt.grid(True, which='both', linestyle='--', linewidth=0.7, alpha=0.7)
    # Increase tick label sizes
    plt.xticks(fontsize=14)
    plt.yticks(fontsize=14)
    plt.tight_layout()
    plt.legend(loc='best', fontsize=14)  # Increased legend font size
    plt.savefig('retry_vs_failure_avg_var.png', dpi=150, bbox_inches='tight')
    plt.show()

def analyze_rounds_vs_conditions(delay_ranges: List[Tuple[float, float]] = [(0.01, 0.05), (0.1, 0.2), (0.3, 0.5)],
                               failure_rates: List[float] = [0.0, 0.1, 0.2],
                               num_proposers: int = 2,
                               num_acceptors: int = 4,
                               num_learners: int = 0,
                               runs_per_config: int = 5):
    """Analyze how many rounds are needed to reach consensus under different conditions"""
    results = []
    print("\nAnalyzing rounds needed for consensus...")
    
    for delay in delay_ranges:
        for failure in failure_rates:
            print(f"\nTesting with delay={delay}, failure_rate={failure}...")
            times = []
            for _ in range(runs_per_config):
                wait_time, consensus_before, consensus_time, rounds, total_retries = simulate_paxos(
                    num_proposers=num_proposers,
                    num_acceptors=num_acceptors,
                    num_learners=num_learners,
                    delay_range=delay,
                    failure_rate=failure
                )
                # Only add to results if consensus was reached
                if consensus_time is not None:
                    times.append(consensus_time)
                    results.append({
                        'delay': f"{delay[0]}-{delay[1]}s",
                        'failure_rate': failure,
                        'consensus_time': consensus_time,
                        'rounds': rounds
                    })
                    print(f"Consensus time: {consensus_time:.6f}s (Approx. rounds: {rounds})")
                else:
                    print(f"Consensus NOT reached (timeout)")
    
    # Plot results
    df = pd.DataFrame(results)
    plt.figure(figsize=(12, 6))
    
    # Plot for different delay ranges
    for delay in df['delay'].unique():
        delay_data = df[df['delay'] == delay]
        plt.plot(delay_data['failure_rate'], delay_data['rounds'], 'o-', label=f'Delay: {delay}')
    
    plt.xlabel('Failure Rate')
    plt.ylabel('Number of Rounds')
    plt.title('Rounds Needed for Consensus Under Different Network Conditions')
    plt.legend()
    plt.grid(True)
    plt.savefig('rounds_vs_conditions.png')
    plt.close()

def plot_elapsed_time_vs_delay(
    delay_ranges: List[Tuple[float, float]] = [(0.01, 0.05), (0.05, 0.1), (0.1, 0.2), (0.2, 0.3), (0.3, 0.4), (0.4, 0.5), (0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0)],
    failure_rate: float = 0.0,
    num_proposers: int = 2,
    num_acceptors: int = 4,
    num_learners: int = 0,
    runs_per_config: int = 3
):
    """Plot average consensus time vs network delay with a white background and improved style. Runs each config multiple times and averages results."""
    results = []
    print("\nAnalyzing elapsed time vs delay...")

    for delay in delay_ranges:
        times = []
        for _ in range(runs_per_config):
            _, consensus_before, consensus_time, _, _ = simulate_paxos(
                num_proposers=num_proposers,
                num_acceptors=num_acceptors,
                num_learners=num_learners,
                delay_range=delay,
                failure_rate=failure_rate
            )
            if consensus_before and consensus_time is not None:
                times.append(consensus_time)
        avg_time = np.mean(times) if times else None
        std_time = np.std(times) if times else None
        results.append({
            'delay': f"{delay[0]}-{delay[1]}",
            'avg_consensus_time': avg_time,
            'std_consensus_time': std_time
        })
        print(f"Delay {delay}: Avg consensus time = {avg_time:.4f}s ± {std_time:.4f}s")

    # Plot
    df = pd.DataFrame(results)

    # Convert delay and consensus time to ms
    df['avg_consensus_time_ms'] = df['avg_consensus_time'] * 1000 if df['avg_consensus_time'] is not None else None
    df['std_consensus_time_ms'] = df['std_consensus_time'] * 1000 if df['std_consensus_time'] is not None else None
    df['delay_min_ms'] = df['delay'].apply(lambda x: float(x.split('-')[0]) * 1000)
    df['delay_max_ms'] = df['delay'].apply(lambda x: float(x.split('-')[1]) * 1000)
    df['delay_label'] = df.apply(lambda row: f"{int(row['delay_min_ms'])}-{int(row['delay_max_ms'])}", axis=1)

    # Use a white background and modern style
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.errorbar(
        df['delay_label'],
        df['avg_consensus_time_ms'],
        yerr=df['std_consensus_time_ms'],
        marker='o', color='#007acc', linewidth=2, markersize=8, capsize=5
    )
    ax.set_xlabel('Network Delay Range (ms)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Average Consensus Time (ms)', fontsize=14, fontweight='bold')
    ax.set_title('Elapsed Consensus Time vs Network Delay', fontsize=16, fontweight='bold', pad=20)
    ax.grid(True, which='both', linestyle='--', linewidth=0.7, alpha=0.7)
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white')
    # Add value markers
    for i, v in enumerate(df['avg_consensus_time_ms']):
        if not pd.isnull(v):
            ax.text(i, v + max(df['avg_consensus_time_ms']) * 0.02, f"{v:.0f}", ha='center', va='bottom', fontsize=11, color='#333333')
    plt.tight_layout()
    plt.savefig('elapsed_time_vs_delay_ms.png', dpi=150, bbox_inches='tight')
    plt.show()

if __name__ == "__main__":
    # Set style
    plt.style.use('ggplot')
    
    # Run all analyses
    print("Starting Paxos analysis...")
    
    # 1. Analyze impact of number of acceptors
    #analyze_acceptor_impact(
    #    max_acceptors=10,
    #    num_proposers=2,
    #    num_learners=2,
    #    delay_range=(0.01, 0.05),
    #    failure_rate=0.0,
    #    runs_per_config=5
    #)
    
    # 2. Analyze impact of number of proposers
    #analyze_proposer_impact(
    #    max_proposers=10,
    #    num_acceptors=4,
    #    num_learners=4,
    #    delay_range=(0.01, 0.05),
    #    failure_rate=0.0,
    #    runs_per_config=5
    #)
    
    # 3. Analyze impact of network conditions
    #analyze_network_conditions(
    #    delay_ranges=[(0.01, 0.05), (0.1, 0.2), (0.2, 0.3), (0.3, 0.4)],  # Keep a constant delay range
    #    failure_rates=[0.1, 0.2, 0.3, 0.4],  # Vary failure rates
    #    num_proposers=2,
    #    num_acceptors=4,
    #    num_learners=4,
    #    runs_per_config=5
    #)
    
    plot_elapsed_time_vs_delay(
        delay_ranges=[(0.01, 0.05), (0.05, 0.1), (0.1, 0.2), (0.2, 0.3), (0.3, 0.4), (0.4, 0.5), (0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0)],
        failure_rate=0.0,
        num_proposers=2,
        num_acceptors=4,
        num_learners=0,
        runs_per_config=3
    )
    
    print("\nAnalysis complete! Check the generated PNG files for results.") 