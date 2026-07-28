"""spec_schema_cover — proves `docs/spec/` documents every key the system actually reads or writes.

Level L2 of the conformance ladder (§12.1). The failure mode it exists to prevent is the one that
kills every re-specification project: the document describes the eight interesting fields and quietly
omits the three boring ones, and the re-implementer discovers them only when a pin refuses to
reproduce.

Method: collect the vocabulary from REAL artifacts on disk (not from prose), bucket it, and require
each term to appear literally in `docs/spec/*.md`. Collection is bounded to structural positions —
top-level keys, entry keys of the known containers — so that domain data (entity names, field names
of a particular product) never leaks into the requirement.

Two-sided: with SPEC_SCHEMA_SABOTAGE=1 a phantom term is injected and the gate MUST fail.

Usage:  python3 tools/spec_schema_cover.py [repo_root]
"""
from __future__ import annotations

import ast
import json
import os
import re
import sys
from pathlib import Path

import yaml

SPEC_DIR = "docs/spec"
PHANTOM = "zzphantomkeyzz"
MAX_REPORT = 4


def _keys(obj) -> set[str]:
    return set(map(str, obj.keys())) if isinstance(obj, dict) else set()


def _entry_keys(obj, field: str) -> set[str]:
    """Union of the keys of every mapping inside obj[field] (a list of entries)."""
    out: set[str] = set()
    if isinstance(obj, dict):
        for entry in obj.get(field) or []:
            out |= _keys(entry)
    return out


def _yaml(path: Path):
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return None


def collect(root: Path) -> dict[str, set[str]]:
    v: dict[str, set[str]] = {k: set() for k in
                              ("proof", "station", "factory_spec", "product", "slot", "kinds", "gates")}

    # ── proofs: the record and its check entries ────────────────────────────────
    for pf in root.glob("factories/*/.proof/*.json"):
        if pf.name in {"active.json", "ledger.json"}:
            continue
        try:
            proof = json.loads(pf.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        v["proof"] |= _keys(proof) | _entry_keys(proof, "checks")

    # ── station YAMLs: meta line and every factory line ─────────────────────────
    for sy in list(root.glob("src/metafactory/stations/*.yml")) + list(root.glob("factories/*/stations/*.yml")):
        st = _yaml(sy)
        v["station"] |= _keys(st) | _entry_keys(st, "checks") | _entry_keys(st, "builds")

    # ── factory specs: top level + the governed sub-objects + station entries ───
    for fs in list(root.glob("factories/*/factory.spec.yml")) + list(root.glob("specs/*.yml")):
        spec = _yaml(fs)
        if not isinstance(spec, dict):
            continue
        v["factory_spec"] |= _keys(spec)
        for sub in ("factory", "domain", "factory_substrate", "governance", "machinery"):
            v["factory_spec"] |= _keys(spec.get(sub))
        v["factory_spec"] |= _entry_keys(spec.get("domain"), "station_sequence")

    # ── product blueprints: top level + entity + field entries ──────────────────
    for pb in root.glob("factories/*/products/*/product.yml"):
        blue = _yaml(pb)
        if not isinstance(blue, dict):
            continue
        v["product"] |= _keys(blue)
        for ent in blue.get("entities") or []:
            v["product"] |= _keys(ent)
            for fld in (ent.get("fields") if isinstance(ent, dict) else None) or []:
                v["product"] |= _keys(fld)

    # ── slot law: the constants ARE the schema ─────────────────────────────────
    sys.path.insert(0, str(root))
    try:
        from seed import delegation
        v["slot"] |= set(delegation.MANIFEST_REQUIRED_KEYS) | set(delegation.VERDICT_REQUIRED_KEYS)
        for name in ("MANIFEST_OPTIONAL_KEYS", "MANIFEST_ENUM_KEYS"):
            v["slot"] |= set(getattr(delegation, name, ()) or ())
    except Exception:                                            # noqa: BLE001
        pass
    for mf in root.glob(".gen/*slot*.json"):
        try:
            v["slot"] |= _keys(json.loads(mf.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            pass

    # ── the two frozen vocabularies ────────────────────────────────────────────
    sys.path.insert(0, str(root / "src"))
    try:
        from metafactory.verify.checks.registry import KINDS
        v["kinds"] |= set(KINDS)
    except Exception:                                            # noqa: BLE001
        pass
    v["gates"] |= _gate_names(root / "src" / "metafactory" / "cli.py")
    return v


def _gate_names(cli_py: Path) -> set[str]:
    """Extract the gate names from the `checks = [...]` literal inside cmd_check (ast, not regex)."""
    try:
        tree = ast.parse(cli_py.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "cmd_check":
            names: set[str] = set()
            for sub in ast.walk(node):
                if isinstance(sub, ast.Dict):
                    for k, val in zip(sub.keys, sub.values):
                        if (isinstance(k, ast.Constant) and k.value == "name"
                                and isinstance(val, ast.Constant) and isinstance(val.value, str)):
                            names.add(val.value)
            return names
    return set()


def main(argv: list[str]) -> int:
    root = Path(argv[0]).resolve() if argv else Path(__file__).resolve().parents[1]
    vocab = collect(root)
    if os.environ.get("SPEC_SCHEMA_SABOTAGE") == "1":
        vocab["proof"].add(PHANTOM)

    text = "\n".join(p.read_text(encoding="utf-8")
                     for p in sorted((root / SPEC_DIR).glob("*.md")))
    missing: dict[str, list[str]] = {}
    total = covered = 0
    for bucket, terms in sorted(vocab.items()):
        for term in sorted(terms):
            total += 1
            if re.search(rf"(?<![\w-]){re.escape(term)}(?![\w-])", text):
                covered += 1
            else:
                missing.setdefault(bucket, []).append(term)

    if os.environ.get("SPEC_SCHEMA_SABOTAGE") == "1":
        if PHANTOM in missing.get("proof", []):
            print("VERDICT    spec-schema-cover (SABOTAGE) — PASS   (exit 0)")
            print("SUMMARY    the phantom key was detected as undocumented, as it must be")
            return 0
        print("VERDICT    spec-schema-cover (SABOTAGE) — FAIL   (exit 1)")
        print("SUMMARY    GATE DECORATIVO: a phantom key passed as documented")
        return 1

    if missing:
        n = sum(len(v) for v in missing.values())
        print("VERDICT    spec-schema-cover — FAIL   (exit 1)")
        print(f"SUMMARY    {n} undocumented term(s) of {total}; the spec is not transcribable yet")
        for bucket, terms in sorted(missing.items()):
            shown = ", ".join(terms[:MAX_REPORT])
            more = f" (+{len(terms) - MAX_REPORT})" if len(terms) > MAX_REPORT else ""
            print(f"FAILURES   {bucket}: {shown}{more}")
        print(f"NEXT       document them in {SPEC_DIR}/13-schemas.md")
        return 1
    print("VERDICT    spec-schema-cover — PASS   (exit 0)")
    print(f"SUMMARY    {covered}/{total} real artifact terms documented across "
          f"{len(vocab)} bucket(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
