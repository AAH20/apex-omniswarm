"""
Master Orchestrator for Apex-OmniSwarm.
Unifies all 8 operational phases into a single deterministic sub-millisecond execution loop.
Zero external dependencies.
"""

from __future__ import annotations
import time
from typing import Dict, List, Optional, Set, Tuple

from apex_omniswarm.core.primitives import (
    Vector3D,
    NodeTelemetry,
    TrackState,
    MissionIntentContract,
    ExecutionReport,
)
from apex_omniswarm.core.step1_intent import IntentAndROEEngine
from apex_omniswarm.core.step2_spatial import SpatialIntelligenceEngine
from apex_omniswarm.core.step3_grounding import SwarmGroundingEngine
from apex_omniswarm.core.step4_spectral import SpectralMeshEngine
from apex_omniswarm.core.step5_coalition import CoalitionGenerationEngine
from apex_omniswarm.core.step6_killchain import KillChainAndBottleneckEngine
from apex_omniswarm.core.step7_reflex import DeterministicReflexCBF
from apex_omniswarm.core.step8_provenance import PostQuantumEvidenceLedger


class ApexOmniSwarmOrchestrator:
    """
    Master System of Systems (SoS) Engine executing the 8-Step pipeline:
    1. Intent & Constitutional ROE Ingestion
    2. Multi-Domain Sensing & Spatial 3D Intelligence
    3. Swarm Grounding & Byzantine Epistemic Consensus
    4. Spectral Quarantine & Topology Sparsification
    5. Coalition Structure Generation & Task Allocation
    6. Parallel Bottleneck Discovery & Microsecond Kill-Chain
    7. Deterministic Reflex, 4D Kinematic CBF & Motor Actuation
    8. Post-Quantum Provenance & Black Box Evidence Ledger
    """

    def __init__(self, mission_contract: Optional[MissionIntentContract] = None):
        self.mission = mission_contract or MissionIntentContract(
            mission_id="DEFAULT-MISSION-OMNISWARM",
            originator="C2_AUTONOMOUS_DEFAULT",
            target_area_centroid=Vector3D(0.0, 0.0, 50.0),
            operational_radius_meters=3000.0,
            max_engagement_velocity_mps=25.0,
            proportionality_threshold=0.80,
            roe_approved=True
        )

        # 8 Specialized Engines
        self.intent_engine = IntentAndROEEngine()
        self.spatial_engine = SpatialIntelligenceEngine()
        self.grounding_engine = SwarmGroundingEngine()
        self.spectral_engine = SpectralMeshEngine()
        self.coalition_engine = CoalitionGenerationEngine()
        self.killchain_engine = KillChainAndBottleneckEngine()
        self.reflex_engine = DeterministicReflexCBF()
        self.evidence_ledger = PostQuantumEvidenceLedger()

        # Telemetry & State Stores
        self.nodes: Dict[str, NodeTelemetry] = {}
        self.cycle_count = 0
        self.quarantined_node_ids: Set[str] = set()

    def register_node(self, node: NodeTelemetry) -> None:
        """Adds a heterogeneous node to the swarm registry."""
        self.nodes[node.node_id] = node

    def set_mission_contract(self, contract: MissionIntentContract) -> None:
        """Sets or updates the current tactical mission contract."""
        self.mission = contract

    def record_sensor_observation(
        self,
        target_id: str,
        target_type: str,
        observed_pos: Vector3D,
        sensor_uncertainty: float,
        reporting_node_id: str,
        threat_priority: float = 5.0
    ) -> TrackState:
        """Ingests an observation from radar, EO/IR, or ESM into Step 2."""
        return self.spatial_engine.ingest_sensor_contact(
            target_id=target_id,
            target_type=target_type,
            observed_pos=observed_pos,
            sensor_uncertainty_trace=sensor_uncertainty,
            reporting_node_id=reporting_node_id,
            threat_priority=threat_priority
        )

    def execute_operational_cycle(self, dt: float = 0.05) -> ExecutionReport:
        """
        Executes one complete real-time arbitration cycle encompassing all 8 steps.
        Sub-1.5 millisecond target latency budget.
        """
        self.cycle_count += 1
        cycle_start_ns = time.perf_counter_ns()
        latencies: Dict[str, float] = {}

        # -----------------------------------------------------------------
        # STEP 1: Intent & ROE Ingestion
        # -----------------------------------------------------------------
        t1_start = time.perf_counter_ns()
        # Verify ROE against current mission centroid
        roe_ok, roe_reason = self.intent_engine.validate_roe_and_loac(
            self.mission, self.mission.target_area_centroid
        )
        latencies["step1_intent_roe_us"] = (time.perf_counter_ns() - t1_start) / 1000.0

        # -----------------------------------------------------------------
        # STEP 2: Spatial Intelligence & 3D Tracks
        # -----------------------------------------------------------------
        t2_start = time.perf_counter_ns()
        active_tracks = self.spatial_engine.tracks
        latencies["step2_spatial_3d_us"] = (time.perf_counter_ns() - t2_start) / 1000.0

        # -----------------------------------------------------------------
        # STEP 3: Swarm Grounding & Epistemic Filter
        # -----------------------------------------------------------------
        t3_start = time.perf_counter_ns()
        node_list = list(self.nodes.values())
        grounded_pos, grounded_cov, newly_quarantined = (
            self.grounding_engine.compute_grounded_consensus(node_list)
        )
        self.quarantined_node_ids.update(newly_quarantined)
        latencies["step3_swarm_grounding_us"] = (time.perf_counter_ns() - t3_start) / 1000.0

        # -----------------------------------------------------------------
        # STEP 4: Spectral Quarantine & Topology
        # -----------------------------------------------------------------
        t4_start = time.perf_counter_ns()
        active_topology = self.spectral_engine.compute_active_topology(self.nodes)
        latencies["step4_spectral_quarantine_us"] = (time.perf_counter_ns() - t4_start) / 1000.0

        # -----------------------------------------------------------------
        # STEP 5: Coalition Structure Generation
        # -----------------------------------------------------------------
        t5_start = time.perf_counter_ns()
        coalitions = self.coalition_engine.form_tactical_coalitions(
            self.nodes, active_tracks
        )
        prioritized_targets = self.coalition_engine.prioritize_targets_kemeny(
            list(active_tracks.values())
        )
        latencies["step5_coalition_csg_us"] = (time.perf_counter_ns() - t5_start) / 1000.0

        # -----------------------------------------------------------------
        # STEP 6: Parallel Bottleneck Discovery & Kill-Chain
        # -----------------------------------------------------------------
        t6_start = time.perf_counter_ns()
        offload_tasks = self.killchain_engine.discover_and_offload_bottlenecks(self.nodes)
        strike_nodes = [
            self.nodes[nid] for nid in coalitions.get("strike_cell", [])
            if nid in self.nodes and not self.nodes[nid].quarantined
        ]
        wta_assignments = self.killchain_engine.compute_weapon_target_assignment(
            strike_nodes, prioritized_targets
        )
        latencies["step6_killchain_pbd_us"] = (time.perf_counter_ns() - t6_start) / 1000.0

        # -----------------------------------------------------------------
        # STEP 7: Deterministic Reflex CBF & Motor Setpoints
        # -----------------------------------------------------------------
        t7_start = time.perf_counter_ns()
        actuation_commands: Dict[str, Vector3D] = {}
        active_nodes = [n for n in self.nodes.values() if not n.quarantined]

        for node in self.nodes.values():
            if node.quarantined:
                # Emergency hold pattern for quarantined / rogue nodes
                actuation_commands[node.node_id] = Vector3D(0.0, 0.0, 0.0)
                continue

            # Determine mission vector
            if node.node_id in wta_assignments:
                # Intercept assigned track
                target_track_id = wta_assignments[node.node_id]
                target_pos = active_tracks[target_track_id].position
                desired_dir = (target_pos - node.position).normalized()
                desired_vel = desired_dir * min(self.mission.max_engagement_velocity_mps, 20.0)
            else:
                # Maintain formation around grounded centroid
                desired_dir = (grounded_pos - node.position).normalized()
                desired_vel = desired_dir * 10.0  # 10 m/s cruise

            # Filter via Control Barrier Function (<5us safety guarantee)
            safe_vel = self.reflex_engine.compute_safe_reflex_velocity(
                node, desired_vel, active_nodes
            )
            actuation_commands[node.node_id] = safe_vel
            node.velocity = safe_vel

        latencies["step7_reflex_cbf_us"] = (time.perf_counter_ns() - t7_start) / 1000.0

        # -----------------------------------------------------------------
        # STEP 8: Post-Quantum Provenance Ledger
        # -----------------------------------------------------------------
        t8_start = time.perf_counter_ns()
        total_cycle_latency_us = (time.perf_counter_ns() - cycle_start_ns) / 1000.0
        evidence_block = self.evidence_ledger.append_cycle_evidence(
            cycle_latency_us=total_cycle_latency_us,
            centroid=grounded_pos,
            quarantined=list(self.quarantined_node_ids),
            actuation_map=actuation_commands
        )
        latencies["step8_provenance_audit_us"] = (time.perf_counter_ns() - t8_start) / 1000.0

        return ExecutionReport(
            cycle_index=self.cycle_count,
            total_cycle_latency_us=total_cycle_latency_us,
            step_latencies_us=latencies,
            active_nodes_count=len(active_nodes),
            quarantined_nodes=list(self.quarantined_node_ids),
            formed_coalitions=coalitions,
            offloaded_tasks_count=len(offload_tasks),
            actuation_commands=actuation_commands,
            hash_chain_head=evidence_block.block_hash
        )
