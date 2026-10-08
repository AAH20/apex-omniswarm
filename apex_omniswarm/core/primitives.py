"""
Core Mathematical and Telemetry Primitives for Apex-OmniSwarm.
Zero external dependencies.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class Vector3D:
    x: float
    y: float
    z: float

    def __add__(self, other: Vector3D) -> Vector3D:
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vector3D) -> Vector3D:
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> Vector3D:
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> Vector3D:
        return self * scalar

    def magnitude(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def dot(self, other: Vector3D) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def distance_to(self, other: Vector3D) -> float:
        return (self - other).magnitude()

    def normalized(self) -> Vector3D:
        mag = self.magnitude()
        if mag < 1e-9:
            return Vector3D(0.0, 0.0, 0.0)
        return Vector3D(self.x / mag, self.y / mag, self.z / mag)


@dataclass
class NodeTelemetry:
    node_id: str
    role: str  # 'recon', 'strike', 'relay', 'mothership', 'ugv'
    position: Vector3D
    velocity: Vector3D
    covariance_trace: float  # Sensor spatial uncertainty measure
    battery_joules: float
    queue_backlog: int
    bandwidth_capacity_bps: float
    is_compromised: bool = False
    quarantined: bool = False
    assigned_cell_id: Optional[str] = None


@dataclass
class TrackState:
    track_id: str
    target_type: str
    position: Vector3D
    velocity: Vector3D
    covariance_trace: float
    threat_priority: float  # 0.0 to 10.0
    confirmed: bool = False
    confirming_nodes: Set[str] = field(default_factory=set)


@dataclass
class MissionIntentContract:
    mission_id: str
    originator: str  # e.g., 'ATAK_OPERATOR', 'BCI_PILOT', 'AUTONOMOUS_C2'
    target_area_centroid: Vector3D
    operational_radius_meters: float
    max_engagement_velocity_mps: float
    proportionality_threshold: float
    no_fire_zones: List[Tuple[Vector3D, float]] = field(default_factory=list)  # (center, radius)
    roe_approved: bool = False


@dataclass
class ExecutionReport:
    cycle_index: int
    total_cycle_latency_us: float
    step_latencies_us: Dict[str, float]
    active_nodes_count: int
    quarantined_nodes: List[str]
    formed_coalitions: Dict[str, List[str]]
    offloaded_tasks_count: int
    actuation_commands: Dict[str, Vector3D]
    hash_chain_head: str
