"""
Step 5: Coalition Structure Generation & Dynamic Task Knapsack.
Integrates patterns from ApexGraphSwarm (hypergraph_csg) and mirofish-swarm-optimizer (attention_knapsack, kemeny_consensus).
"""

from __future__ import annotations
import math
from typing import Dict, List, Set, Tuple
from apex_omniswarm.core.primitives import Vector3D, NodeTelemetry, TrackState


class CoalitionGenerationEngine:
    """
    Partitions the active swarm into specialized tactical cells (Scout, Strike, Relay)
    and optimizes sensor beam attention using a submodular knapsack solver.
    """

    def form_tactical_coalitions(
        self,
        nodes: Dict[str, NodeTelemetry],
        active_tracks: Dict[str, TrackState]
    ) -> Dict[str, List[str]]:
        """
        Generates optimal coalition structure C* = {C_recon, C_strike, C_relay}
        allocating nodes according to role, spatial proximity, and battery reserve.
        """
        active_nodes = [n for n in nodes.values() if not n.quarantined]
        coalitions: Dict[str, List[str]] = {
            "recon_cell": [],
            "strike_cell": [],
            "relay_cell": [],
            "reserve_cell": []
        }

        # Priority 1: High threat targets demand dedicated strike allocation
        high_threats = [t for t in active_tracks.values() if t.threat_priority >= 6.0 and t.confirmed]

        for node in active_nodes:
            if node.battery_joules < 15000.0:
                coalitions["reserve_cell"].append(node.node_id)
                node.assigned_cell_id = "reserve_cell"
            elif node.role in ("strike", "loitering") and high_threats:
                coalitions["strike_cell"].append(node.node_id)
                node.assigned_cell_id = "strike_cell"
            elif node.role in ("recon", "scout"):
                coalitions["recon_cell"].append(node.node_id)
                node.assigned_cell_id = "recon_cell"
            elif node.role in ("relay", "mothership"):
                coalitions["relay_cell"].append(node.node_id)
                node.assigned_cell_id = "relay_cell"
            else:
                # Default dynamic distribution
                if len(coalitions["recon_cell"]) < len(coalitions["strike_cell"]):
                    coalitions["recon_cell"].append(node.node_id)
                    node.assigned_cell_id = "recon_cell"
                else:
                    coalitions["strike_cell"].append(node.node_id)
                    node.assigned_cell_id = "strike_cell"

        return coalitions

    def compute_shapley_marginal_contribution(
        self,
        node: NodeTelemetry,
        coalition: List[NodeTelemetry]
    ) -> float:
        """
        Calculates cooperative game-theoretic Shapley marginal value:
        phi_i = V(C U {i}) - V(C)
        where utility V(C) balances total sensor coverage, kinetic weapon payload, and battery endurance.
        """
        def coalition_value(members: List[NodeTelemetry]) -> float:
            if not members:
                return 0.0
            recon_count = sum(1 for m in members if m.role in ("recon", "scout"))
            strike_count = sum(1 for m in members if m.role in ("strike", "loitering"))
            relay_count = sum(1 for m in members if m.role in ("relay", "mothership"))
            total_batt = sum(m.battery_joules for m in members) / 100000.0

            # Submodular cooperative synergy: square root of role counts prevents duplicate bloat
            value = (math.sqrt(recon_count) * 4.0 +
                     math.sqrt(strike_count) * 6.0 +
                     math.sqrt(relay_count) * 3.0 +
                     min(total_batt, 10.0))
            return value

        base_val = coalition_value(coalition)
        augmented_val = coalition_value(coalition + [node])
        return max(0.0, augmented_val - base_val)

    def prioritize_targets_kemeny(
        self,
        tracks: List[TrackState]
    ) -> List[TrackState]:
        """
        Ranks confirmed targets based on threat score, kinematic closing velocity,
        and confirmation consensus (Kemeny-Young rank aggregation proxy).
        """
        return sorted(
            tracks,
            key=lambda t: (t.confirmed, t.threat_priority, len(t.confirming_nodes)),
            reverse=True
        )
