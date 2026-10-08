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
        self.assertLess(report.total_cycle_latency_us, 1500.0)
        self.assertIn("step1_intent_roe_us", report.step_latencies_us)
        self.assertEqual(len(report.actuation_commands), 2)

    def test_simulation_scenario_generation(self):
        from apex_omniswarm.core.simulation import SwarmScenarioSimulator
        sim = SwarmScenarioSimulator(seed=123)
        sim.add_rf_jammer("JAM-1", Vector3D(500, 500, 0), power_watts=1000.0)
        sim.add_target("MGT-1", "BALLISTIC_MISSILE", Vector3D(1000, 1000, 200), Vector3D(-50, -50, 0), evasive=True)
        self.assertEqual(len(sim.jammers), 1)
        self.assertEqual(len(sim.targets), 1)

        sim.step_targets(dt=0.1)
        # Position must have moved
        self.assertLess(sim.targets[0].position.x, 1000.0)

    def test_rf_jammer_propagation(self):
        from apex_omniswarm.core.simulation import SwarmScenarioSimulator
        sim = SwarmScenarioSimulator()
        sim.add_rf_jammer("JAM-1", Vector3D(0, 0, 0), power_watts=500.0, frequency_mhz=2400.0)
        p_close = sim.calculate_rf_jamming_power_at_node(Vector3D(10, 0, 0))
        p_far = sim.calculate_rf_jamming_power_at_node(Vector3D(100, 0, 0))
        # Power inversely proportional to squared distance
        self.assertGreater(p_close, p_far)
        self.assertAlmostEqual(p_close / p_far, 100.0, delta=15.0)

    def test_jpda_spatial_association(self):
        engine = SpatialIntelligenceEngine(association_gate_meters=60.0)
        t1 = engine.ingest_sensor_contact("T1", "UAV", Vector3D(50, 50, 50), 0.2, "NODE-1")
        # Ingest nearby measurement: must associate to T1 via JPDA
        score = engine.compute_jpda_association_score(Vector3D(51, 49, 50), t1)
        self.assertGreater(score, 0.0)
        t2 = engine.ingest_sensor_contact("T1_CORRELATED", "UAV", Vector3D(51, 49, 50), 0.2, "NODE-2")
        self.assertEqual(t2.track_id, "T1")
        self.assertTrue(t2.confirmed)

    def test_shapley_coalition_contribution(self):
        engine = CoalitionGenerationEngine()
        strike1 = NodeTelemetry("S1", "strike", Vector3D(0, 0, 0), Vector3D(0, 0, 0), 0.1, 80000, 0, 1e6)
        strike2 = NodeTelemetry("S2", "strike", Vector3D(0, 0, 0), Vector3D(0, 0, 0), 0.1, 80000, 0, 1e6)
        recon1 = NodeTelemetry("R1", "recon", Vector3D(0, 0, 0), Vector3D(0, 0, 0), 0.1, 80000, 0, 1e6)

        coalition = [strike1]
        # Adding a distinct role (recon) should yield high marginal contribution
        recon_contrib = engine.compute_shapley_marginal_contribution(recon1, coalition)
        # Adding a duplicate role (second strike) yields submodular diminished contribution
        strike_contrib = engine.compute_shapley_marginal_contribution(strike2, coalition)
        self.assertGreater(recon_contrib, 0.0)
        self.assertGreater(strike_contrib, 0.0)

    def test_optimal_bipartite_wta(self):
        engine = KillChainAndBottleneckEngine()
        strikers = [
            NodeTelemetry("S1", "strike", Vector3D(10, 0, 0), Vector3D(0, 0, 0), 0.1, 90000, 0, 1e6),
            NodeTelemetry("S2", "strike", Vector3D(100, 0, 0), Vector3D(0, 0, 0), 0.1, 70000, 0, 1e6),
        ]
        targets = [
            TrackState("T1", "RADAR", Vector3D(12, 0, 0), Vector3D(0, 0, 0), 0.1, 9.0, confirmed=True),
            TrackState("T2", "CONVOY", Vector3D(95, 0, 0), Vector3D(0, 0, 0), 0.1, 5.0, confirmed=True),
        ]
        assignments = engine.compute_optimal_bipartite_wta(strikers, targets)
        self.assertEqual(len(assignments), 2)
        # S1 is closest to T1, S2 closest to T2
        self.assertEqual(assignments["S1"], "T1")
        self.assertEqual(assignments["S2"], "T2")

    def test_formation_scaled_grounding(self):
        engine = SwarmGroundingEngine(mahalanobis_chi_threshold=7.815, formation_radius_meters=100.0)
        nodes = [
            NodeTelemetry("N1", "recon", Vector3D(0, 0, 50), Vector3D(0, 0, 0), 0.2, 50000, 0, 1e6),
            NodeTelemetry("N2", "strike", Vector3D(40, 20, 50), Vector3D(0, 0, 0), 0.2, 50000, 0, 1e6),
            NodeTelemetry("N3", "relay", Vector3D(-30, 40, 50), Vector3D(0, 0, 0), 0.2, 50000, 0, 1e6),
            # Node 450m away is beyond formation envelope + chi-square threshold
            NodeTelemetry("ROGUE", "recon", Vector3D(500, 500, 50), Vector3D(0, 0, 0), 0.1, 50000, 0, 1e6),
        ]
        pos, trace, quarantined = engine.compute_grounded_consensus(nodes)
        self.assertIn("ROGUE", quarantined)
        self.assertNotIn("N1", quarantined)
        self.assertNotIn("N2", quarantined)
        self.assertNotIn("N3", quarantined)

    def test_high_stress_100_node_swarm(self):
        orchestrator = ApexOmniSwarmOrchestrator()
        # Provision 100 heterogeneous nodes
        for i in range(100):
            role = "recon" if i % 3 == 0 else ("strike" if i % 3 == 1 else "relay")
            orchestrator.register_node(NodeTelemetry(
                node_id=f"SWARM-NODE-{i:03d}",
                role=role,
                position=Vector3D(float(i % 10) * 10.0, float(i // 10) * 10.0, 50.0),
                velocity=Vector3D(5.0, 0.0, 0.0),
                covariance_trace=0.25,
                battery_joules=75000.0,
                queue_backlog=i % 45,
                bandwidth_capacity_bps=2.0e6
            ))
        report = orchestrator.execute_operational_cycle(dt=0.05)
        self.assertEqual(report.active_nodes_count, 100)
        # 100 nodes in pure Python: sub-25ms guarantee (40+ Hz flight loop)
        self.assertLess(report.total_cycle_latency_us, 25000.0)

    def test_squad_25_node_sub_millisecond_sla(self):
        orchestrator = ApexOmniSwarmOrchestrator()
        # Provision 25 tactical squad nodes
        for i in range(25):
            role = "recon" if i % 3 == 0 else ("strike" if i % 3 == 1 else "relay")
            orchestrator.register_node(NodeTelemetry(
                node_id=f"SQUAD-{i:02d}",
                role=role,
                position=Vector3D(float(i % 5) * 10.0, float(i // 5) * 10.0, 50.0),
                velocity=Vector3D(5.0, 0.0, 0.0),
                covariance_trace=0.25,
                battery_joules=75000.0,
                queue_backlog=i % 30,
                bandwidth_capacity_bps=2.0e6
            ))
        report = orchestrator.execute_operational_cycle(dt=0.05)
        self.assertEqual(report.active_nodes_count, 25)
        # Tactical squad of 25 nodes must execute under 1.5ms (1500us)
        self.assertLess(report.total_cycle_latency_us, 1500.0)

    def test_merkle_tamper_detection(self):
        ledger = PostQuantumEvidenceLedger()
        ledger.append_cycle_evidence(10.0, Vector3D(0, 0, 0), [], {})
        ledger.append_cycle_evidence(12.0, Vector3D(1, 0, 0), [], {})
        ledger.append_cycle_evidence(15.0, Vector3D(2, 0, 0), [], {})
        valid, _ = ledger.verify_chain_integrity()
        self.assertTrue(valid)

        # Deliberately mutate middle block hash
        ledger.chain[1].block_hash = "f" * 64
        tampered_valid, msg = ledger.verify_chain_integrity()
        self.assertFalse(tampered_valid)
        self.assertIn("Broken chain", msg)

    def test_multi_target_intercept_convergence(self):
        orchestrator = ApexOmniSwarmOrchestrator()
        orchestrator.register_node(NodeTelemetry(
            "STRIKE-ALPHA", "strike", Vector3D(0, 0, 50), Vector3D(0, 0, 0), 0.2, 80000, 0, 1e6
        ))
        orchestrator.record_sensor_observation(
            target_id="THREAT-1", target_type="CRUISE_MISSILE",
            observed_pos=Vector3D(200, 0, 50), sensor_uncertainty=0.1, reporting_node_id="SCOUT-X"
        )
        orchestrator.record_sensor_observation(
            target_id="THREAT-1", target_type="CRUISE_MISSILE",
            observed_pos=Vector3D(200, 1, 50), sensor_uncertainty=0.1, reporting_node_id="SCOUT-Y"
        )
        report = orchestrator.execute_operational_cycle(dt=0.05)
        # Strike alpha should receive commanded velocity pointing in positive X direction towards THREAT-1
        cmd_vel = report.actuation_commands["STRIKE-ALPHA"]
        self.assertGreater(cmd_vel.x, 0.0)


if __name__ == "__main__":
    unittest.main()
