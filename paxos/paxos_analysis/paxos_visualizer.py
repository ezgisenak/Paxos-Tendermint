import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
import random
import queue
from typing import Dict, List, Tuple, Optional
import logging
from paxos_main.essential import Proposer, Acceptor, Learner, ProposalID
from paxos_simulation import NetworkMessage, NetworkSimulator, PaxosNode, PaxosProposer, PaxosAcceptor, PaxosLearner

class PaxosVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Paxos Algorithm Visualizer")
        
        # Create main frames
        self.network_frame = ttk.Frame(root)
        self.control_frame = ttk.Frame(root)
        self.log_frame = ttk.Frame(root)
        
        # Layout frames
        self.network_frame.grid(row=0, column=0, padx=10, pady=10)
        self.control_frame.grid(row=0, column=1, padx=10, pady=10)
        self.log_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10)
        
        # Create network canvas
        self.canvas = tk.Canvas(self.network_frame, width=800, height=400, bg='white')
        self.canvas.pack()
        
        # Create control panel
        self.create_control_panel()
        
        # Create log area
        self.log_area = scrolledtext.ScrolledText(self.log_frame, width=100, height=10)
        self.log_area.pack()
        
        # Initialize simulation
        self.simulation = None
        self.running = False
        
        # Node positions
        self.node_positions = {}
        self.message_lines = []
        
    def create_control_panel(self):
        # Node configuration
        ttk.Label(self.control_frame, text="Node Configuration").grid(row=0, column=0, columnspan=2, pady=5)
        
        ttk.Label(self.control_frame, text="Proposers:").grid(row=1, column=0)
        self.proposer_count = ttk.Spinbox(self.control_frame, from_=1, to=5, width=5)
        self.proposer_count.set(2)
        self.proposer_count.grid(row=1, column=1)
        
        ttk.Label(self.control_frame, text="Acceptors:").grid(row=2, column=0)
        self.acceptor_count = ttk.Spinbox(self.control_frame, from_=3, to=7, width=5)
        self.acceptor_count.set(3)
        self.acceptor_count.grid(row=2, column=1)
        
        ttk.Label(self.control_frame, text="Learners:").grid(row=3, column=0)
        self.learner_count = ttk.Spinbox(self.control_frame, from_=1, to=5, width=5)
        self.learner_count.set(2)
        self.learner_count.grid(row=3, column=1)
        
        # Network parameters
        ttk.Label(self.control_frame, text="\nNetwork Parameters").grid(row=4, column=0, columnspan=2, pady=5)
        
        ttk.Label(self.control_frame, text="Min Delay (s):").grid(row=5, column=0)
        self.min_delay = ttk.Spinbox(self.control_frame, from_=0.0, to=1.0, increment=0.1, width=5)
        self.min_delay.set(0.1)
        self.min_delay.grid(row=5, column=1)
        
        ttk.Label(self.control_frame, text="Max Delay (s):").grid(row=6, column=0)
        self.max_delay = ttk.Spinbox(self.control_frame, from_=0.0, to=2.0, increment=0.1, width=5)
        self.max_delay.set(0.5)
        self.max_delay.grid(row=6, column=1)
        
        ttk.Label(self.control_frame, text="Failure Rate:").grid(row=7, column=0)
        self.failure_rate = ttk.Spinbox(self.control_frame, from_=0.0, to=1.0, increment=0.1, width=5)
        self.failure_rate.set(0.1)
        self.failure_rate.grid(row=7, column=1)
        
        # Control buttons
        ttk.Button(self.control_frame, text="Start Simulation", 
                  command=self.start_simulation).grid(row=8, column=0, columnspan=2, pady=10)
        ttk.Button(self.control_frame, text="Stop Simulation", 
                  command=self.stop_simulation).grid(row=9, column=0, columnspan=2)
        
    def draw_network(self, proposers, acceptors, learners):
        self.canvas.delete("all")
        self.node_positions.clear()
        self.message_lines.clear()
        
        # Draw proposers
        for i, proposer in enumerate(proposers):
            x = 100
            y = 100 + i * 80
            self.node_positions[proposer.node_id] = (x, y)
            self.canvas.create_oval(x-20, y-20, x+20, y+20, fill='blue')
            self.canvas.create_text(x, y, text=f"P{i}")
            
        # Draw acceptors
        for i, acceptor in enumerate(acceptors):
            x = 400
            y = 100 + i * 80
            self.node_positions[acceptor.node_id] = (x, y)
            self.canvas.create_oval(x-20, y-20, x+20, y+20, fill='green')
            self.canvas.create_text(x, y, text=f"A{i}")
            
        # Draw learners
        for i, learner in enumerate(learners):
            x = 700
            y = 100 + i * 80
            self.node_positions[learner.node_id] = (x, y)
            self.canvas.create_oval(x-20, y-20, x+20, y+20, fill='red')
            self.canvas.create_text(x, y, text=f"L{i}")
            
    def draw_message(self, msg: NetworkMessage):
        if msg.sender not in self.node_positions or msg.receiver not in self.node_positions:
            return
            
        start_pos = self.node_positions[msg.sender]
        end_pos = self.node_positions[msg.receiver]
        
        # Create animated line
        line = self.canvas.create_line(start_pos[0], start_pos[1], 
                                     start_pos[0], start_pos[1],
                                     arrow=tk.LAST, fill='black')
        self.message_lines.append(line)
        
        # Animate the line
        def animate_line():
            for i in range(10):
                x1, y1 = start_pos
                x2, y2 = end_pos
                progress = (i + 1) / 10
                current_x = x1 + (x2 - x1) * progress
                current_y = y1 + (y2 - y1) * progress
                self.canvas.coords(line, x1, y1, current_x, current_y)
                self.root.update()
                time.sleep(0.05)
            
            # Remove the line after animation
            self.canvas.after(1000, lambda: self.canvas.delete(line))
            self.message_lines.remove(line)
            
        threading.Thread(target=animate_line, daemon=True).start()
        
    def log_message(self, msg: str):
        self.log_area.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {msg}\n")
        self.log_area.see(tk.END)
        
    def start_simulation(self):
        if self.running:
            return
            
        self.running = True
        self.log_area.delete(1.0, tk.END)
        
        # Get parameters from controls
        num_proposers = int(self.proposer_count.get())
        num_acceptors = int(self.acceptor_count.get())
        num_learners = int(self.learner_count.get())
        delay_range = (float(self.min_delay.get()), float(self.max_delay.get()))
        failure_rate = float(self.failure_rate.get())
        
        # Create and start simulation
        self.simulation = PaxosSimulation(self, num_proposers, num_acceptors, num_learners,
                                        delay_range, failure_rate)
        self.simulation.start()
        
    def stop_simulation(self):
        if self.simulation:
            self.simulation.stop()
        self.running = False

