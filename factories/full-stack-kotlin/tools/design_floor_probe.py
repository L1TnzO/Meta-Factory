#!/usr/bin/env python3
"""design_floor_probe.py — derive the design-floor PROBE + form CONTRACT from a product's effective spec
(DATA, ADR-012) and run the product-AGNOSTIC `design_floor_check.ts` against the LIVE app.

Single source of the derivation, shared by TWO callers so the heredocs never drift:
  * the s9 `frontend_design_floor` check (opt-in via `when: {frontend_surface: model-native}`), run with
    cwd = the product's `build/product`, invoking us as `../../../../tools/design_floor_probe.py`;
  * `modelgen_ab_gate.sh` (the ADR-023 §5 A/B acceptance gate).

`design_floor_check.ts` names no domain (it takes JSON args) and stays factory-level next to us: we
self-locate it via `__file__` and derive the frontend dir from the spec path — nothing here is coupled to
the build-tree depth beyond the product_root anchor. It runs with cwd = the product's `frontend/` so
`playwright-core` resolves from THAT node_modules (the tool stays factory-level, the runtime stays
product-level). Reading the plan is Python's job (ADR-012); the `.ts` only renders/checks.

Derivation (copied verbatim from modelgen_ab_gate.sh §2/§2b — this IS that single source now):
  PROBE    = the first entity with an optional field and no required ref, its required fields filled. The
             omitted optionals FORCE the live null-case the `nullcell` axis floors.
  CONTRACT = per-entity settable fields = every spec field MINUS the server-set owner ref (the `fields`
             axis: the create form must offer a control for each).

Exit code propagates the `.ts` verdict (0 floor holds · 1 violations · 2 infra error — not a verdict).
Usage: design_floor_probe.py <base_url> <spec_path> [screenshot.png|-]
"""
import json
import subprocess
import sys
from pathlib import Path

import yaml


def _fill(f: dict):
    """A deterministic non-empty value for a required field, per its declared type."""
    t = f.get("type")
    if t == "enum":
        return f["values"][0]
    return {"string": f"df-{f['name']}", "int": 1, "number": 1.5,
            "boolean": True, "date": "2030-01-01"}.get(t)


def probe(prod: dict) -> str:
    """First entity with an optional field and no required ref -> a create with its optionals OMITTED
    (so the live row carries nulls). `-` when the product has no such entity."""
    for e in prod.get("entities", []):
        fields = e.get("fields", [])
        req = [f for f in fields if f.get("required", True)]
        opt = [f for f in fields if not f.get("required", True)]
        if opt and not any(f.get("type") == "ref" for f in req):
            roles = e.get("write_roles") or prod.get("roles") or []
            return json.dumps({
                "entity": e["name"], "plural": e["name"].lower() + "s",
                "role": roles[0] if roles else "",
                "body": {f["name"]: _fill(f) for f in req},
            })
    return "-"


def contract(prod: dict) -> str:
    """Per-entity settable fields = all spec fields minus the server-set owner ref."""
    out = {}
    for e in prod.get("entities", []):
        owner = e.get("owned_by")  # the owner ref is set server-side from the principal -> not a form control
        out[e["name"]] = [f["name"] for f in e.get("fields", []) if f["name"] != owner]
    return json.dumps(out)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: design_floor_probe.py <base_url> <spec_path> [screenshot.png|-]", file=sys.stderr)
        return 2
    base_url, spec_path = argv[0], argv[1]
    shot = argv[2] if len(argv) > 2 and argv[2] else "-"

    ts = Path(__file__).resolve().parent / "design_floor_check.ts"
    spec_file = Path(spec_path).resolve()
    frontend = spec_file.parent / "build" / "product" / "frontend"

    spec = yaml.safe_load(spec_file.read_text(encoding="utf-8")) or {}
    prod = (spec.get("domain", {}) or {}).get("product", {}) or {}

    if shot != "-":
        shot = str(Path(shot).resolve())  # absolute: the .ts runs with cwd=frontend
        Path(shot).parent.mkdir(parents=True, exist_ok=True)

    cmd = ["node", "--experimental-strip-types", "--disable-warning=ExperimentalWarning",
           str(ts), base_url, shot, probe(prod), contract(prod)]
    return subprocess.run(cmd, cwd=frontend).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
