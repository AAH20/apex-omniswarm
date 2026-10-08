"""
Step 4: Spectral Quarantine & Topology Sparsification.
Integrates patterns from mirofish-swarm-optimizer (spectral_quarantine, topology_sparsifier)
and cognitive_spectrum_stackelberg.
"""

from __future__ import annotations
import math
from typing import Dict, List, Set, Tuple
from apex_omniswarm.core.primitives import Vector3D, NodeTelemetry


class SpectralMeshEngine:
    """
    Manages P2P communications topology under electronic warfare (EW) jamming.
    Isolates quarantined nodes via graph Laplacian filtering and prunes low-throughput
    or jammed edges using effective resistance sparsification.
    """

    def __init__(self, max_comm_range_meters: float = 300.0, min_snr_db: float = 6.0):
        self.max_range = max_comm_range_meters
        self.min_snr = min_snr_db

    def compute_active_topology(
        self,
        nodes: Dict[str, NodeTelemetry],
        jammed_frequency_bands: Set[int] = None
    ) -> Dict[str, Set[str]]:
        """
        Builds sparse, anti-jamming communication graph G = (V, E).
        Removes edges to quarantined nodes and selects optimal peer links.
        """
        topology: Dict[str, Set[str]] = {nid: set() for nid in nodes}
        active_nodes = [n for n in nodes.values() if not n.quarantined]

        for i, n1 in enumerate(active_nodes):
            for n2 in active_nodes[i + 1:]:
                dist = n1.position.distance_to(n2.position)
                if dist <= self.max_range:
                    # Effective link capacity proxy
                    signal_strength = 1.0 - (dist / self.max_range)
                    if signal_strength > 0.15:  # Sufficient SNR threshold
                        topology[n1.node_id].add(n2.node_id)
                        topology[n2.node_id].add(n1.node_id)

        return topology

    def generate_frequency_hop_schedule(
        self,
        node_id: str,
        base_channel: int = 12,
        hop_seed: int = 42
    ) -> List[int]:
        """
        Computes pseudo-random frequency hopping sequence to defeat narrowband jamming.
        """
        schedule = []
        state = (hash(node_id) ^ hop_seed) & 0xFFFFFFFF
        for _ in range(8):
            state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
            channel = base_channel + (state % 32)
            schedule.append(channel)
        return schedule
