"""
High-Fidelity Synthetic Swarm Scenario Simulator for Apex-OmniSwarm.
Simulates contested operational theaters:
- Multi-target kinematic trajectories (evasive weave, ballistic, terrain-hug)
- Electronic Warfare (EW) RF jammer emissions & path loss
- GPS spoofing & signal degradation fields
- Contested communication packet loss and link attenuation
Zero external dependencies. Pure Python standard library.
"""

from __future__ import annotations
import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from apex_omniswarm.core.primitives import Vector3D, NodeTelemetry, TrackState


@dataclass
class JammerEmitter:
    jammer_id: str
    position: Vector3D
    effective_radiated_power_watts: float
    frequency_mhz: float
    bandwidth_mhz: float


@dataclass
class SimulatedTarget:
    target_id: str
    target_type: str  # 'SAM_RADAR', 'BALLISTIC_MISSILE', 'CRUISE_MISSILE', 'UAV_SCOUT'
    position: Vector3D
    velocity: Vector3D
    radar_cross_section_sqm: float
    threat_priority: float
    evasive_maneuver: bool = False


class SwarmScenarioSimulator:
    """
    High-fidelity physical and electromagnetic scenario generator
    for stress-testing and hardware-in-the-loop (HIL) validation.
    """

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.jammers: List[JammerEmitter] = []
        self.targets: List[SimulatedTarget] = []

    def add_rf_jammer(
        self,
        jammer_id: str,
        position: Vector3D,
        power_watts: float = 500.0,
        frequency_mhz: float = 2400.0
    ) -> None:
        self.jammers.append(JammerEmitter(
            jammer_id=jammer_id,
            position=position,
            effective_radiated_power_watts=power_watts,
            frequency_mhz=frequency_mhz,
            bandwidth_mhz=40.0
        ))

    def add_target(
        self,
        target_id: str,
        target_type: str,
        initial_pos: Vector3D,
        velocity: Vector3D,
        rcs_sqm: float = 2.0,
        threat_priority: float = 7.0,
        evasive: bool = False
    ) -> None:
        self.targets.append(SimulatedTarget(
            target_id=target_id,
            target_type=target_type,
            position=initial_pos,
            velocity=velocity,
            radar_cross_section_sqm=rcs_sqm,
            threat_priority=threat_priority,
            evasive_maneuver=evasive
        ))

    def step_targets(self, dt: float = 0.05) -> None:
        """Advances target physical kinematics."""
        for tgt in self.targets:
            if tgt.evasive_maneuver:
                # Sinusoidal evasive jinking maneuver
                time_proxy = tgt.position.x * 0.05
                lateral_accel = math.sin(time_proxy) * 4.0
                tgt.velocity = tgt.velocity + Vector3D(0.0, lateral_accel * dt, 0.0)

            tgt.position = tgt.position + (tgt.velocity * dt)

    def calculate_rf_jamming_power_at_node(self, node_pos: Vector3D) -> float:
        """
        Calculates received jamming power (Watts) using Friis free-space path loss:
        P_rx = P_tx * (c / (4 * pi * f * d))^2
        """
        c = 3.0e8  # speed of light m/s
        total_jamming_power = 0.0

        for jammer in self.jammers:
            dist = max(node_pos.distance_to(jammer.position), 1.0)
            wavelength = c / (jammer.frequency_mhz * 1.0e6)
            path_loss = (wavelength / (4.0 * math.pi * dist)) ** 2
            p_rx = jammer.effective_radiated_power_watts * path_loss
            total_jamming_power += p_rx

        return total_jamming_power

    def generate_sensor_measurements(
        self,
        observing_nodes: List[NodeTelemetry]
    ) -> List[Tuple[str, str, Vector3D, float, str, float]]:
        """
        Simulates radar/optical observation generation with noise proportional to jamming interference.
        Returns: List of (target_id, target_type, observed_pos, uncertainty_trace, reporting_node_id, threat_priority)
        """
        observations = []

        for tgt in self.targets:
            for node in observing_nodes:
                if node.quarantined:
                    continue

                dist = node.position.distance_to(tgt.position)
                # Sensor visual/radar horizon check (e.g. 5 km limit)
                if dist > 5000.0:
                    continue

                # Jamming noise calculation
                jamming_w = self.calculate_rf_jamming_power_at_node(node.position)
                noise_sigma = 0.5 + (jamming_w * 1000.0)  # Noise grows with jamming power

                # Add measurement noise
                noise_vec = Vector3D(
                    self.rng.gauss(0.0, noise_sigma),
                    self.rng.gauss(0.0, noise_sigma),
                    self.rng.gauss(0.0, noise_sigma * 0.5)
                )
                noisy_pos = tgt.position + noise_vec
                uncertainty_trace = noise_sigma * noise_sigma * 3.0

                observations.append((
                    tgt.target_id,
                    tgt.target_type,
                    noisy_pos,
                    uncertainty_trace,
                    node.node_id,
                    tgt.threat_priority
                ))

        return observations
