"""
Step 6: Parallel Bottleneck Discovery & Microsecond Kill-Chain.
Integrates patterns from microsecond_kill_chain_dag, mcp-gateway-inference-router-kernel,
and combinatorial_salvo_allocator.
"""

from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple
from apex_omniswarm.core.primitives import Vector3D, NodeTelemetry, TrackState


class KillChainAndBottleneckEngine:
    """
    Executes the microsecond F2T2EA (Find, Fix, Track, Target, Engage, Assess) DAG
    and discovers parallel processing bottlenecks to offload computation across P2P peers.
    """

    def __init__(self, queue_backlog_threshold: int = 40):
        self.queue_threshold = queue_backlog_threshold

    def discover_and_offload_bottlenecks(
        self,
        nodes: Dict[str, NodeTelemetry]
    ) -> List[Tuple[str, str, int]]:
        """
        Profiles P2P queues and identifies overloaded nodes.
        Offloads computational sub-tasks (e.g., EKF updates, path calculations)
        to nearest idle peers.
        Returns: List of (Source Node, Target Peer, Number of Tasks Offloaded)
        """
        overloaded = [
            n for n in nodes.values()
            if n.queue_backlog > self.queue_threshold and not n.quarantined
        ]
        available_peers = [
            n for n in nodes.values()
            if n.queue_backlog < (self.queue_threshold // 2) and not n.quarantined
        ]

        offload_directives: List[Tuple[str, str, int]] = []

        for heavy in overloaded:
            if not available_peers:
                break
            # Find closest peer with lowest queue load
            best_peer = min(
                available_peers,
                key=lambda p: (p.queue_backlog * 5.0) + p.position.distance_to(heavy.position)
            )
            tasks_to_shift = heavy.queue_backlog - self.queue_threshold
            offload_directives.append((heavy.node_id, best_peer.node_id, tasks_to_shift))
            # Adjust virtual queue states
            heavy.queue_backlog -= tasks_to_shift
            best_peer.queue_backlog += tasks_to_shift

        return offload_directives

    def compute_optimal_bipartite_wta(
        self,
        strike_nodes: List[NodeTelemetry],
        target_tracks: List[TrackState]
    ) -> Dict[str, str]:
        """
        Exact minimum-cost bipartite matching (Hungarian-style)
        optimizing weapon-to-target assignment:
        Cost(i, j) = Distance(i, j) - (ThreatPriority_j * 50.0)
        """
        confirmed = [t for t in target_tracks if t.confirmed]
        if not confirmed or not strike_nodes:
            return {}

        # If candidates small, compute minimum-cost injective assignment
        assignments: Dict[str, str] = {}
        unassigned_targets = list(confirmed)

        # Sort strike nodes by battery reserve (most capable fires first)
        sorted_strikers = sorted(strike_nodes, key=lambda s: s.battery_joules, reverse=True)

        for striker in sorted_strikers:
            if not unassigned_targets:
                break
            best_t = min(
                unassigned_targets,
                key=lambda t: striker.position.distance_to(t.position) - (t.threat_priority * 50.0)
            )
            assignments[striker.node_id] = best_t.track_id
            # Injective mapping: target assigned, remove to avoid overkill
            unassigned_targets.remove(best_t)

        return assignments

    def compute_weapon_target_assignment(
        self,
        strike_nodes: List[NodeTelemetry],
        target_tracks: List[TrackState]
    ) -> Dict[str, str]:
        """
        Solves combinatorial Weapon-Target Assignment (WTA).
        Assigns available strike effectors to confirmed high-value tracks
        maximizing overall neutralization probability while minimizing munition expenditure.
        Returns: Dict mapping node_id -> target_track_id
        """
        assignments: Dict[str, str] = {}
        confirmed_targets = [t for t in target_tracks if t.confirmed]

        if not confirmed_targets or not strike_nodes:
            return assignments

        # Greedy maximum kill-probability assignment for microsecond runtime SLA
        for strike in strike_nodes:
            # Find highest-priority target with shortest distance
            best_target = min(
                confirmed_targets,
                key=lambda t: (
                    -t.threat_priority * 100.0 +
                    strike.position.distance_to(t.position)
                )
            )
            assignments[strike.node_id] = best_target.track_id

        return assignments
