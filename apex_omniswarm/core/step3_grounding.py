"""
Step 3: Swarm Grounding & Byzantine Epistemic Consensus.
Integrates patterns from distributed-track-fusion-kernel and byzantine-epistemic-filter.
"""

from __future__ import annotations
import math
from typing import Dict, List, Optional, Set, Tuple
from apex_omniswarm.core.primitives import Vector3D, NodeTelemetry


class SwarmGroundingEngine:
    """
    Decentralized multi-sensor consensus engine.
    Computes trace-minimized Covariance Intersection and filters out
    jammed, spoofed, or Byzantine malicious peer reports using the Mahalanobis distance metric.
    """

    def __init__(
        self,
        mahalanobis_chi_threshold: float = 7.815,
        formation_radius_meters: float = 150.0
    ):
        # 7.815 corresponds to chi^2 distribution with 3 degrees of freedom at 95% confidence
        self.chi_threshold = mahalanobis_chi_threshold
        self.formation_radius = formation_radius_meters

    def compute_grounded_consensus(
        self,
        node_telemetry_list: List[NodeTelemetry]
    ) -> Tuple[Vector3D, float, List[str]]:
        """
        Executes decentralized spatial consensus across swarm nodes.
        Returns:
            (grounded_position, grounded_covariance_trace, list_of_quarantined_node_ids)
        """
        if not node_telemetry_list:
            return Vector3D(0.0, 0.0, 0.0), 999.0, []

        active_reports = [n for n in node_telemetry_list if not n.quarantined]
        if not active_reports:
            return Vector3D(0.0, 0.0, 0.0), 999.0, []

        # 1. Compute robust coordinate-wise median as Byzantine-resistant reference center
        n = len(active_reports)
        xs = sorted(node.position.x for node in active_reports)
        ys = sorted(node.position.y for node in active_reports)
        zs = sorted(node.position.z for node in active_reports)
        mid = len(active_reports) // 2
        if len(active_reports) % 2 == 1:
            robust_center = Vector3D(xs[mid], ys[mid], zs[mid])
        else:
            robust_center = Vector3D(
                (xs[mid - 1] + xs[mid]) / 2.0,
                (ys[mid - 1] + ys[mid]) / 2.0,
                (zs[mid - 1] + zs[mid]) / 2.0
            )

        valid_nodes: List[NodeTelemetry] = []
        quarantined_ids: List[str] = []

        # 2. Byzantine Mahalanobis Outlier Filter against robust center & formation envelope
        for node in active_reports:
            dist = node.position.distance_to(robust_center)
            excess_dist = max(0.0, dist - self.formation_radius)
            sigma = math.sqrt(max(node.covariance_trace, 0.05))
            # Normalized Mahalanobis proxy: squared spatial residual beyond formation / variance
            mahalanobis_metric = (excess_dist * excess_dist) / sigma

            if mahalanobis_metric > self.chi_threshold and n > 2:
                quarantined_ids.append(node.node_id)
                node.is_compromised = True
                node.quarantined = True
            else:
                valid_nodes.append(node)

        # Fallback if all nodes flagged
        if not valid_nodes:
            valid_nodes = active_reports

        # 3. Covariance Intersection (Trace-optimal weighting w_i = 1 / Tr(P_i))
        inverse_traces = [1.0 / max(node.covariance_trace, 0.01) for node in valid_nodes]
        sum_inv_trace = sum(inverse_traces)
        weights = [inv / sum_inv_trace for inv in inverse_traces]

        consensus_x = sum(node.position.x * w for node, w in zip(valid_nodes, weights))
        consensus_y = sum(node.position.y * w for node, w in zip(valid_nodes, weights))
        consensus_z = sum(node.position.z * w for node, w in zip(valid_nodes, weights))
        grounded_pos = Vector3D(consensus_x, consensus_y, consensus_z)

        # Harmonic sum uncertainty trace
        grounded_trace = 1.0 / sum_inv_trace

        return grounded_pos, grounded_trace, quarantined_ids
