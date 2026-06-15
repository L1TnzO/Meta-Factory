"""rtm — the build EVIDENCE TREE (C4): req → capability → station → proof → artifact, re-derived ONLY
from the spec + `.proof/` + the artifacts on disk (SAFE-4, I-10). Not from prose.

Single source for BOTH `meta rtm` (display, bounded to the verdict bus) and the `rtm_tree` gate (block) —
the same law, no duplication (the discipline of `rederive_pinned`, ADR-005 §4). A requirement is SATISFIED
iff EVERY edge of its tree holds:

  - it maps to ≥1 station (`satisfied_by`)                          [closure — also M0]
  - its declared capability (if any) is a real capability           [L5→L1 edge — also M0]
  - every station's proof is present AND gate-recompute-OK          [station→proof, lock #2]
  - every artifact its capability declares EXISTS on disk           [proof→artifact leaf, the C4 tooth]

A broken edge anywhere drops the requirement to UNSATISFIED. The artifact leaf catches STALE EVIDENCE: a
proof that says passed while the artifact it certifies vanished — distinct from M5 (flips an exit code) and
M6 (full rebuild). Where a capability declares no artifact (a proxy/legacy factory), the leaf is empty: we
do not fabricate an edge the spec never declared (honest, SAFE-7).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class StationNode:
    sid: str
    proof_open: bool   # proof present AND gate-recompute-OK (lock #2)
    sha: str = ""      # the proof_sha (first 12), for the trace


@dataclass
class ArtifactNode:
    path: str
    exists: bool


@dataclass
class ReqNode:
    rid: str
    capability: str
    capability_ok: bool          # capability declared (or none declared) — the L5→L1 edge
    stations: list[StationNode] = field(default_factory=list)
    artifacts: list[ArtifactNode] = field(default_factory=list)

    @property
    def satisfied(self) -> bool:
        return (bool(self.stations)
                and self.capability_ok
                and all(s.proof_open for s in self.stations)
                and all(a.exists for a in self.artifacts))

    def broken_edge(self) -> str:
        """A short reason for the FIRST broken edge (for the bounded bus line). '' if satisfied."""
        if not self.stations:
            return "sin estación (satisfied_by vacío)"
        if not self.capability_ok:
            return f"capability fantasma {self.capability!r}"
        shut = [s.sid for s in self.stations if not s.proof_open]
        if shut:
            return "proof SHUT: " + ",".join(shut)
        missing = [a.path for a in self.artifacts if not a.exists]
        if missing:
            return "artefacto ausente: " + ",".join(missing)
        return ""


def _caps_by_id(spec) -> dict:
    return {c.id: c for c in spec.capabilities if c.id}


def build_tree(spec, verifier, factory_root) -> list[ReqNode]:
    """Re-derive the evidence tree for every requirement from the spec + `.proof/` + artifacts on disk."""
    root = Path(factory_root)
    caps = _caps_by_id(spec)
    nodes: list[ReqNode] = []
    for req in spec.requirements:
        cap_ok = (not req.capability) or (req.capability in caps)
        stations: list[StationNode] = []
        for sid in req.satisfied_by:
            proof = verifier.load_proof(root, sid)
            ok = proof is not None and verifier.gate_recompute_ok(proof)[0]
            stations.append(StationNode(sid, ok, str((proof or {}).get("proof_sha", ""))[:12]))
        artifacts: list[ArtifactNode] = []
        cap = caps.get(req.capability) if req.capability else None
        if cap and cap.artifact:
            artifacts.append(ArtifactNode(cap.artifact, (root / cap.artifact).exists()))
        nodes.append(ReqNode(req.id, req.capability, cap_ok, stations, artifacts))
    return nodes


def is_complete(nodes: list[ReqNode]) -> bool:
    return bool(nodes) and all(n.satisfied for n in nodes)


def render(slug: str, nodes: list[ReqNode]) -> str:
    """Bounded verdict-bus render (I-7): one line per requirement with its trace; the broken edge is
    annotated only when UNSATISFIED. req → capability → station(proof) → artifact, all on one line."""
    nsat = sum(1 for n in nodes if n.satisfied)
    complete = is_complete(nodes)
    out = [f"VEREDICTO  rtm {slug} — {'COMPLETE' if complete else 'INCOMPLETE'}   (exit {0 if complete else 1})",
           f"RESUMEN    {nsat}/{len(nodes)} requisitos SATISFIED (árbol re-derivado de .proof/ + artefactos)"]
    for n in nodes:
        status = "SATISFIED" if n.satisfied else "UNSATISFIED"
        cap = n.capability or "-"
        chain = " ".join(f"{s.sid}{'' if s.proof_open else '(SHUT)'}" for s in n.stations) or "(sin estación)"
        arts = " ".join(f"{a.path}{'✓' if a.exists else '✗'}" for a in n.artifacts)
        line = f"           {n.rid} {status} <- {cap}: {chain}"
        if arts:
            line += f" [{arts}]"
        if not n.satisfied:
            line += f"  — {n.broken_edge()}"
        out.append(line)
    return "\n".join(out)
