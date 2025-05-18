from paxos.essential import Proposer, Acceptor, Learner, ProposalID
import threading
import time
import random
import queue
from typing import Dict, List, Tuple, Optional, TYPE_CHECKING
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NetworkMessage:
    def __init__(self, msg_type: str, sender: str, receiver: str,
                 proposal_id: ProposalID, previous_id: Optional[ProposalID] = None,
                 accepted_value: Optional[str] = None, dropped=False):
        self.msg_type = msg_type
        self.sender = sender
        self.receiver = receiver
        self.proposal_id = proposal_id
        self.previous_id = previous_id
        self.accepted_value = accepted_value
        self.dropped = dropped

class NetworkSimulator:
    def __init__(self, delay_range: Tuple[float, float] = (0.05, 0.1), 
                 failure_rate: float = 0.0, visualizer=None):
        self.nodes = {}  # Store actual node objects
        self.delay_range = delay_range
        self.failure_rate = failure_rate
        self.running = True
        self.message_count = 0
        self.dropped_messages = 0
        self.visualizer = visualizer
        self.max_retries = 3  # Maximum number of retries for dropped messages
        self.active_messages = set()  # Track active messages to prevent duplicates
        self.message_lock = threading.Lock()  # Add lock for thread safety
        self.message_queue = queue.Queue()  # Add message queue for ordered processing
        self.total_retries = 0
        
    def register_node(self, node: 'PaxosNode'):
        """Register a node with the network simulator"""
        self.nodes[node.node_id] = node
        
    def send_message(self, msg: NetworkMessage, retry_count=0):
        if not self.running:
            return
            
        # Create a unique identifier for this message
        msg_id = f"{msg.sender}-{msg.receiver}-{msg.msg_type}-{msg.proposal_id}-{retry_count}"
        
        with self.message_lock:
            # Skip if this message is already being processed
            if msg_id in self.active_messages:
                return
                
            self.active_messages.add(msg_id)
            self.message_count += 1
            
            # Only simulate message loss if failure rate is greater than 0
            if self.failure_rate > 0 and random.random() < self.failure_rate:
                self.dropped_messages += 1
                msg.dropped = True
                
                if self.visualizer:
                    self.visualizer.log_message(f"Message dropped: {msg.msg_type} from {msg.sender} to {msg.receiver}")
                    self.visualizer.draw_message(msg)
                    
                # Skip retries if failure rate is 100%
                if self.failure_rate >= 1.0:
                    self.active_messages.remove(msg_id)
                    return
                    
                # Retry logic for dropped messages
                if retry_count < self.max_retries:
                    if self.visualizer:
                        self.visualizer.log_message(f"Retrying message (attempt {retry_count + 1}/{self.max_retries})")
                    # Schedule retry with exponential backoff
                    delay = min(0.5 * (2 ** retry_count), 5.0)  # Up to 5s delay
                    threading.Timer(delay, self._retry_message, args=[msg_id, msg.sender, msg.receiver, msg, retry_count + 1]).start()
                else:
                    if self.visualizer:
                        self.visualizer.log_message(f"Message permanently dropped after {self.max_retries} retries")
                    self.active_messages.remove(msg_id)
                return
                
            msg.dropped = False
            
            # Simulate network delay
            delay = random.uniform(*self.delay_range)
            if delay == 0.0:
                threading.Thread(target=self._deliver_message, args=(msg, msg_id), daemon=True).start()
            else:
                threading.Thread(
                    target=self._delayed_delivery,
                    args=(msg, msg_id, delay),
                    daemon=True
                ).start()
            
            # Visualize message if visualizer is available
            if self.visualizer:
                self.visualizer.draw_message(msg)
                self.visualizer.log_message(f"Message sent: {msg.msg_type} from {msg.sender} to {msg.receiver}")

    def _retry_message(self, msg_id, from_node, to_node, message, attempt=0):
        try:
            with self.message_lock:  # Use lock when modifying shared state
                if not self.running or attempt >= 3:  # Don't retry if simulator is stopped
                    if msg_id in self.active_messages:
                        self.active_messages.remove(msg_id)
                    return

                if msg_id not in self.active_messages:  # Message already delivered
                    return

                # Simulate message drop
                if random.random() < self.failure_rate:
                    self.total_retries += 1  
                    self.dropped_messages += 1
                    # Schedule retry with exponential backoff
                    delay = min(0.1 * (2 ** attempt), 1.0)  # Cap maximum delay at 1 second
                    threading.Timer(delay, self._retry_message, 
                                 args=[msg_id, from_node, to_node, message, attempt + 1]).start()
                    return

                # Deliver message if not dropped and node exists and is running
                if to_node in self.nodes:
                    # Get the actual node from the nodes dictionary
                    target_node = self.nodes[to_node]
                    if target_node.running:
                        target_node.handle_message(message)
                
                self.active_messages.remove(msg_id)

        except Exception as e:
            logging.error(f"Error in _retry_message: {e}")
            with self.message_lock:
                if msg_id in self.active_messages:
                    self.active_messages.remove(msg_id)
        
    def _deliver_message(self, msg: NetworkMessage, msg_id: str):
        """Deliver a message to its destination node"""
        try:
            if msg.receiver in self.nodes:
                target_node = self.nodes[msg.receiver]
                if target_node.running:
                    target_node.handle_message(msg)
        finally:
            with self.message_lock:
                if msg_id in self.active_messages:
                    self.active_messages.remove(msg_id)
            
    def _delayed_delivery(self, msg, msg_id, delay):
        time.sleep(delay)
        self._deliver_message(msg, msg_id)

    def stop(self):
        self.running = False
        if self.visualizer:
            self.visualizer.log_message(f"Network stats: {self.message_count} messages sent, {self.dropped_messages} dropped")
        self.active_messages.clear()

