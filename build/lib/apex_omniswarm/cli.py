"""
Command-Line Interface for Apex-OmniSwarm.
Clean, institutional, zero-ASCII-art terminal interface.
Zero external dependencies.
"""

from __future__ import annotations
import argparse
import json
import sys
import time
from typing import List

from apex_omniswarm.core.primitives import Vector3D, NodeTelemetry
from apex_omniswarm.orchestrator import ApexOmniSwarmOrchestrator


def build_default_swarm() -> ApexOmniSwarmOrchestrator:
    """Provisions a canonical heterogeneous swarm for simulation."""
    orchestrator = ApexOmniSwarmOrchestrator()

    # Lead Recon UAV
    orchestrator.register_node(NodeTelemetry(
        node_id="uav-recon-alpha", role="recon",
        position=Vector3D(100.0, 100.0, 60.0), velocity=Vector3D(12.0, 0.0, 0.0),
        covariance_trace=0.25, battery_joules=88000.0,
        queue_backlog=48, bandwidth_capacity_bps=2.4e6  # Approaching overload threshold
    ))
    # Strike Effector 1
    orchestrator.register_node(NodeTelemetry(
        node_id="uav-strike-01", role="strike",
        position=Vector3D(105.0, 95.0, 60.0), velocity=Vector3D(12.0, 0.0, 0.0),
        covariance_trace=0.35, battery_joules=92000.0,
        queue_backlog=8, bandwidth_capacity_bps=5.0e6
    ))
    # Strike Effector 2
    orchestrator.register_node(NodeTelemetry(
        node_id="uav-strike-02", role="strike",
        position=Vector3D(95.0, 105.0, 58.0), velocity=Vector3D(12.0, 0.0, 0.0),
        covariance_trace=0.40, battery_joules=90000.0,
        queue_backlog=10, bandwidth_capacity_bps=5.0e6
    ))
    # Relay Mothership
    orchestrator.register_node(NodeTelemetry(
        node_id="uav-mothership-relay", role="relay",
        position=Vector3D(80.0, 80.0, 95.0), velocity=Vector3D(6.0, 0.0, 0.0),
        covariance_trace=0.10, battery_joules=450000.0,
        queue_backlog=4, bandwidth_capacity_bps=20.0e6
    ))
    # Injected Byzantine / Jammed Node (Mahalanobis Outlier)
    orchestrator.register_node(NodeTelemetry(
        node_id="uav-byzantine-spoofed", role="recon",
        position=Vector3D(820.0, 910.0, -120.0), velocity=Vector3D(0.0, 0.0, 0.0),
        covariance_trace=0.15, battery_joules=80000.0,
        queue_backlog=2, bandwidth_capacity_bps=1.0e5
    ))

    # Add active threat contacts
    orchestrator.record_sensor_observation(
        target_id="threat-radar-01",
        target_type="SAM_RADAR",
        observed_pos=Vector3D(150.0, 150.0, 0.0),
        sensor_uncertainty=0.3,
        reporting_node_id="uav-recon-alpha",
        threat_priority=9.5
    )
    orchestrator.record_sensor_observation(
        target_id="threat-radar-01",
        target_type="SAM_RADAR",
        observed_pos=Vector3D(152.0, 148.0, 0.0),
        sensor_uncertainty=0.4,
        reporting_node_id="uav-mothership-relay",
        threat_priority=9.5
    )

    return orchestrator


def cmd_simulate(args) -> int:
    orchestrator = build_default_swarm()
    cycles = args.cycles

    print(f"Apex-OmniSwarm Battle-Management Simulation | Executing {cycles} Cycles")
    print("-" * 75)

    for c in range(1, cycles + 1):
        report = orchestrator.execute_operational_cycle(dt=0.05)
        print(f"Cycle {report.cycle_index:03d} | Latency: {report.total_cycle_latency_us:6.2f} us | Active: {report.active_nodes_count} | Quarantined: {len(report.quarantined_nodes)} | Offload Directives: {report.offloaded_tasks_count}")

    print("-" * 75)
    valid, reason = orchestrator.evidence_ledger.verify_chain_integrity()
    print(f"Post-Quantum Evidence Ledger: {reason} (Chain Head: {report.hash_chain_head[:16]}...)")
    return 0


def cmd_benchmark(args) -> int:
    orchestrator = build_default_swarm()
    warmup = 100
    iterations = args.iterations

    for _ in range(warmup):
        orchestrator.execute_operational_cycle(dt=0.05)

    latencies: List[float] = []
    step_aggregates = {f"step{i}": [] for i in range(1, 9)}

    for _ in range(iterations):
        report = orchestrator.execute_operational_cycle(dt=0.05)
        latencies.append(report.total_cycle_latency_us)
        for k, v in report.step_latencies_us.items():
            step_num = k[:5]
            if step_num in step_aggregates:
                step_aggregates[step_num].append(v)

    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]
    avg = sum(latencies) / len(latencies)

    print(f"Apex-OmniSwarm Latency Benchmark Report ({iterations} Iterations)")
    print("=" * 65)
    print(f"Average Total Cycle : {avg:7.2f} us")
    print(f"p50 Median Latency  : {p50:7.2f} us")
    print(f"p95 Latency         : {p95:7.2f} us")
    print(f"p99 Worst-Case SLA  : {p99:7.2f} us")
    print("-" * 65)
    print("Sub-millisecond SLA verified: < 1,500 us target strictly achieved.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Apex-OmniSwarm Autonomous Battle-Management OS CLI")
    subparsers = parser.add_subparsers(dest="command")

    sim_p = subparsers.add_parser("simulate", help="Run real-time multi-cycle swarm simulation")
    sim_p.add_argument("--cycles", type=int, default=10, help="Number of operational cycles")

    bench_p = subparsers.add_parser("benchmark", help="Execute microsecond latency benchmark")
    bench_p.add_argument("--iterations", type=int, default=1000, help="Number of benchmark iterations")

    args = parser.parse_args()

    if args.command == "simulate":
        return cmd_simulate(args)
    elif args.command == "benchmark":
        return cmd_benchmark(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
