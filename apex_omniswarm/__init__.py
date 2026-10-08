"""
Apex-OmniSwarm: Autonomous Heterogeneous Battle-Management OS
Sovereign Multi-Domain Swarm Orchestration & Microsecond Sensor-to-Shooter Engine
"""

__version__ = "1.1.0"

from apex_omniswarm.core.primitives import (
    Vector3D,
    NodeTelemetry,
    TrackState,
    MissionIntentContract,
    ExecutionReport,
)
from apex_omniswarm.orchestrator import ApexOmniSwarmOrchestrator

__all__ = [
    "Vector3D",
    "NodeTelemetry",
    "TrackState",
    "MissionIntentContract",
    "ExecutionReport",
    "ApexOmniSwarmOrchestrator",
]