class PaxosNode:
    def __init__(self, node_id: str, network: NetworkSimulator):
        self.node_id = node_id
        self.network = network
        self.running = True
        self.message_timeouts = {}  # Track message timeouts
        network.register_node(self)
        
    def start(self):
        """Start the node's message processing"""
        self.running = True
        
    def handle_message(self, msg: NetworkMessage):
        """Handle an incoming message - to be implemented by subclasses"""
        raise NotImplementedError

class PaxosProposer(PaxosNode, Proposer):
    def __init__(self, node_id: str, network: NetworkSimulator, quorum_size: int):
        PaxosNode.__init__(self, node_id, network)
        Proposer.__init__(self)
        self.messenger = self
        self.proposer_uid = node_id
        self.quorum_size = quorum_size
        self.next_proposal_number = 1
        self.pending_promises = {}  # Track pending promises
        self.timeout = 4.0  # Reduced timeout to 4 seconds
        self.pending_accepts = {}  # Track pending accept requests
        self.current_phase = None  # Track current phase: 'prepare' or 'accept'
        self.phase_lock = threading.RLock()  # Lock to ensure phase ordering
        self.proposal_value = None  # Store the current proposal value
        self.message_queue = queue.Queue()  # Add message queue for ordered processing
        self.processing_thread = None
        self.processed_messages = set()  # Track processed messages to prevent duplicates
        self.quorum_reached = False  # Track if quorum has been reached
        self.proposal_id = None  # Track current proposal ID
        self.consensus_time = None  # Track when consensus is reached
        self.start_time = None  # Track when the proposal starts
        self.rounds = 0  # Track the number of rounds
        
    def set_proposal(self, value):
        """Set the proposal value"""
        self.proposal_value = value
        
    def prepare(self):
        """Start a new prepare phase"""
        if not self.running:
            return
            
        with self.phase_lock:
            self.rounds += 1
            self.current_phase = 'prepare'
            self.quorum_reached = False
            self.next_proposal_number += 1
            self.proposal_id = ProposalID(self.next_proposal_number, self.proposer_uid)
            if self.start_time is None:  # Only set once
                self.start_time = time.time()
            
            # Initialize base class state
            self.promises_rcvd = set()
            self.last_accepted_id = None
            
            # Send prepare messages to all acceptors
            for node_id, node in self.network.nodes.items():
                if isinstance(node, PaxosAcceptor):
                    self.network.send_message(NetworkMessage('prepare', self.node_id, node_id, self.proposal_id))
            
            # Start timeout for promises
            self.pending_promises[self.proposal_id] = {
                'count': 0,
                'start_time': time.time(),
                'received': set(),
                'value': None,
                'retry_count': 0
            }
            # Start timeout timer
            threading.Timer(self.timeout, self._check_promise_timeout, args=[self.proposal_id]).start()
        
    def _check_promise_timeout(self, proposal_id):
        if proposal_id not in self.pending_promises:
            return
            
        with self.phase_lock:
            promises = self.pending_promises[proposal_id]
            if promises['count'] < self.quorum_size:
                # Not enough promises received, try again with higher number
                promises['retry_count'] += 1
                if promises['retry_count'] < 3:  # Max 3 retries
                    self.next_proposal_number += 1
                    new_proposal_id = ProposalID(self.next_proposal_number, self.proposer_uid)
                    # Clear current phase before retrying
                    self.current_phase = None
                    self.prepare()
                else:
                    # Too many retries, give up
                    if self.network.visualizer:
                        self.network.visualizer.log_message(f"Proposer {self.node_id} failed to get quorum after {promises['retry_count']} attempts")
                    del self.pending_promises[proposal_id]
                    self.current_phase = None
        
    def send_accept(self, proposal_id, proposal_value):
        """Send accept messages to all acceptors"""
        if not self.running:
            return
        
        with self.phase_lock:
            # Only send accept if prepare phase is complete and quorum was reached
            if not self.quorum_reached:
                logger.warning(f"{self.node_id} cannot send accept - quorum not reached")
                return

                
            logger.info(f"{self.node_id} sending accept messages with value: {proposal_value}")
            self.current_phase = 'accept'
            for node_id, node in self.network.nodes.items():
                if isinstance(node, PaxosAcceptor):
                    logger.info(f"{self.node_id} sending accept to {node_id}")
                    self.network.send_message(NetworkMessage('accept', self.node_id, node_id, 
                                                            proposal_id, accepted_value=proposal_value))
            # Track accept request
            self.pending_accepts[proposal_id] = {
                'count': 0,
                'start_time': time.time(),
                'received': set(),
                'value': proposal_value,
                'retry_count': 0
            }
            # Start timeout timer
            threading.Timer(self.timeout, self._check_accept_timeout, args=[proposal_id]).start()
        
    def _check_accept_timeout(self, proposal_id):
        if proposal_id not in self.pending_accepts:
            return
        with self.phase_lock:
            accepts = self.pending_accepts[proposal_id]
            if accepts['count'] < self.quorum_size:
                accepts['retry_count'] += 1
                if accepts['retry_count'] < 3:
                    self.rounds += 1  # Increment rounds on accept retry
                    self.send_accept(proposal_id, accepts['value'])
                else:
                    # Too many retries, give up and start over with prepare phase
                    self.current_phase = None
                    self.next_proposal_number += 1
                    self.prepare()
        
    def start(self):
        """Start the node's message processing"""
        self.running = True
        self.processing_thread = threading.Thread(target=self._process_messages)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
    def _process_messages(self):
        """Process messages in order"""
        while self.running:
            try:
                msg = self.message_queue.get(timeout=0.1)
                # Create unique message identifier
                msg_id = f"{msg.sender}-{msg.msg_type}-{msg.proposal_id}"
                
                # Skip if already processed
                if msg_id in self.processed_messages:
                    logger.info(f"{self.node_id} skipping duplicate message from {msg.sender}")
                    continue
                    
                self.processed_messages.add(msg_id)
                
                if msg.msg_type == 'promise':
                    logger.info(f"{self.node_id} processing promise from {msg.sender}")
                    self.handle_promise(msg)
                elif msg.msg_type == 'accepted':
                    logger.info(f"{self.node_id} processing accepted from {msg.sender}")
                    self.handle_accepted(msg)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing message in {self.node_id}: {e}")
                
    def handle_promise(self, msg: NetworkMessage):
        """Handle a promise message"""
        with self.phase_lock:
            if msg.proposal_id in self.pending_promises and self.current_phase == 'prepare':
                promises = self.pending_promises[msg.proposal_id]
                
                # Skip if we already received a promise from this acceptor
                if msg.sender in promises['received']:
                    logger.info(f"{self.node_id} skipping duplicate promise from {msg.sender}")
                    return
                    
                promises['count'] += 1
                promises['received'].add(msg.sender)
                
                # Track highest accepted value
                if msg.accepted_value is not None:
                    if promises['value'] is None or msg.previous_id > promises['value'][0]:
                        promises['value'] = (msg.previous_id, msg.accepted_value)
                
                # Call the base class method to update state
                try:
                    # Update the base class state
                    if msg.previous_id is not None and (self.last_accepted_id is None or msg.previous_id > self.last_accepted_id):
                        self.last_accepted_id = msg.previous_id
                        if msg.accepted_value is not None:
                            self.proposed_value = msg.accepted_value
                    
                    # Add to promises received set
                    if not hasattr(self, 'promises_rcvd'):
                        self.promises_rcvd = set()
                    self.promises_rcvd.add(msg.sender)
                    
                    # Check if we have enough promises
                    if len(self.promises_rcvd) >= self.quorum_size and not self.quorum_reached:
                        logger.info(f"{self.node_id} received quorum of promises ({len(self.promises_rcvd)})")
                        self.quorum_reached = True
                        # Use highest accepted value if any, otherwise use our own
                        if promises['value'] is not None:
                            value = promises['value'][1]
                        else:
                            value = self.proposal_value
                        # Move to accept phase
                        self.send_accept(msg.proposal_id, value)
                        del self.pending_promises[msg.proposal_id]
                except Exception as e:
                    logger.error(f"Error in handle_promise: {e}")
                    return
                
    def handle_accepted(self, msg: NetworkMessage):
        """Handle an accepted message"""
        with self.phase_lock:
            if msg.proposal_id in self.pending_accepts and self.current_phase == 'accept':
                accepts = self.pending_accepts[msg.proposal_id]
                
                # Skip if we already received an accept from this acceptor
                if msg.sender in accepts['received']:
                    logger.info(f"{self.node_id} skipping duplicate accept from {msg.sender}")
                    return
                    
                accepts['count'] += 1
                accepts['received'].add(msg.sender)
                logger.info(f"{self.node_id} received accept from {msg.sender}, total accepts: {accepts['count']}")
                
                # Check if we have enough accepts
                if accepts['count'] >= self.quorum_size:
                    if self.consensus_time is None:
                        logger.info(f"{self.node_id} received quorum of accepts ({accepts['count']})")
                        self.consensus_time = time.time()
                        if self.start_time is not None:
                            consensus_duration = self.consensus_time - self.start_time
                            logger.info(f"Consensus reached in {consensus_duration:.6f} seconds")
                        if self.network.visualizer:
                            self.network.visualizer.log_message(
                                f"Proposer {self.node_id} achieved consensus with value: {accepts['value']}"
                            )
                    del self.pending_accepts[msg.proposal_id]
                    self.current_phase = None
        
    def handle_message(self, msg: NetworkMessage):
        """Queue the message for ordered processing"""
        if not self.running:
            return
        self.message_queue.put(msg)
        logger.info(f"{self.node_id} queued {msg.msg_type} message from {msg.sender}")

