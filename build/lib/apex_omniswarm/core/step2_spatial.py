"""
Step 2: Multi-Domain Sensing & Spatial 3D Intelligence.
Integrates concepts from Apex_ISR, phased_aperture_orchestrator, and spatial-intelligence-3dgs-kernel.
"""

from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple
from apex_omniswarm.core.primitives import Vector3D, TrackState


class SpatialIntelligenceEngine:
    """
    Maintains 3D spatial target representations, multi-sensor association,
    and microsecond kinematic filtering.
    """

    def __init__(self, association_gate_meters: float = 35.0):
        self.association_gate = association_gate_meters
        self.tracks: Dict[str, TrackState] = {}

    def compute_jpda_association_score(
        self,
        measurement_pos: Vector3D,
        track: TrackState
    ) -> float:
        """
        Computes normalized association likelihood under Gaussian spatial distribution:
        P(z | track) = exp(-0.5 * ||z - pos||^2 / sigma^2) / sqrt(2*pi*sigma^2)
        """
        dist = measurement_pos.distance_to(track.position)
        sigma = math.sqrt(max(track.covariance_trace, 0.1))
        exponent = -0.5 * (dist * dist) / (sigma * sigma)
        if exponent < -20.0:
            return 0.0
        return math.exp(exponent) / (math.sqrt(2.0 * math.pi) * sigma)

    def ingest_sensor_contact(
        self,
        target_id: str,
        target_type: str,
        observed_pos: Vector3D,
        sensor_uncertainty_trace: float,
        reporting_node_id: str,
        threat_priority: float = 5.0,
        dt: float = 0.05
    ) -> TrackState:
        """
        Associates raw radar / optical contacts to existing tracks or initiates new tracks.
        Executes constant-velocity Extended Kalman Filter state update.
        """
        # Multi-target JPDA Gating: check if measurement matches an existing track
        best_track_id: Optional[str] = None
        highest_score = 0.0

        for tid, track in self.tracks.items():
            dist = observed_pos.distance_to(track.position)
            if dist <= self.association_gate:
                score = self.compute_jpda_association_score(observed_pos, track)
                if score > highest_score:
                    highest_score = score
                    best_track_id = tid

        if best_track_id is not None:
            track = self.tracks[best_track_id]
            # Kinematic measurement residual
            residual = observed_pos - track.position

            # Kalman Gain computation (simplified 1D trace approximation for microsecond speed)
            prior_var = track.covariance_trace
            sensor_var = max(sensor_uncertainty_trace, 0.05)
            kalman_gain = prior_var / (prior_var + sensor_var)

            # State update
            track.position = track.position + (residual * kalman_gain)
            # Velocity estimate update
            measured_vel = residual * (1.0 / max(dt, 1e-4))
            track.velocity = track.velocity + ((measured_vel - track.velocity) * (kalman_gain * 0.5))
            # Covariance update
            track.covariance_trace = (1.0 - kalman_gain) * prior_var
            track.confirming_nodes.add(reporting_node_id)
            track.confirmed = len(track.confirming_nodes) >= 2
            track.threat_priority = max(track.threat_priority, threat_priority)
            return track

        # Track initiation (M-of-N confirmation trigger)
        new_track = TrackState(
            track_id=target_id,
            target_type=target_type,
            position=observed_pos,
            velocity=Vector3D(0.0, 0.0, 0.0),
            covariance_trace=sensor_uncertainty_trace,
            threat_priority=threat_priority,
            confirmed=False,
            confirming_nodes={reporting_node_id}
        )
        self.tracks[target_id] = new_track
        return new_track

    def prune_stale_tracks(self, active_target_ids: Set[str]) -> None:
        """Removes dropped or destroyed tracks."""
        dropped = [tid for tid in self.tracks if tid not in active_target_ids]
        for tid in dropped:
            del self.tracks[tid]
