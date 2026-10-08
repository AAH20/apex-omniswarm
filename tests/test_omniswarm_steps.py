"""
Comprehensive Test Suite for Apex-OmniSwarm (All 8 Steps & Master Engine).
Zero external dependencies, uses standard unittest.
"""

from __future__ import annotations
import math
import unittest

from apex_omniswarm.core.primitives import (
    Vector3D,
    NodeTelemetry,
    TrackState,
    MissionIntentContract,
)
from apex_omniswarm.core.step1_intent import IntentAndROEEngine
from apex_omniswarm.core.step2_spatial import SpatialIntelligenceEngine
from apex_omniswarm.core.step3_grounding import SwarmGroundingEngine
from apex_omniswarm.core.step4_spectral import SpectralMeshEngine
from apex_omniswarm.core.step5_coalition import CoalitionGenerationEngine
from apex_omniswarm.core.step6_killchain import KillChainAndBottleneckEngine
from apex_omniswarm.core.step7_reflex import DeterministicReflexCBF
from apex_omniswarm.core.step8_provenance import PostQuantumEvidenceLedger
from apex_omniswarm.orchestrator import ApexOmniSwarmOrchestrator


class TestApexOmniSwarm(unittest.TestCase):

    def test_vector3d_primitives(self):
        v1 = Vector3D(1.0, 2.0, 3.0)
        v2 = Vector3D(4.0, 5.0, 6.0)
        self.assertEqual(v1 + v2, Vector3D(5.0, 7.0, 9.0))
        self.assertEqual(v2 - v1, Vector3D(3.0, 3.0, 3.0))
        self.assertEqual(v1 * 2.0, Vector3D(2.0, 4.0, 6.0))
        self.assertAlmostEqual(v1.magnitude(), math.sqrt(14.0))
        self.assertAlmostEqual(v1.distance_to(v2), math.sqrt(27.0))
        self.assertAlmostEqual(v1.dot(v2), 32.0)

    def test_step1_intent_and_roe(self):
        engine = IntentAndROEEngine()
        # CoT ingestion
        contract = engine.parse_cursor_on_target(
            cot_uid="TEST-001",
            lat_lon_hae=(34.0, -118.0, 100.0),
            callsign="VIPER-1",
            no_fire_polygons=[(Vector3D(100.0, 100.0, 0.0), 50.0)]
        )
        self.assertEqual(contract.originator, "VIPER-1")
        self.assertEqual(len(contract.no_fire_zones), 1)

        # ROE inside no-fire zone must fail
        violating_target = Vector3D(110.0, 110.0, 0.0)
        approved, reason = engine.validate_roe_and_loac(contract, violating_target)
        self.assertFalse(approved)
        self.assertIn("No-Fire Zone", reason)

        # Target in authorized area passes
        valid_target = contract.target_area_centroid + Vector3D(50.0, 50.0, 0.0)
        approved, reason = engine.validate_roe_and_loac(contract, valid_target)
        self.assertTrue(approved)
        self.assertTrue(contract.roe_approved)

    def test_step2_spatial_intelligence(self):
        engine = SpatialIntelligenceEngine(association_gate_meters=50.0)
        # Ingest first contact (unconfirmed)
        track = engine.ingest_sensor_contact(
            target_id="TGT-A",
            target_type="UAV",
            observed_pos=Vector3D(100.0, 100.0, 50.0),
            sensor_uncertainty_trace=0.5,
            reporting_node_id="NODE-1"
        )
        self.assertFalse(track.confirmed)
        self.assertEqual(len(track.confirming_nodes), 1)

        # Ingest second contact from different node (confirmed)
        track2 = engine.ingest_sensor_contact(
            target_id="TGT-A",
            target_type="UAV",
            observed_pos=Vector3D(102.0, 99.0, 50.0),
            sensor_uncertainty_trace=0.3,
            reporting_node_id="NODE-2"
        )
        self.assertTrue(track2.confirmed)
        self.assertEqual(len(track2.confirming_nodes), 2)
        # Covariance must have reduced due to Kalman fusion
        self.assertLess(track2.covariance_trace, 0.5)

    def test_step3_swarm_grounding_and_byzantine_quarantine(self):
        engine = SwarmGroundingEngine(mahalanobis_chi_threshold=7.815)
        honest_nodes = [
            NodeTelemetry("H1", "recon", Vector3D(10.0, 10.0, 50.0), Vector3D(0, 0, 0), 0.2, 50000, 5, 1e6),
            NodeTelemetry("H2", "strike", Vector3D(12.0, 9.0, 50.0), Vector3D(0, 0, 0), 0.3, 50000, 5, 1e6),
            NodeTelemetry("H3", "relay", Vector3D(9.0, 11.0, 50.0), Vector3D(0, 0, 0), 0.2, 50000, 5, 1e6),
        ]
        # Injected Byzantine outlier
        byzantine_node = NodeTelemetry(
            "BYZ-1", "recon", Vector3D(950.0, 900.0, -200.0), Vector3D(0, 0, 0), 0.1, 50000, 5, 1e6
        )
        all_nodes = honest_nodes + [byzantine_node]

        grounded_pos, grounded_trace, quarantined = engine.compute_grounded_consensus(all_nodes)
        self.assertIn("BYZ-1", quarantined)
        self.assertTrue(byzantine_node.quarantined)
        # Consensus should reflect honest cluster near (10, 10, 50)
        self.assertAlmostEqual(grounded_pos.x, 10.0, delta=2.5)
        self.assertAlmostEqual(grounded_pos.y, 10.0, delta=2.5)

    def test_step4_spectral_mesh(self):
        engine = SpectralMeshEngine(max_comm_range_meters=100.0)
        nodes = {
            "N1": NodeTelemetry("N1", "recon", Vector3D(0, 0, 0), Vector3D(0, 0, 0), 0.1, 50000, 0, 1e6),
            "N2": NodeTelemetry("N2", "strike", Vector3D(50, 0, 0), Vector3D(0, 0, 0), 0.1, 50000, 0, 1e6),
            "N3": NodeTelemetry("N3", "relay", Vector3D(250, 0, 0), Vector3D(0, 0, 0), 0.1, 50000, 0, 1e6),
        }
        topology = engine.compute_active_topology(nodes)
        # N1 and N2 are within 100m, N3 is 200m away from N2
        self.assertIn("N2", topology["N1"])
        self.assertNotIn("N3", topology["N1"])

        hops = engine.generate_frequency_hop_schedule("N1")
        self.assertEqual(len(hops), 8)

    def test_step5_coalition_generation(self):
        engine = CoalitionGenerationEngine()
        nodes = {
            "R1": NodeTelemetry("R1", "recon", Vector3D(0, 0, 0), Vector3D(0, 0, 0), 0.1, 80000, 0, 1e6),
            "S1": NodeTelemetry("S1", "strike", Vector3D(0, 0, 0), Vector3D(0, 0, 0), 0.1, 80000, 0, 1e6),
            "LOW_BAT": NodeTelemetry("LOW_BAT", "strike", Vector3D(0, 0, 0), Vector3D(0, 0, 0), 0.1, 8000, 0, 1e6),
        }
        tracks = {
            "T1": TrackState("T1", "RADAR", Vector3D(100, 100, 0), Vector3D(0, 0, 0), 0.2, 8.0, confirmed=True)
        }
        coalitions = engine.form_tactical_coalitions(nodes, tracks)
        self.assertIn("R1", coalitions["recon_cell"])
        self.assertIn("S1", coalitions["strike_cell"])
        self.assertIn("LOW_BAT", coalitions["reserve_cell"])

    def test_step6_killchain_and_bottleneck(self):
        engine = KillChainAndBottleneckEngine(queue_backlog_threshold=20)
        nodes = {
            "OVERLOADED": NodeTelemetry("OVERLOADED", "recon", Vector3D(0, 0, 0), Vector3D(0, 0, 0), 0.1, 50000, 45, 1e6),
            "IDLE": NodeTelemetry("IDLE", "strike", Vector3D(10, 0, 0), Vector3D(0, 0, 0), 0.1, 50000, 2, 1e6),
        }
        offload = engine.discover_and_offload_bottlenecks(nodes)
        self.assertEqual(len(offload), 1)
        src, dst, tasks = offload[0]
        self.assertEqual(src, "OVERLOADED")
        self.assertEqual(dst, "IDLE")
        self.assertEqual(tasks, 25)

    def test_step7_reflex_cbf(self):
        cbf = DeterministicReflexCBF(min_separation_meters=5.0, gamma_barrier=0.8)
        node_a = NodeTelemetry("A", "strike", Vector3D(0, 0, 0), Vector3D(10, 0, 0), 0.1, 50000, 0, 1e6)
        node_b = NodeTelemetry("B", "strike", Vector3D(10, 0, 0), Vector3D(0, 0, 0), 0.1, 50000, 0, 1e6)

        # Desired velocity directly toward node_b
        desired_v = Vector3D(10.0, 0.0, 0.0)
        safe_v = cbf.compute_safe_reflex_velocity(node_a, desired_v, [node_a, node_b])
        # Inward velocity component along X must be suppressed or deflected
        self.assertLess(safe_v.x, desired_v.x)

        motor_throttles = cbf.convert_to_motor_actuator_setpoints(safe_v)
        self.assertEqual(len(motor_throttles), 4)
        for m in motor_throttles:
            self.assertTrue(0.0 <= m <= 1.0)

    def test_step8_post_quantum_ledger(self):
        ledger = PostQuantumEvidenceLedger()
        b1 = ledger.append_cycle_evidence(
            cycle_latency_us=450.0,
            centroid=Vector3D(10, 20, 30),
            quarantined=[],
            actuation_map={"A": Vector3D(5, 5, 0)}
        )
        b2 = ledger.append_cycle_evidence(
            cycle_latency_us=430.0,
            centroid=Vector3D(12, 22, 30),
            quarantined=["ROGUE-1"],
            actuation_map={"A": Vector3D(6, 4, 0)}
        )
        self.assertEqual(b2.previous_hash, b1.block_hash)
        self.assertEqual(b1.index, 1)
        self.assertEqual(b2.index, 2)

        valid, msg = ledger.verify_chain_integrity()
        self.assertTrue(valid)
        self.assertIn("verified", msg.lower())

    def test_master_orchestrator_end_to_end(self):
        orchestrator = ApexOmniSwarmOrchestrator()
        orchestrator.register_node(NodeTelemetry(
            "SCOUT-1", "recon", Vector3D(100, 100, 50), Vector3D(5, 0, 0), 0.2, 50000, 55, 1e6
        ))
        orchestrator.register_node(NodeTelemetry(
            "STRIKE-1", "strike", Vector3D(105, 102, 50), Vector3D(5, 0, 0), 0.3, 50000, 4, 1e6
        ))
        orchestrator.record_sensor_observation(
            target_id="RADAR-X", target_type="SAM",
            observed_pos=Vector3D(200, 200, 0), sensor_uncertainty=0.4, reporting_node_id="SCOUT-1"
        )
        orchestrator.record_sensor_observation(
            target_id="RADAR-X", target_type="SAM",
            observed_pos=Vector3D(201, 199, 0), sensor_uncertainty=0.3, reporting_node_id="STRIKE-1"
        )

        report = orchestrator.execute_operational_cycle(dt=0.05)

        self.assertEqual(report.cycle_index, 1)
        self.assertEqual(report.active_nodes_count, 2)
        # Latency must be well under 1,500 microseconds target
        self.assertLess(report.total_cycle_latency_us, 1500.0)
        self.assertIn("step1_intent_roe_us", report.step_latencies_us)
        self.assertIn("step8_provenance_audit_us", report.step_latencies_us)
        self.assertEqual(len(report.actuation_commands), 2)


if __name__ == "__main__":
    unittest.main()