class PaxosAcceptor(PaxosNode, Acceptor):
    def __init__(self, node_id: str, network: NetworkSimulator):
        PaxosNode.__init__(self, node_id, network)
        Acceptor.__init__(self)
        self.messenger = self
        self.pending_responses = {}  # Track pending responses
        self.message_queue = queue.Queue()  # Add message queue for ordered processing
        self.processing_thread = None
        
    def recv_accept_request(self, proposer_uid, proposal_id, value):
        """Override and call base implementation"""
        logger.info(f"{self.node_id} received accept request from {proposer_uid} with value: {value}")
        super().recv_accept_request(proposer_uid, proposal_id, value)
        logger.info(f"{self.node_id} processed accept request from {proposer_uid}")
        
    def start(self):
        """Start the node's message processing"""
        self.running = True
        self.processing_thread = threading.Thread(target=self._process_messages)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
    def _process_messages(self):
        """Process messages in order"""
        while self.running:
            try:
                msg = self.message_queue.get(timeout=0.1)
                if msg.msg_type == 'prepare':
                    logger.info(f"{self.node_id} processing prepare message from {msg.sender}")
                    self.recv_prepare(msg.sender, msg.proposal_id)
                elif msg.msg_type == 'accept':
                    logger.info(f"{self.node_id} processing accept message from {msg.sender}")
                    self.recv_accept_request(msg.sender, msg.proposal_id, msg.accepted_value)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing message in {self.node_id}: {e}")
        
    def send_promise(self, to_uid, proposal_id, previous_id, accepted_value):
        if not self.running:
            return
        logger.info(f"{self.node_id} sending promise to {to_uid} for proposal {proposal_id}")
        msg = NetworkMessage('promise', self.node_id, to_uid, 
                           proposal_id, previous_id, accepted_value)
        self.network.send_message(msg)
        
    def send_accepted(self, proposal_id, accepted_value):
        """Send accepted messages to all learners and proposers"""
        for node_id, node in self.network.nodes.items():
            if isinstance(node, PaxosLearner) or isinstance(node, PaxosProposer):
                logger.info(f"{self.node_id} sending accepted to {node_id} for proposal {proposal_id}")
                msg = NetworkMessage(
                    'accepted',
                    sender=self.node_id,
                    receiver=node_id,
                    proposal_id=proposal_id,
                    accepted_value=accepted_value 
                )
                self.network.send_message(msg)
        
    def handle_message(self, msg: NetworkMessage):
        """Queue the message for ordered processing"""
        if not self.running:
            return
        self.message_queue.put(msg)
        logger.info(f"{self.node_id} queued {msg.msg_type} message from {msg.sender}")

