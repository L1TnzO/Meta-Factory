#!/usr/bin/env bash
# modelgen_ab_gate.sh <producto> [shot.png] — acceptance gate of the ADR-023 §5 A/B experiment
# (FSK-FRONTEND-MODELGEN-AB). ONE command, exit 0 = everything green:
#   1. re-runs the REAL stations that MEASURE the frontend — s8 (a11y axe + perf bundle-budget) and
#      s9 (obs · access-control · consume · browser, live Chromium) — via the engine (`run_station`:
#      the same law, real verdicts to the product's proof bus) WITHOUT re-deriving s0, so the
#      model-native artifact in build/ is never clobbered by templates;
#   2. boots the live app (dev_run.sh, fresh PG) and runs the design-floor proof (+ screenshots).
# The design-floor probe (an entity with an optional field and no required refs, minimal body) is
# derived HERE from the product's effective spec — DATA, not domain knowledge (ADR-012).
# Two-sided: on the template frontend this gate ends RED at design-floor (the arm-A baseline);
# arm B must end GREEN through the very same commands.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"          # factories/full-stack-kotlin/tools
FACTORY_DIR="$(dirname "$HERE")"
ROOT="$(cd "$FACTORY_DIR/../.." && pwd)"
PRODUCT="${1:?usage: modelgen_ab_gate.sh <producto> [shot.png]}"
SHOT="${2:-}"

cd "$ROOT"
eval "$(bash tools/toolchain.sh ensure)"

# ── 1) real s8 + s9 through the engine (no s0 re-derivation) ─────────────────────────────────────────
PYTHONPATH=src python3 - "$PRODUCT" <<'PYEOF'
import sys
from pathlib import Path

from metafactory.cli import _meta_root, _subst_for
from metafactory.engine import RunContext, load_sequence, run_station
from metafactory.spec import load_spec

product = sys.argv[1]
chassis = Path("factories/full-stack-kotlin").resolve()
root = chassis / "products" / product
spec = load_spec(root / "factory.spec.yml")
subst = _subst_for(spec, root)
ctx = RunContext(root=root, meta_root=_meta_root(), slug="full-stack-kotlin", chassis=chassis)
pseq = load_sequence(root / "stations")
for sid in ("s8", "s9"):
    st = pseq.get(sid)
    if st is None:
        print(f"modelgen_ab_gate: station {sid} not found", file=sys.stderr)
        sys.exit(2)
    run = run_station(ctx, st, pseq, subst, stations_dir=root / "stations",
                      spec_path=root / "factory.spec.yml", record_active=True)
    if not (run.passed and run.gate.opened):
        print(f"modelgen_ab_gate: {sid} RED", file=sys.stderr)
        sys.exit(1)
    print(f"modelgen_ab_gate: {sid} green")
PYEOF

# ── 2) design-floor probe = DATA derived from the product spec (ADR-012) ─────────────────────────────
PROBE="$(PYTHONPATH=src python3 - "$PRODUCT" <<'PYEOF'
import json
import sys
from pathlib import Path

import yaml

spec = yaml.safe_load((Path("factories/full-stack-kotlin/products") / sys.argv[1] / "factory.spec.yml").read_text())
prod = spec["domain"]["product"]

def fill(f):
    t = f.get("type")
    if t == "enum":
        return f["values"][0]
    return {"string": f"df-{f['name']}", "int": 1, "number": 1.5, "boolean": True, "date": "2030-01-01"}.get(t)

for e in prod.get("entities", []):
    fields = e.get("fields", [])
    req = [f for f in fields if f.get("required", True)]
    opt = [f for f in fields if not f.get("required", True)]
    if opt and not any(f.get("type") == "ref" for f in req):
        roles = e.get("write_roles") or prod.get("roles") or []
        print(json.dumps({"entity": e["name"], "plural": e["name"].lower() + "s",
                          "role": roles[0] if roles else "", "body": {f["name"]: fill(f) for f in req}}))
        break
PYEOF
)"
PROBE="${PROBE:--}"

# ── 2b) form_contract = per-entity settable fields (all spec fields MINUS the server-set owner ref) ───
CONTRACT="$(PYTHONPATH=src python3 - "$PRODUCT" <<'PYEOF'
import json
import sys
from pathlib import Path

import yaml

spec = yaml.safe_load((Path("factories/full-stack-kotlin/products") / sys.argv[1] / "factory.spec.yml").read_text())
prod = spec["domain"]["product"]
contract = {}
for e in prod.get("entities", []):
    owner = e.get("owned_by")  # the owner ref is set server-side from the principal -> not a form control
    contract[e["name"]] = [f["name"] for f in e.get("fields", []) if f["name"] != owner]
print(json.dumps(contract))
PYEOF
)"
CONTRACT="${CONTRACT:--}"

# ── 3) live app (fresh PG) + design-floor (+ screenshots) ────────────────────────────────────────────
bash "$HERE/dev_run.sh" stop "$PRODUCT" >/dev/null 2>&1 || true
bash "$HERE/dev_run.sh" "$PRODUCT"
trap 'bash "$HERE/dev_run.sh" stop "$PRODUCT" >/dev/null 2>&1 || true' EXIT
URL="$(cat "${TMPDIR:-/tmp}/fsk-dev/$PRODUCT/url")"
if [ -n "$SHOT" ]; then SHOT="$(realpath -m "$SHOT")"; mkdir -p "$(dirname "$SHOT")"; fi   # absolute: design-floor runs with cwd=frontend
( cd "$FACTORY_DIR/products/$PRODUCT/build/product/frontend" &&
  exec node --experimental-strip-types --disable-warning=ExperimentalWarning \
    "$HERE/design_floor_check.ts" "$URL" "${SHOT:--}" "$PROBE" "$CONTRACT" )
echo "modelgen_ab_gate: design-floor green — full gate GREEN"
