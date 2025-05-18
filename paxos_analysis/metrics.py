import time
import numpy as np
import matplotlib.pyplot as plt
from paxos_simulation import simulate_paxos, NetworkSimulator, PaxosProposer, PaxosAcceptor, PaxosLearner, ProposalID
import logging

logging.basicConfig(level=logging.CRITICAL)  # suppress verbose logs

def headless_run(drop_rate, num_crashes=0, num_proposers=2, num_acceptors=3, num_learners=2):
    """
    Run one simulation headlessly, returns:
      latency   : time to reach consensus (sec or None if failed)
      total_msgs: total messages sent
      dropped   : total messages dropped
      success   : bool
    """
    try:
        # Initialize network
        network = NetworkSimulator((0.0, 0.0), drop_rate)
        # Create nodes
        proposers = [PaxosProposer(f'P{i}', network, num_acceptors//2+1) for i in range(num_proposers)]
        acceptors = [PaxosAcceptor(f'A{i}', network) for i in range(num_acceptors)]
        learners  = [PaxosLearner(f'L{i}', network, num_acceptors//2+1) for i in range(num_learners)]
        # Register nodes
        for node in proposers+acceptors+learners:
            node.start()
        
        # Run the Paxos phases
        t0 = time.time()
        
        # Phase 1a
        proposers[0].set_proposal("Value")
        proposers[0].prepare()
        time.sleep(0.5)  # Increased wait time
        
        # Phase 1b responses
        for a in acceptors:
            if a.running:  # Only send to running acceptors
                a.recv_prepare("P0", proposers[0].proposal_id)
        time.sleep(0.5)  # Increased wait time
        
        # Phase 2a accept
        proposers[0].send_accept(proposers[0].proposal_id, "Value")
        time.sleep(0.5)  # Increased wait time
        
        # Phase 2b accept responses
        for a in acceptors:
            if a.running:  # Only send to running acceptors
                a.recv_accept_request("P0", proposers[0].proposal_id, "Value")
        
        # Crash leaders if requested
        proposers[0].running = False
        
        # Additional crashes
        for i in range(1, num_crashes+1):
            if i < len(acceptors):
                acceptors[i].running = False
        
        time.sleep(1.0)  # Increased wait time
        
        # New proposer takes over
        if num_proposers>1:
            proposers[1].set_proposal("Value2")
            proposers[1].prepare()
            time.sleep(0.5)  # Increased wait time
            
            for a in acceptors:
                if a.running:
                    a.recv_prepare("P1", proposers[1].proposal_id)
            time.sleep(0.5)  # Increased wait time
            
            proposers[1].send_accept(proposers[1].proposal_id, "Value2")
            time.sleep(0.5)  # Increased wait time
            
            for a in acceptors:
                if a.running:
                    a.recv_accept_request("P1", proposers[1].proposal_id, "Value2")
        
        # Wait longer for learners
        time.sleep(1.0)
        
        # Stop network
        network.stop()
        
        # Check learner for consensus
        final_vals = [l.final_value for l in learners if l.running]
        success = any(v is not None for v in final_vals)
        latency = time.time() - t0 if success else None
        
        return latency, network.message_count, network.dropped_messages, success
    
    except Exception as e:
        logging.error(f"Error in headless_run: {e}")
        return None, 0, 0, False


def batch_drop_rate(drop_rates, runs=10):
    latencies = []
    totals    = []
    drops     = []
    successes = []
    for dr in drop_rates:
        run_lat = []
        run_tot = []
        run_drop= []
        run_suc = []
        for _ in range(runs):
            lat, tot, drp, suc = headless_run(dr)
            run_lat.append(lat if lat is not None else np.nan)
            run_tot.append(tot)
            run_drop.append(drp)
            run_suc.append(1 if suc else 0)
        latencies.append(np.nanmean(run_lat))
        totals.append(np.mean(run_tot))
        drops.append(np.mean(run_drop))
        successes.append(np.mean(run_suc))
    return np.array(latencies), np.array(totals), np.array(drops), np.array(successes)


def batch_crash_counts(crash_counts, drop_rate=0.1, runs=10):
    latencies = []
    successes = []
    for nc in crash_counts:
        run_lat = []
        run_suc = []
        for _ in range(runs):
            lat, _, _, suc = headless_run(drop_rate, num_crashes=nc)
            run_lat.append(lat if lat is not None else np.nan)
            run_suc.append(1 if suc else 0)
        latencies.append(np.nanmean(run_lat))
        successes.append(np.mean(run_suc))
    return np.array(latencies), np.array(successes)


def plot_all():
    drop_rates = np.linspace(0, 0.9, 10)
    crash_counts = list(range(4))  # 0..3
    runs = 20

    lat, tot, drp, suc = batch_drop_rate(drop_rates, runs)
    lat_c, suc_c = batch_crash_counts(crash_counts, drop_rate=0.3, runs=runs)

    fig, axs = plt.subplots(2, 2, figsize=(12, 10))

    ax = axs[0,0]
    ax.plot(drop_rates*100, lat, marker='o')
    ax.set_title('Consensus Latency vs. Drop Rate')
    ax.set_xlabel('Message Drop Rate (%)')
    ax.set_ylabel('Latency (s)')

    ax = axs[0,1]
    ax.plot(drop_rates*100, tot, marker='o')
    ax.set_title('Total Messages vs. Drop Rate')
    ax.set_xlabel('Message Drop Rate (%)')
    ax.set_ylabel('Total Messages Sent')

    ax = axs[1,0]
    ax.plot(drop_rates*100, suc, marker='o')
    ax.set_title('Success Rate vs. Drop Rate')
    ax.set_xlabel('Message Drop Rate (%)')
    ax.set_ylabel('Success Fraction')

    ax = axs[1,1]
    ax2 = ax.twinx()
    ax.plot(crash_counts, suc_c, 'r-o', label='Success Rate')
    ax2.plot(crash_counts, lat_c, 'b-s', label='Latency')
    ax.set_title('Impact of Crashes (Drop Rate 30%)')
    ax.set_xlabel('Number of Additional Acceptor Crashes')
    ax.set_ylabel('Success Fraction', color='r')
    ax2.set_ylabel('Latency (s)', color='b')

    fig.tight_layout()
    plt.savefig('paxos_metrics.png')
    plt.show()


if __name__ == '__main__':
    plot_all() 