class PaxosLearner(PaxosNode, Learner):
    def __init__(self, node_id: str, network: NetworkSimulator, quorum_size: int):
        PaxosNode.__init__(self, node_id, network)
        Learner.__init__(self)
        self.messenger = self
        self.quorum_size = quorum_size
        self.pending_accepted = {}  # Track pending accepted messages
        
    def on_resolution(self, proposal_id, value):
        if self.network.visualizer:
            self.network.visualizer.log_message(f"Learner {self.node_id} reached consensus: {value}")
        
    def handle_message(self, msg: NetworkMessage):
        if msg.msg_type == 'accepted':
            if msg.proposal_id not in self.pending_accepted:
                self.pending_accepted[msg.proposal_id] = {
                    'count': 0,
                    'value': msg.accepted_value,
                    'received': set()
                }
            
            self.pending_accepted[msg.proposal_id]['count'] += 1
            self.pending_accepted[msg.proposal_id]['received'].add(msg.sender)
            self.recv_accepted(msg.sender, msg.proposal_id, msg.accepted_value)
            
            # Check if we have enough accepted messages
            if self.pending_accepted[msg.proposal_id]['count'] >= self.quorum_size:
                self.on_resolution(msg.proposal_id, msg.accepted_value)
                del self.pending_accepted[msg.proposal_id]

