import time
import threading
import random
import logging
from paxos_main.essential import Proposer, Acceptor, Learner, ProposalID

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Message class
class Message:
    def __init__(self, msg_type, sender, receiver, proposal_id, prev_id=None, value=None):
        self.msg_type = msg_type
        self.sender = sender
        self.receiver = receiver
        self.proposal_id = proposal_id
        self.prev_id = prev_id
        self.value = value

# Network simulator
class Network:
    def __init__(self, delay_range=(0.0, 0.2), drop_rate=0.0):
        self.nodes = {}
        self.delay_range = delay_range
        self.drop_rate = drop_rate

    def register(self, node):
        self.nodes[node.node_id] = node

    def send(self, msg: Message):
        if random.random() < self.drop_rate:
            logger.warning(f"[DROP] {msg.msg_type} from {msg.sender} to {msg.receiver}")
            return

        delay = random.uniform(*self.delay_range)
        threading.Timer(delay, self._deliver, args=[msg]).start()

    def _deliver(self, msg: Message):
        if msg.receiver in self.nodes:
            self.nodes[msg.receiver].receive(msg)

# Paxos nodes
class PaxosProposer(Proposer):
    def __init__(self, node_id, network, quorum):
        super().__init__()
        self.node_id = node_id
        self.network = network
        self.quorum_size = quorum
        self.proposer_uid = node_id
        self.messenger = self
        network.register(self)

    def send_prepare(self, proposal_id):
        for node in self.network.nodes.values():
            if isinstance(node, PaxosAcceptor):
                msg = Message('prepare', self.node_id, node.node_id, proposal_id)
                self.network.send(msg)

    def send_accept(self, proposal_id, proposal_value):
        for node in self.network.nodes.values():
            if isinstance(node, PaxosAcceptor):
                msg = Message('accept', self.node_id, node.node_id, proposal_id, value=proposal_value)
                self.network.send(msg)

    def receive(self, msg: Message):
        if msg.msg_type == 'promise':
            self.recv_promise(msg.sender, msg.proposal_id, msg.prev_id, msg.value)

class PaxosAcceptor(Acceptor):
    def __init__(self, node_id, network):
        super().__init__()
        self.node_id = node_id
        self.network = network
        self.messenger = self
        network.register(self)

    def send_promise(self, to_uid, proposal_id, prev_id, value):
        msg = Message('promise', self.node_id, to_uid, proposal_id, prev_id, value)
        self.network.send(msg)

    def send_accepted(self, proposal_id, accepted_value):
        for node in self.network.nodes.values():
            if isinstance(node, PaxosLearner):
                msg = Message('accepted', self.node_id, node.node_id, proposal_id, value=accepted_value)
                self.network.send(msg)

    def receive(self, msg: Message):
        if msg.msg_type == 'prepare':
            self.recv_prepare(msg.sender, msg.proposal_id)
        elif msg.msg_type == 'accept':
            self.recv_accept_request(msg.sender, msg.proposal_id, msg.value)

class PaxosLearner(Learner):
    def __init__(self, node_id, network, quorum):
        super().__init__()
        self.node_id = node_id
        self.network = network
        self.quorum_size = quorum
        self.messenger = self
        network.register(self)

    def on_resolution(self, proposal_id, value):
        logger.info(f"[CONSENSUS] Learner {self.node_id} learned value: {value} (proposal {proposal_id})")

    def receive(self, msg: Message):
        if msg.msg_type == 'accepted':
            self.recv_accepted(msg.sender, msg.proposal_id, msg.value)

# Simulation

def simulate():
    net = Network(delay_range=(0.1, 0.3), drop_rate=0.1)

    proposer = PaxosProposer('P1', net, quorum=2)
    acceptors = [PaxosAcceptor(f'A{i}', net) for i in range(3)]
    learners = [PaxosLearner(f'L{i}', net, quorum=2) for i in range(2)]

    proposer.set_proposal("value42")
    proposer.prepare()

    time.sleep(5)

if __name__ == "__main__":
    simulate()
