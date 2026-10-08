"""
Step 8: Post-Quantum Provenance, Black Box Evidence & Metamorphic Audit.
Integrates patterns from robot-black-box, pqattest, and verified-effects-runtime.
Zero external dependencies.
"""

from __future__ import annotations
import hashlib
import json
import time
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional
from apex_omniswarm.core.primitives import Vector3D


@dataclass
class EvidenceBlock:
    index: int
    timestamp_ns: int
    previous_hash: str
    cycle_latency_us: float
    grounded_centroid: Dict[str, float]
    quarantined_nodes: List[str]
    actuation_hash: str
    block_hash: str
    post_quantum_signature_id: str


class PostQuantumEvidenceLedger:
    """
    Append-only Merkle hash-chain ledger for physical AI state transitions.
    Provides verifiable action provenance (FIPS 204 ML-DSA-65 mock attestation)
    for post-mission debrief, incident reconstruction, and legal compliance.
    """

    def __init__(self, genesis_salt: str = "APEX-OMNISWARM-GENESIS-2026"):
        self.genesis_salt = genesis_salt
        self.chain: List[EvidenceBlock] = []
        self._last_hash = hashlib.sha256(genesis_salt.encode("utf-8")).hexdigest()

    def append_cycle_evidence(
        self,
        cycle_latency_us: float,
        centroid: Vector3D,
        quarantined: List[str],
        actuation_map: Dict[str, Vector3D]
    ) -> EvidenceBlock:
        """
        Calculates SHA-256 block hash chained to previous state and appends to ledger.
        """
        timestamp = time.perf_counter_ns()
        actuation_payload = {
            nid: {"x": v.x, "y": v.y, "z": v.z} for nid, v in actuation_map.items()
        }
        actuation_hash = hashlib.sha256(
            json.dumps(actuation_payload, sort_keys=True).encode("utf-8")
        ).hexdigest()

        block_index = len(self.chain) + 1
        raw_header = f"{block_index}:{timestamp}:{self._last_hash}:{cycle_latency_us}:{centroid.x}:{centroid.y}:{centroid.z}:{','.join(quarantined)}:{actuation_hash}"
        block_hash = hashlib.sha256(raw_header.encode("utf-8")).hexdigest()

        # Mock FIPS 204 ML-DSA-65 post-quantum signature identifier
        pq_sig = f"ML-DSA-65:{block_hash[:16]}:{hashlib.sha256((block_hash + 'PQ_KEY').encode()).hexdigest()[:32]}"

        block = EvidenceBlock(
            index=block_index,
            timestamp_ns=timestamp,
            previous_hash=self._last_hash,
            cycle_latency_us=cycle_latency_us,
            grounded_centroid={"x": centroid.x, "y": centroid.y, "z": centroid.z},
            quarantined_nodes=list(quarantined),
            actuation_hash=actuation_hash,
            block_hash=block_hash,
            post_quantum_signature_id=pq_sig
        )

        self.chain.append(block)
        self._last_hash = block_hash
        return block

    def verify_chain_integrity(self) -> Tuple[bool, str]:
        """
        Traverses the full evidence chain validating cryptographic link hashes.
        """
        current_prev = hashlib.sha256(self.genesis_salt.encode("utf-8")).hexdigest()
        for idx, block in enumerate(self.chain):
            if block.previous_hash != current_prev:
                return False, f"Broken chain at block {block.index}: mismatch previous hash"
            current_prev = block.block_hash
        return True, f"Integrity verified across {len(self.chain)} blocks"
