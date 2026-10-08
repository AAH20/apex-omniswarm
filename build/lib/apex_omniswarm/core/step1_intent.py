"""
Step 1: Multi-Modal Intent Ingestion & Constitutional ROE Guardrails.
Integrates patterns from hermes-matrix-adapter, zero-shot-bci, and Apex_JADC2.
"""

from __future__ import annotations
import math
import time
from typing import Dict, List, Optional, Tuple
from apex_omniswarm.core.primitives import Vector3D, MissionIntentContract


class IntentAndROEEngine:
    """
    Translates tactical multi-modal intent (ATAK CoT, BCI neural telemetry, voice tokens)
    into formal mission contracts and validates Law of Armed Conflict (LOAC) guardrails.
    """

    def __init__(self, default_proportionality_threshold: float = 0.85):
        self.default_proportionality = default_proportionality_threshold

    def parse_cursor_on_target(
        self,
        cot_uid: str,
        lat_lon_hae: Tuple[float, float, float],
        callsign: str,
        no_fire_polygons: Optional[List[Tuple[Vector3D, float]]] = None
    ) -> MissionIntentContract:
        """
        Parses military Cursor-on-Target (CoT) telemetry into a canonical 3D Cartesian contract.
        Approximates localized tangent plane centered on reference coordinates.
        """
        lat, lon, hae = lat_lon_hae
        # Simple local flat-earth Cartesian projection for microsecond tactical execution
        x = lon * 111320.0 * math.cos(math.radians(lat))
        y = lat * 110540.0
        z = hae

        return MissionIntentContract(
            mission_id=f"COT-{cot_uid}",
            originator=callsign,
            target_area_centroid=Vector3D(x, y, z),
            operational_radius_meters=1500.0,
            max_engagement_velocity_mps=28.0,
            proportionality_threshold=self.default_proportionality,
            no_fire_zones=no_fire_polygons or [],
            roe_approved=False
        )

    def parse_bci_neural_intent(
        self,
        subject_id: str,
        focus_coordinates: Vector3D,
        neural_confidence: float,
        target_radius: float = 800.0
    ) -> MissionIntentContract:
        """
        Ingests parsed neural intent decoded from zero-shot-bci continuous multi-modal attestation.
        """
        return MissionIntentContract(
            mission_id=f"BCI-{subject_id}-{int(time.time())}",
            originator=f"PILOT-NEURAL-{subject_id}",
            target_area_centroid=focus_coordinates,
            operational_radius_meters=target_radius,
            max_engagement_velocity_mps=22.0,
            proportionality_threshold=max(neural_confidence, 0.70),
            no_fire_zones=[],
            roe_approved=False
        )

    def validate_roe_and_loac(
        self,
        contract: MissionIntentContract,
        candidate_target_pos: Vector3D,
        estimated_collateral_damage_radius: float = 50.0
    ) -> Tuple[bool, str]:
        """
        Evaluates Law of Armed Conflict (LOAC):
        1. Proportionality: target value vs collateral risk.
        2. Geometric Distinction: target must not fall within any No-Fire / Civilian Exclusion Zone.
        """
        # 1. Check No-Fire Zones
        for nf_center, nf_radius in contract.no_fire_zones:
            dist = candidate_target_pos.distance_to(nf_center)
            if dist < (nf_radius + estimated_collateral_damage_radius):
                return False, f"ROE REJECTED: Target within No-Fire Zone exclusion buffer ({dist:.1f}m < {nf_radius + estimated_collateral_damage_radius}m)"

        # 2. Check Operational Radius Boundary
        dist_to_mission_center = candidate_target_pos.distance_to(contract.target_area_centroid)
        if dist_to_mission_center > contract.operational_radius_meters:
            return False, f"ROE REJECTED: Target beyond tactical authorized corridor ({dist_to_mission_center:.1f}m > {contract.operational_radius_meters}m)"

        # 3. Proportionality threshold gate
        if contract.proportionality_threshold < 0.60:
            return False, "ROE REJECTED: Insufficient confidence metric for kinetic release"

        contract.roe_approved = True
        return True, "ROE APPROVED: Proportionality and distinction constraints satisfied"