def simulate_paxos(num_proposers: int = 2, 
                  num_acceptors: int = 2,
                  num_learners: int = 2,
                  delay_range: Tuple[float, float] = (0.0, 0.0),
                  failure_rate: float = 0.0):
    # Create network with no delay and no failures
    network = NetworkSimulator(delay_range, failure_rate)
    
    # Create nodes
    proposers = [PaxosProposer(f'P{i}', network, num_acceptors // 2 + 1) 
                for i in range(num_proposers)]
    acceptors = [PaxosAcceptor(f'A{i}', network) for i in range(num_acceptors)]
    learners = [PaxosLearner(f'L{i}', network, num_acceptors // 2 + 1) 
               for i in range(num_learners)]
    
    # Start all nodes
    for node in proposers + acceptors + learners:
        node.start()
    
    # Simulate value proposal
    logger.info("Starting Paxos simulation...")
    
    # Let first proposer propose a value
    proposers[0].set_proposal("Initial Value")
    proposers[0].start_time = time.time()  # Set start time before prepare
    proposers[0].prepare()
    
    # Wait until consensus or timeout
    start_time = time.time()
    timeout_limit = 30.0  # Increased timeout to 30 seconds
    while proposers[0].consensus_time is None and (time.time() - start_time) < timeout_limit:
        time.sleep(0.1)  # Increased sleep time to 0.1 seconds
        if proposers[0].current_phase == 'accept':
            logger.info(f"Proposer {proposers[0].node_id} in accept phase")
        if proposers[0].consensus_time is not None:
            consensus_duration = proposers[0].consensus_time - proposers[0].start_time
            logger.info(f"Consensus reached in {consensus_duration:.6f} seconds")

    consensus_before = proposers[0].consensus_time is not None
    consensus_time = proposers[0].consensus_time - proposers[0].start_time if proposers[0].consensus_time is not None else None
    rounds = proposers[0].rounds  # Get the actual number of rounds

    # Stop simulation
    network.stop()
    logger.info("Simulation complete")

    return timeout_limit, consensus_before, consensus_time, rounds, network.total_retries