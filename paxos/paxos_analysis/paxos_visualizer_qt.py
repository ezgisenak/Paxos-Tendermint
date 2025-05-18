import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QSpinBox, QPushButton, QTextEdit, QLineEdit)
from PyQt6.QtCore import Qt, QTimer, QPoint, QThread, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen
import threading
import time
import random
import queue
from typing import Dict, List, Tuple, Optional
from paxos.essential import Proposer, Acceptor, Learner, ProposalID
from paxos_simulation import NetworkMessage, NetworkSimulator, PaxosNode, PaxosProposer, PaxosAcceptor, PaxosLearner
import math

class SimulationThread(QThread):
    message_signal = pyqtSignal(str)  # For logging messages
    simulation_complete = pyqtSignal()  # For signaling completion
    
    def __init__(self, simulation):
        super().__init__()
        self.simulation = simulation
        
    def run(self):
        self.message_signal.emit("Starting Paxos simulation...")
        
        # Phase 1a: First proposer sends prepare
        self.message_signal.emit("Phase 1a: P0 sending prepare messages")
        self.simulation.proposers[0].set_proposal("Initial Value")
        self.simulation.proposers[0].prepare()
        time.sleep(2)  # Wait for messages to be processed
        
        # Phase 1b: Acceptors respond with promises
        self.message_signal.emit("Phase 1b: Acceptors sending promise messages")
        for acceptor in self.simulation.acceptors:
            acceptor.recv_prepare("P0", self.simulation.proposers[0].proposal_id)
        time.sleep(2)
        
        # Phase 2a: Proposer sends accept
        self.message_signal.emit("Phase 2a: P0 sending accept messages")
        self.simulation.proposers[0].send_accept(self.simulation.proposers[0].proposal_id, "Initial Value")
        time.sleep(2)
        
        # Phase 2b: Acceptors accept and notify learners
        self.message_signal.emit("Phase 2b: Acceptors accepting and notifying learners")
        for acceptor in self.simulation.acceptors:
            acceptor.recv_accept_request("P0", self.simulation.proposers[0].proposal_id, "Initial Value")
        time.sleep(2)
        
        # Simulate leader crash
        self.message_signal.emit("Simulating leader crash (P0)...")
        self.simulation.proposers[0].running = False
        time.sleep(2)
        
        # Phase 1a: Second proposer sends prepare with higher number
        if len(self.simulation.proposers) > 1:
            self.message_signal.emit("Phase 1a: P1 sending prepare messages with higher number")
            self.simulation.proposers[1].set_proposal("New Value After Crash")
            self.simulation.proposers[1].prepare()
            time.sleep(2)
            
            # Phase 1b: Acceptors respond with promises
            self.message_signal.emit("Phase 1b: Acceptors sending promise messages to P1")
            for acceptor in self.simulation.acceptors:
                acceptor.recv_prepare("P1", self.simulation.proposers[1].proposal_id)
            time.sleep(2)
            
            # Phase 2a: Send accept request
            self.message_signal.emit("Phase 2a: P1 sending accept messages")
            self.simulation.proposers[1].send_accept(self.simulation.proposers[1].proposal_id, 
                                                   "New Value After Crash")
            time.sleep(2)
            
            # Phase 2b: Acceptors accept and notify learners
            self.message_signal.emit("Phase 2b: Acceptors accepting and notifying learners")
            for acceptor in self.simulation.acceptors:
                acceptor.recv_accept_request("P1", self.simulation.proposers[1].proposal_id, "New Value After Crash")
            time.sleep(2)
            
            # Check if consensus was reached
            for learner in self.simulation.learners:
                if learner.final_value is not None:
                    self.message_signal.emit(f"Consensus reached! Value: {learner.final_value}")
        
        # Let simulation run for a while to see all messages
        time.sleep(2)
        
        # Stop simulation
        self.simulation.stop()
        self.message_signal.emit("Simulation complete")
        self.simulation_complete.emit()

class NetworkCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.node_positions = {}
        self.message_lines = []
        self.crashed_nodes = set()
        self.crash_animations = {}
        self.visualizer = parent  # Store reference to parent visualizer
        self.setMinimumSize(800, 600)
        
        # Create timer for message animation
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update)
        self.animation_timer.start(16)  # 60 FPS
        
        # Define message colors and descriptions
        self.message_types = {
            'prepare': (QColor(255, 165, 0), "Prepare: Request to propose a value"),
            'promise': (QColor(0, 128, 255), "Promise: Accept to consider proposal"),
            'accept': (QColor(255, 0, 255), "Accept: Proposal with value"),
            'accepted': (QColor(0, 255, 255), "Accepted: Value has been accepted")
        }
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate node positions based on canvas size
        self.update_node_positions()
        
        # Draw legend
        self.draw_legend(painter)
        
        # Draw nodes
        for node_id, pos in self.node_positions.items():
            if node_id.startswith('P'):
                color = QColor(0, 0, 255)  # Blue for proposers
                role = "Proposer"
            elif node_id.startswith('A'):
                color = QColor(0, 255, 0)  # Green for acceptors
                role = "Acceptor"
            else:
                color = QColor(255, 0, 0)  # Red for learners
                role = "Learner"
                
            # Draw node circle
            if node_id in self.crashed_nodes:
                # Animate crash effect
                crash_progress = self.crash_animations.get(node_id, 1.0)
                
                # Draw multiple explosion rings
                if crash_progress < 1.0:
                    for i in range(3):
                        alpha = int(255 * (1 - crash_progress) * (1 - i/3))
                        radius = int(25 + (50 * (1 - crash_progress) * (1 + i/2)))
                        painter.setPen(QPen(QColor(255, 0, 0, alpha), 3))
                        painter.drawEllipse(pos.x() - radius, pos.y() - radius,
                                          radius * 2, radius * 2)
                
                # Draw crashed node with pulsing effect
                pulse = (math.sin(time.time() * 5) + 1) / 2  # 5Hz pulse
                gray_value = int(128 + 64 * pulse)
                painter.setBrush(QColor(gray_value, gray_value, gray_value))
                painter.setPen(QPen(Qt.GlobalColor.black, 2))
                painter.drawEllipse(pos.x() - 25, pos.y() - 25, 50, 50)
                
                # Draw pulsing X
                x_color = QColor(255, int(128 * (1 - pulse)), int(128 * (1 - pulse)))
                painter.setPen(QPen(x_color, 3))
                painter.drawLine(pos.x() - 15, pos.y() - 15, pos.x() + 15, pos.y() + 15)
                painter.drawLine(pos.x() - 15, pos.y() + 15, pos.x() + 15, pos.y() - 15)
                
                # Draw "CRASHED" label
                font = painter.font()
                font.setBold(True)
                font.setPointSize(12)
                painter.setFont(font)
                painter.setPen(QPen(Qt.GlobalColor.red, 2))
                painter.drawText(QPoint(pos.x() - 30, pos.y() - 40), "CRASHED")
            else:
                painter.setBrush(color)
                painter.setPen(QPen(Qt.GlobalColor.black, 2))
                painter.drawEllipse(pos.x() - 25, pos.y() - 25, 50, 50)
            
            # Draw node ID and role
            painter.setPen(Qt.GlobalColor.black)
            font = painter.font()
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(QPoint(pos.x() - 15, pos.y() + 5), node_id)
            font.setBold(False)
            painter.setFont(font)
            painter.drawText(QPoint(pos.x() - 25, pos.y() + 40), role)
            
        # Draw message lines with enhanced visualization for dropped messages
        current_time = time.time()
        remaining_lines = []
        for msg in self.message_lines:
            start_pos, end_pos, msg_type, start_time, duration, dropped, msg_id = msg
            elapsed = current_time - start_time
            if elapsed < duration:
                progress = elapsed / duration
                current_x = start_pos.x() + (end_pos.x() - start_pos.x()) * progress
                current_y = start_pos.y() + (end_pos.y() - start_pos.y()) * progress
                current_pos = QPoint(int(current_x), int(current_y))
                
                color = self.message_types[msg_type][0]
                
                if dropped:
                    # Draw dropped message visualization
                    pen = QPen(QColor(255, 0, 0), 3, Qt.PenStyle.DashLine)
                    painter.setPen(pen)
                    painter.drawLine(start_pos, current_pos)
                    
                    # Draw "DROPPED" text
                    mid_x = (start_pos.x() + current_x) / 2
                    mid_y = (start_pos.y() + current_y) / 2 - 15
                    font = painter.font()
                    font.setBold(True)
                    font.setPointSize(10)
                    painter.setFont(font)
                    
                    # Draw text without shadow
                    painter.setPen(QPen(Qt.GlobalColor.red, 2))
                    painter.drawText(QPoint(int(mid_x) - 30, int(mid_y)), "DROPPED")
                    
                    # Draw explosion effect at the drop point
                    explosion_radius = int(10 + (20 * (1 - progress)))
                    painter.setPen(QPen(QColor(255, 0, 0, int(255 * (1 - progress))), 2))
                    painter.drawEllipse(int(current_x) - explosion_radius, int(current_y) - explosion_radius,
                                      explosion_radius * 2, explosion_radius * 2)
                else:
                    pen = QPen(color, 3)
                    painter.setPen(pen)
                    painter.drawLine(start_pos, current_pos)
                    
                    if progress > 0.1:
                        self.draw_arrow_head(painter, current_pos, start_pos, end_pos, color)
                    
                    # Draw message type label
                    mid_x = (start_pos.x() + current_x) / 2
                    mid_y = (start_pos.y() + current_y) / 2 - 15
                    painter.setPen(Qt.GlobalColor.black)
                    font = painter.font()
                    font.setBold(True)
                    painter.setFont(font)
                    painter.drawText(QPoint(int(mid_x), int(mid_y)), msg_type.upper())
                
                remaining_lines.append(msg)

        self.message_lines = remaining_lines
        
        # Update crash animations
        current_time = time.time()
        for node_id in list(self.crash_animations.keys()):
            if current_time - self.crash_animations[node_id] > 2.0:  # 2 second animation
                del self.crash_animations[node_id]
            else:
                self.crash_animations[node_id] = current_time - self.crash_animations[node_id]
    
    def update_node_positions(self):
        width = self.width()
        height = self.height()
        margin = 100  # Margin from edges
        
        # Count nodes of each type
        num_proposers = len([n for n in self.node_positions.keys() if n.startswith('P')])
        num_acceptors = len([n for n in self.node_positions.keys() if n.startswith('A')])
        num_learners = len([n for n in self.node_positions.keys() if n.startswith('L')])
        
        # Calculate vertical spacing
        max_nodes = max(num_proposers, num_acceptors, num_learners)
        v_spacing = (height - 2 * margin) // (max_nodes - 1) if max_nodes > 1 else height // 2
        
        # Update positions
        for node_id in self.node_positions.keys():
            if node_id.startswith('P'):
                idx = int(node_id[1])
                x = int(margin)
                y = int(margin + (v_spacing * idx))
            elif node_id.startswith('A'):
                idx = int(node_id[1])
                x = int(width // 2)
                y = int(margin + (v_spacing * idx))
            else:  # Learners
                idx = int(node_id[1])
                x = int(width - margin)
                y = int(margin + (v_spacing * idx))
            
            self.node_positions[node_id] = QPoint(x, y)
    
    def draw_arrow_head(self, painter, tip, start, end, color):
        # Calculate arrow direction
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        angle = math.atan2(dy, dx)
        
        # Arrow head parameters
        arrow_size = 10
        arrow_angle = math.pi / 6  # 30 degrees
        
        # Calculate arrow head points
        p1 = QPoint(
            int(tip.x() - arrow_size * math.cos(angle - arrow_angle)),
            int(tip.y() - arrow_size * math.sin(angle - arrow_angle))
        )
        p2 = QPoint(
            int(tip.x() - arrow_size * math.cos(angle + arrow_angle)),
            int(tip.y() - arrow_size * math.sin(angle + arrow_angle))
        )
        
        # Draw arrow head
        painter.setBrush(color)
        points = [tip, p1, p2]
        painter.drawPolygon(points)
    
    def draw_legend(self, painter):
        # Draw legend box
        legend_x = 20
        legend_y = self.height() - 160  # Move it near the bottom!
        legend_width = 250  # Increased width
        legend_height = 150  # Increased height
        
        painter.setBrush(QColor(255, 255, 255, 230))  # More opaque background
        painter.setPen(QPen(Qt.GlobalColor.black, 2))  # Thicker border
        painter.drawRect(legend_x, legend_y, legend_width, legend_height)
        
        # Draw legend title
        font = painter.font()
        font.setBold(True)
        font.setPointSize(10)  # Increased font size
        painter.setFont(font)
        painter.drawText(legend_x + 10, legend_y + 25, "Message Types:")
        
        # Draw legend items
        font.setBold(False)
        font.setPointSize(9)  # Slightly smaller for items
        painter.setFont(font)
        y_offset = 45
        for msg_type, (color, description) in self.message_types.items():
            # Draw color box
            painter.setBrush(color)
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.drawRect(legend_x + 10, legend_y + y_offset, 20, 20)  # Larger color boxes
            
            # Draw description
            painter.drawText(legend_x + 35, legend_y + y_offset + 15, description)
            y_offset += 25  # Increased spacing between items
    
    def add_node(self, node_id: str, pos: QPoint):
        self.node_positions[node_id] = pos
        self.update()

    def add_message(self, start: QPoint, end: QPoint, msg_type: str, dropped=False):
        """Add a message to the visualization"""
        duration = 2.0
        # If this is a dropped message, remove any existing solid message for the same tuple
        if dropped:
            self.message_lines = [m for m in self.message_lines
                                  if not (m[0] == start and m[1] == end and m[2] == msg_type and not m[5])]
        else:
            # If a dropped version exists, skip adding the solid message
            for m in self.message_lines:
                if m[0] == start and m[1] == end and m[2] == msg_type and m[5]:
                    return
        # Only add the message if it's not already being animated
        msg_id = f"{start.x()}-{start.y()}-{end.x()}-{end.y()}-{msg_type}-{dropped}"
        if not any(m[6] == msg_id for m in self.message_lines):
            self.message_lines.append((start, end, msg_type, time.time(), duration, dropped, msg_id))
            if self.visualizer:
                if dropped:
                    self.visualizer.log_message(f"Message dropped: {msg_type}")
                else:
                    self.visualizer.log_message(f"Message sent: {msg_type}")
        
    def mark_node_crashed(self, node_id: str):
        """Mark a node as crashed in the visualization with animation"""
        print(f"DEBUG: Marking node {node_id} as crashed")  # Debug log
        self.crashed_nodes.add(node_id)
        self.crash_animations[node_id] = time.time()
        self.update()
        print(f"DEBUG: Node {node_id} marked as crashed, crashed_nodes: {self.crashed_nodes}")  # Debug log

    def reset_crashed_nodes(self):
        """Reset all crashed nodes"""
        self.crashed_nodes.clear()
        self.crash_animations.clear()
        self.update()

class PaxosVisualizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Paxos Algorithm Visualizer")
        self.setMinimumSize(1200, 800)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Create network canvas with self as parent
        self.canvas = NetworkCanvas(self)  # Pass self as parent
        layout.addWidget(self.canvas, stretch=2)
        
        # Create right panel for controls and log
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(15)
        layout.addWidget(right_panel, stretch=1)
        
        # Node configuration
        right_layout.addWidget(QLabel("Node Configuration"))
        
        # Proposers
        proposer_layout = QHBoxLayout()
        proposer_layout.addWidget(QLabel("Proposers:"))
        self.proposer_count = QSpinBox()
        self.proposer_count.setRange(1, 5)
        self.proposer_count.setValue(2)
        proposer_layout.addWidget(self.proposer_count)
        right_layout.addLayout(proposer_layout)
        
        # Acceptors
        acceptor_layout = QHBoxLayout()
        acceptor_layout.addWidget(QLabel("Acceptors:"))
        self.acceptor_count = QSpinBox()
        self.acceptor_count.setRange(3, 7)
        self.acceptor_count.setValue(3)
        acceptor_layout.addWidget(self.acceptor_count)
        right_layout.addLayout(acceptor_layout)
        
        # Learners
        learner_layout = QHBoxLayout()
        learner_layout.addWidget(QLabel("Learners:"))
        self.learner_count = QSpinBox()
        self.learner_count.setRange(1, 5)
        self.learner_count.setValue(2)
        learner_layout.addWidget(self.learner_count)
        right_layout.addLayout(learner_layout)
        
        # Network parameters
        right_layout.addWidget(QLabel("\nNetwork Parameters"))
        
        # Min Delay
        min_delay_layout = QHBoxLayout()
        min_delay_layout.addWidget(QLabel("Min Delay (s):"))
        self.min_delay = QSpinBox()
        self.min_delay.setRange(0, 100)
        self.min_delay.setValue(10)
        min_delay_layout.addWidget(self.min_delay)
        right_layout.addLayout(min_delay_layout)
        
        # Max Delay
        max_delay_layout = QHBoxLayout()
        max_delay_layout.addWidget(QLabel("Max Delay (s):"))
        self.max_delay = QSpinBox()
        self.max_delay.setRange(0, 200)
        self.max_delay.setValue(50)
        max_delay_layout.addWidget(self.max_delay)
        right_layout.addLayout(max_delay_layout)
        
        # Failure Rate (renamed to Message Drop Rate)
        failure_rate_layout = QHBoxLayout()
        failure_rate_layout.addWidget(QLabel("Message Drop Rate (%):"))
        self.failure_rate = QSpinBox()
        self.failure_rate.setRange(0, 100)
        self.failure_rate.setValue(30)  # Default drop rate
        failure_rate_layout.addWidget(self.failure_rate)
        right_layout.addLayout(failure_rate_layout)
        
        # Crash Controls
        right_layout.addWidget(QLabel("\nCrash Controls"))
        crash_layout = QHBoxLayout()
        crash_layout.addWidget(QLabel("Crash Node ID:"))
        self.crash_node_id = QLineEdit()
        crash_layout.addWidget(self.crash_node_id)
        self.crash_button = QPushButton("Crash Node")
        self.crash_button.clicked.connect(self.crash_node)
        crash_layout.addWidget(self.crash_button)
        right_layout.addLayout(crash_layout)
        
        # Control buttons
        self.start_button = QPushButton("Start Simulation")
        self.start_button.clicked.connect(self.start_simulation)
        right_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop Simulation")
        self.stop_button.clicked.connect(self.stop_simulation)
        self.stop_button.setEnabled(False)
        right_layout.addWidget(self.stop_button)
        
        # Create log area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        right_layout.addWidget(self.log_area)
        
        # Initialize simulation
        self.simulation = None
        self.running = False
        
    def start_simulation(self):
        if self.running:
            return
            
        self.running = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.log_area.clear()
        
        # Get parameters from controls
        num_proposers = self.proposer_count.value()
        num_acceptors = self.acceptor_count.value()
        num_learners = self.learner_count.value()
        delay_range = (self.min_delay.value() / 100, self.max_delay.value() / 100)
        failure_rate = self.failure_rate.value() / 100
        
        # Create and start simulation
        self.simulation = PaxosSimulation(self, num_proposers, num_acceptors, num_learners,
                                        delay_range, failure_rate)
                                        
        self.canvas.update_node_positions()   # <-- Force update before anything starts
        # Create and start simulation thread
        self.sim_thread = SimulationThread(self.simulation)
        self.sim_thread.message_signal.connect(self.log_message)
        self.sim_thread.simulation_complete.connect(self.on_simulation_complete)
        self.sim_thread.start()
        
    def on_simulation_complete(self):
        self.running = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
    def stop_simulation(self):
        if self.simulation:
            self.simulation.stop()
        if hasattr(self, 'sim_thread'):
            self.sim_thread.terminate()
            self.sim_thread.wait()
        self.running = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
    def log_message(self, msg: str):
        self.log_area.append(f"{time.strftime('%H:%M:%S')} - {msg}")
        
    def draw_network(self, proposers, acceptors, learners):
        self.canvas.node_positions.clear()
        
        # Draw proposers
        for i, proposer in enumerate(proposers):
            pos = QPoint(100, 100 + i * 80)
            self.canvas.add_node(proposer.node_id, pos)
            
        # Draw acceptors
        for i, acceptor in enumerate(acceptors):
            pos = QPoint(400, 100 + i * 80)
            self.canvas.add_node(acceptor.node_id, pos)
            
        # Draw learners
        for i, learner in enumerate(learners):
            pos = QPoint(700, 100 + i * 80)
            self.canvas.add_node(learner.node_id, pos)
            
    def draw_message(self, msg: NetworkMessage):
        if msg.sender not in self.canvas.node_positions or (msg.receiver != 'broadcast' and msg.receiver not in self.canvas.node_positions):
            return
            
        start_pos = self.canvas.node_positions[msg.sender]
        
        # Handle broadcast messages
        if msg.receiver == 'broadcast':
            if msg.msg_type == 'prepare':
                receivers = [node_id for node_id in self.canvas.node_positions if node_id.startswith('A')]
            elif msg.msg_type == 'accept':
                receivers = [node_id for node_id in self.canvas.node_positions if node_id.startswith('A')]
            elif msg.msg_type == 'accepted':
                receivers = [node_id for node_id in self.canvas.node_positions if node_id.startswith('L')]
            else:
                return
                
            for receiver in receivers:
                end_pos = self.canvas.node_positions[receiver]
                self.canvas.add_message(start_pos, end_pos, msg.msg_type, dropped=msg.dropped)
        else:
            end_pos = self.canvas.node_positions[msg.receiver]
            self.canvas.add_message(start_pos, end_pos, msg.msg_type, dropped=msg.dropped)

    def crash_node(self):
        """Handler to manually crash a node by ID"""
        node_id = self.crash_node_id.text().strip()
        if not self.simulation:
            return
        # Find and crash the node
        all_nodes = self.simulation.proposers + self.simulation.acceptors + self.simulation.learners
        for node in all_nodes:
            if node.node_id == node_id and node.running:
                node.running = False
                self.canvas.mark_node_crashed(node_id)
                self.log_message(f"Node {node_id} manually crashed")
                return
        self.log_message(f"Invalid or already crashed node ID: {node_id}")

class PaxosSimulation:
    def __init__(self, visualizer: PaxosVisualizer, num_proposers: int, num_acceptors: int,
                 num_learners: int, delay_range: Tuple[float, float], failure_rate: float):
        self.visualizer = visualizer
        self.network = NetworkSimulator(delay_range, failure_rate, visualizer)
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
        self.visualizer.canvas.reset_crashed_nodes()
        
    def _run_simulation(self):
        self.visualizer.log_message("Starting Paxos simulation...")
        
        # Phase 1a: First proposer sends prepare
        self.visualizer.log_message("Phase 1a: P0 sending prepare messages")
        self.proposers[0].set_proposal("Initial Value")
        self.proposers[0].prepare()
        time.sleep(2)  # Wait for messages to be processed
        
        # Phase 1b: Acceptors respond with promises
        self.visualizer.log_message("Phase 1b: Acceptors sending promise messages")
        for acceptor in self.acceptors:
            acceptor.recv_prepare("P0", self.proposers[0].proposal_id)
        time.sleep(2)
        
        # Phase 2a: Proposer sends accept
        self.visualizer.log_message("Phase 2a: P0 sending accept messages")
        self.proposers[0].send_accept(self.proposers[0].proposal_id, "Initial Value")
        time.sleep(2)
        
        # Phase 2b: Acceptors accept and notify learners
        self.visualizer.log_message("Phase 2b: Acceptors accepting and notifying learners")
        for acceptor in self.acceptors:
            acceptor.recv_accept_request("P0", self.proposers[0].proposal_id, "Initial Value")
        time.sleep(2)
        
        # Simulate leader crash with debug logging
        self.visualizer.log_message("Simulating leader crash (P0)...")
        print("DEBUG: About to crash P0")  # Debug log
        self.proposers[0].running = False
        self.visualizer.canvas.mark_node_crashed("P0")
        print("DEBUG: P0 crashed and marked")  # Debug log
        time.sleep(2)
        
        # Simulate some acceptor crashes with debug logging
        if len(self.acceptors) > 1:
            self.visualizer.log_message("Simulating acceptor crashes (A0, A1)...")
            print("DEBUG: About to crash A0 and A1")  # Debug log
            self.acceptors[0].running = False
            self.acceptors[1].running = False
            self.visualizer.canvas.mark_node_crashed("A0")
            self.visualizer.canvas.mark_node_crashed("A1")
            print("DEBUG: A0 and A1 crashed and marked")  # Debug log
            time.sleep(2)
        
        # Phase 1a: Second proposer sends prepare with higher number
        if len(self.proposers) > 1:
            self.visualizer.log_message("Phase 1a: P1 sending prepare messages with higher number")
            self.proposers[1].set_proposal("New Value After Crash")
            self.proposers[1].prepare()
            time.sleep(2)
            
            # Phase 1b: Acceptors respond with promises
            self.visualizer.log_message("Phase 1b: Acceptors sending promise messages to P1")
            for acceptor in self.acceptors:
                if acceptor.running:  # Only process messages from running acceptors
                    acceptor.recv_prepare("P1", self.proposers[1].proposal_id)
            time.sleep(2)
            
            # Phase 2a: Send accept request
            self.visualizer.log_message("Phase 2a: P1 sending accept messages")
            self.proposers[1].send_accept(self.proposers[1].proposal_id, "New Value After Crash")
            time.sleep(2)
            
            # Phase 2b: Acceptors accept and notify learners
            self.visualizer.log_message("Phase 2b: Acceptors accepting and notifying learners")
            for acceptor in self.acceptors:
                if acceptor.running:  # Only process messages from running acceptors
                    acceptor.recv_accept_request("P1", self.proposers[1].proposal_id, "New Value After Crash")
            time.sleep(2)
            
            # Check if consensus was reached
            for learner in self.learners:
                if learner.final_value is not None:
                    self.visualizer.log_message(f"Consensus reached! Value: {learner.final_value}")
        
        # Let simulation run for a while to see all messages
        time.sleep(2)
        
        # Stop simulation
        self.stop()
        self.visualizer.log_message("Simulation complete")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PaxosVisualizer()
    window.show()
    sys.exit(app.exec()) 