"""rtm_tree — C4 gate: the build evidence tree (req → capability → station → proof → artifact) re-derives
from `.proof/` + artifacts, proven by BLOCKING. Reuses `verify/rtm.py` (single source, no duplicated law).

Three things, all against the REAL factory + a hermetic temp (never mutates the factory):
  1. baseline: the tree re-derives and ≥1 requirement is fully SATISFIED (else there is nothing to prove —
     the factory was not built; run the line first).
  2. PROOF tooth: in a hermetic copy, corrupt the proof of a SATISFIED requirement's station → that
     requirement must drop to UNSATISFIED (the M5 discipline, now through the whole tree).
  3. ARTIFACT tooth (NEW, C4): if a SATISFIED requirement declares an EXISTING artifact, remove it
     (hermetic) → that requirement must drop to UNSATISFIED — the stale-evidence tooth (the proof says
     passed but the artifact it certifies vanished). A factory whose SATISFIED reqs declare no artifact
     (a proxy, e.g. ASF) cannot exercise this tooth; it is REPORTED as N/A, never faked (SAFE-7).

Argv: <factory_root> <meta_root> [spec_path-rel]."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path


def _copy_evidence(verifier, src_root: Path, dst_root: Path, station_ids: list[str],
                   artifact_paths: list[str]) -> None:
    """Copy ONLY the evidence a requirement's tree reads — the proofs of its stations and the artifact
    files — into a hermetic dst_root, so build_tree(dst_root) re-derives the same baseline before we
    tamper. Minimal: we never copy the whole factory."""
    for sid in station_ids:
        p = verifier.proof_path(src_root, sid)
        if p.exists():
            dst = verifier.proof_path(dst_root, sid)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)
    for rel in artifact_paths:
        src = src_root / rel
        if src.exists() and src.is_file():
            dst = dst_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def _tamper_proof(verifier, proof_root: Path, sid: str) -> bool:
    """Flip an exit 0 → 9 in sid's proof: recompute_passed falls to False and proof_sha stops matching,
    so gate_recompute_ok rejects it. True if it could tamper (the proof has checks)."""
    p = verifier.proof_path(proof_root, sid)
    if not p.exists():
        return False
    proof = json.loads(p.read_text(encoding="utf-8"))
    checks = proof.get("checks", [])
    if not checks:
        return False
    checks[0]["exit"] = 9
    p.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    return True


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: rtm_tree <factory_root> <meta_root> [spec_path]", file=sys.stderr)
        return 2
    factory_root = Path(argv[0]).resolve()
    meta_root = Path(argv[1]).resolve()
    spec_rel = argv[2] if len(argv) > 2 else "factory.spec.yml"

    from ...engine import RunContext
    from ...spec.loader import load_spec
    from .. import rtm

    spec = load_spec(factory_root / spec_rel)
    v = RunContext(root=factory_root, meta_root=meta_root, slug=spec.slug).verifier

    # 1. baseline from the REAL tree: need ≥1 fully-SATISFIED requirement to prove the drop.
    nodes = rtm.build_tree(spec, v, factory_root)
    sat = [n for n in nodes if n.satisfied]
    if not sat:
        print("ÁRBOL SIN COBERTURA: ningún requisito SATISFIED — la fábrica no fue construida (corré la línea)")
        return 1

    # 2. PROOF tooth: corrupt a SATISFIED req's station proof (hermetic) → it must drop to UNSATISFIED.
    target = next(n for n in sat if n.stations)
    tmp = Path(tempfile.mkdtemp(prefix="rtm_tree_"))
    try:
        _copy_evidence(v, factory_root, tmp, [s.sid for s in target.stations],
                       [a.path for a in target.artifacts])
        if not _tamper_proof(v, tmp, target.stations[0].sid):
            print(f"NO VERIFICABLE: no pude corromper el proof de {target.stations[0].sid} (¿sin checks?)")
            return 1
        after = {n.rid: n.satisfied for n in rtm.build_tree(spec, v, tmp)}
        if after.get(target.rid):
            print(f"ÁRBOL DECORATIVO: corromper el proof de {target.stations[0].sid} NO cambió {target.rid} "
                  f"(el árbol no se re-deriva de .proof/ — sería prosa)")
            return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # 3. ARTIFACT tooth (C4): pick a SATISFIED req with an existing declared artifact; remove it (hermetic)
    #    → it must drop to UNSATISFIED. The stale-evidence tooth. N/A (reported) when no req declares one.
    art_target = next((n for n in sat if any(a.exists for a in n.artifacts)), None)
    artifact_tooth = "N/A (ningún requisito SATISFIED declara un artefacto — proxy/legacy)"
    if art_target is not None:
        tmp2 = Path(tempfile.mkdtemp(prefix="rtm_tree_art_"))
        try:
            _copy_evidence(v, factory_root, tmp2, [s.sid for s in art_target.stations],
                           [a.path for a in art_target.artifacts])
            gone = next(a.path for a in art_target.artifacts if a.exists)
            (tmp2 / gone).unlink()
            after = {n.rid: n.satisfied for n in rtm.build_tree(spec, v, tmp2)}
            if after.get(art_target.rid):
                print(f"ÁRBOL DECORATIVO (artefacto): borrar {gone} NO cambió {art_target.rid} "
                      f"(la hoja proof→artifact no se re-deriva — evidencia rancia no detectada)")
                return 1
            artifact_tooth = f"borrar {gone} tira {art_target.rid} a UNSATISFIED"
        finally:
            shutil.rmtree(tmp2, ignore_errors=True)

    print(f"OK árbol vivo: {len(sat)}/{len(nodes)} SATISFIED re-derivado de .proof/+artefactos; "
          f"corromper {target.stations[0].sid} tira {target.rid} a UNSATISFIED; artefacto: {artifact_tooth}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
