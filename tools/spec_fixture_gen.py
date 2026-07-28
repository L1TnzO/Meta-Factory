"""spec_fixture_gen — derive the spec's GOLDEN VECTORS from live proofs, anchored to committed pins.

Why this exists: `docs/spec/` must be reconstruction-complete — someone rebuilding the system from the
documents alone needs an ORACLE for the kernel hash, and `.proof/` is NOT committed (only
`pinned_verdict.json` is). So the spec ships its own vectors, and this script derives them.

Honesty of the derivation (the reason a fabricated vector cannot enter the fixture):
  1. a vector is (station, checks[(name, exit)], proof_sha) read from a live proof;
  2. the sha stored in the proof must RECOMPUTE from its own checks (internal consistency, Lock #2);
  3. the sha must EQUAL the entry in the factory's COMMITTED `pinned_verdict.json` (pin anchoring).
A vector failing (2) or (3) is skipped and counted, never written. The committed pin is the authority;
this script only transcribes what the pin already attests.

Usage:  python3 tools/spec_fixture_gen.py [repo_root]        # writes docs/spec/fixtures/
Prints counts only — never proof content (context economy, I-7).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from seed.verifier import compute_proof_sha  # noqa: E402  (the current authority)

FIXTURE_REL = "docs/spec/fixtures/proof-sha-vectors.json"
SKIP_FILES = {"active.json", "ledger.json"}


def _proof_roots(root: Path) -> list[tuple[str, Path]]:
    """Every root that owns a pin: each factory, plus each named product instance."""
    out: list[tuple[str, Path]] = []
    for fdir in sorted((root / "factories").glob("*")):
        if not (fdir / "pinned_verdict.json").exists():
            continue
        out.append((fdir.name, fdir))
        for pdir in sorted((fdir / "products").glob("*")):
            if (pdir / "pinned_verdict.json").exists():
                out.append((f"{fdir.name}/{pdir.name}", pdir))
    return out


def collect(root: Path) -> tuple[list[dict], dict[str, int]]:
    vectors: list[dict] = []
    stats = {"roots": 0, "proofs": 0, "written": 0, "skip_inconsistent": 0,
             "skip_unpinned": 0, "skip_pin_mismatch": 0}
    for label, rdir in _proof_roots(root):
        stats["roots"] += 1
        pin = json.loads((rdir / "pinned_verdict.json").read_text(encoding="utf-8"))
        for pf in sorted((rdir / ".proof").glob("*.json")):
            if pf.name in SKIP_FILES:
                continue
            stats["proofs"] += 1
            try:
                proof = json.loads(pf.read_text(encoding="utf-8"))
                station = str(proof["station"])
                checks = [{"name": str(c["name"]), "exit": int(c["exit"])} for c in proof["checks"]]
                stored = str(proof["proof_sha"])
            except (KeyError, ValueError, TypeError, json.JSONDecodeError):
                stats["skip_inconsistent"] += 1
                continue
            if compute_proof_sha(station, checks) != stored:      # (2) internal consistency
                stats["skip_inconsistent"] += 1
                continue
            if station not in pin:                                 # (3) pin anchoring
                stats["skip_unpinned"] += 1
                continue
            if pin[station] != stored:
                stats["skip_pin_mismatch"] += 1
                continue
            vectors.append({
                "origin": label,
                "station": station,
                "checks": [[c["name"], c["exit"]] for c in checks],
                "proof_sha": stored,
            })
            stats["written"] += 1
    vectors.sort(key=lambda v: (v["origin"], v["station"]))
    return vectors, stats


def main(argv: list[str]) -> int:
    root = Path(argv[0]).resolve() if argv else Path(__file__).resolve().parents[1]
    vectors, stats = collect(root)
    if not vectors:
        print("VERDICT    spec-fixture-gen — FAIL   (exit 1)")
        print("SUMMARY    no pin-anchored vector could be derived; is `.proof/` present and current?")
        print(f"COUNTS     {stats}")
        return 1
    out = root / FIXTURE_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "_doc": "Golden vectors for the kernel hash. Derived by tools/spec_fixture_gen.py; every "
                "vector is anchored to a committed pinned_verdict.json entry. Regenerate, never edit.",
        "algorithm": "proof_sha = sha256(json.dumps({'station': id, 'checks': sorted[(name, exit)]}, "
                     "sort_keys=True, separators=(',',':')).encode()).hexdigest()",
        "vectors": vectors,
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print("VERDICT    spec-fixture-gen — PASS   (exit 0)")
    print(f"SUMMARY    {stats['written']} pin-anchored vector(s) from {stats['roots']} root(s) "
          f"→ {FIXTURE_REL}")
    print(f"COUNTS     {stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