class PaxosSimulation:
    def __init__(self, visualizer: PaxosVisualizer, num_proposers: int, num_acceptors: int,
                 num_learners: int, delay_range: Tuple[float, float], failure_rate: float):
        self.visualizer = visualizer
        self.network = NetworkSimulator(delay_range, failure_rate)
        self.running = True
        
        # Create nodes
        self.proposers = [PaxosProposer(f'P{i}', self.network, num_acceptors // 2 + 1) 
                         for i in range(num_proposers)]
        self.acceptors = [PaxosAcceptor(f'A{i}', self.network) 
                         for i in range(num_acceptors)]
        self.learners = [PaxosLearner(f'L{i}', self.network, num_acceptors // 2 + 1) 
                        for i in range(num_learners)]
        
        # Draw initial network
        self.visualizer.draw_network(self.proposers, self.acceptors, self.learners)
        
    def start(self):
        # Start all nodes
        for node in self.proposers + self.acceptors + self.learners:
            node.start()
            
        # Start simulation thread
        threading.Thread(target=self._run_simulation, daemon=True).start()
        
    def stop(self):
        self.running = False
        self.network.stop()
        
    def _run_simulation(self):
        self.visualizer.log_message("Starting Paxos simulation...")
        
        # Let first proposer propose a value
        self.proposers[0].set_proposal("Initial Value")
        self.proposers[0].prepare()
        self.visualizer.log_message("Proposer P0 proposed value: 'Initial Value'")
        
        # Simulate leader crash after some time
        time.sleep(2)
        self.visualizer.log_message("Simulating leader crash (P0)...")
        self.proposers[0].running = False
        
        # Let second proposer take over
        time.sleep(1)
        if len(self.proposers) > 1:
            self.proposers[1].set_proposal("New Value After Crash")
            self.proposers[1].prepare()
            self.visualizer.log_message("Proposer P1 proposed value: 'New Value After Crash'")
        
        # Let simulation run for a while
        time.sleep(5)
        
        # Stop simulation
        self.stop()
        self.visualizer.log_message("Simulation complete")

if __name__ == "__main__":
    root = tk.Tk()
    app = PaxosVisualizer(root)
    root.mainloop() 