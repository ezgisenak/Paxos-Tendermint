from paxos_main.essential import Proposer, Acceptor, Learner, ProposalID
import threading
import time

class SimpleMessenger:
    def __init__(self):
        self.messages = []
        self.lock = threading.Lock()
    
    def send_prepare(self, proposal_id):
        with self.lock:
            self.messages.append(('prepare', proposal_id))
    
    def send_promise(self, to_uid, proposal_id, previous_id, accepted_value):
        with self.lock:
            self.messages.append(('promise', to_uid, proposal_id, previous_id, accepted_value))
    
    def send_accept(self, proposal_id, proposal_value):
        with self.lock:
            self.messages.append(('accept', proposal_id, proposal_value))
    
    def send_accepted(self, proposal_id, accepted_value):
        with self.lock:
            self.messages.append(('accepted', proposal_id, accepted_value))
    
    def on_resolution(self, proposal_id, value):
        with self.lock:
            self.messages.append(('resolution', proposal_id, value))
            print(f"Consensus reached! Value: {value}")

def main():
    # Create messengers for each node
    proposer_messenger = SimpleMessenger()
    acceptor_messenger = SimpleMessenger()
    learner_messenger = SimpleMessenger()
    
    # Create nodes
    proposer = Proposer()
    proposer.messenger = proposer_messenger
    proposer.proposer_uid = 'P1'
    proposer.quorum_size = 2  # Need 2 acceptors for quorum
    
    acceptor = Acceptor()
    acceptor.messenger = acceptor_messenger
    acceptor.quorum_size = 2
    
    learner = Learner()
    learner.messenger = learner_messenger
    learner.quorum_size = 2
    
    # Set up the network (in a real implementation, this would be distributed)
    proposer_messenger.messages = acceptor_messenger.messages
    acceptor_messenger.messages = proposer_messenger.messages
    learner_messenger.messages = acceptor_messenger.messages
    
    # Propose a value
    print("Starting Paxos consensus...")
    proposer.set_proposal("Hello, Paxos!")
    proposer.prepare()
    
    # Wait for consensus
    time.sleep(1)  # Give time for messages to be processed
    
    # Print the messages exchanged
    print("\nMessages exchanged:")
    for msg in proposer_messenger.messages:
        print(msg)

if __name__ == "__main__":
    main() 