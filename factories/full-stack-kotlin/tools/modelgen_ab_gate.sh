#!/usr/bin/env bash
# modelgen_ab_gate.sh <producto> [shot.png] — acceptance gate of the ADR-023 §5 A/B experiment
# (FSK-FRONTEND-MODELGEN-AB). ONE command, exit 0 = everything green:
#   1. re-runs the REAL stations that MEASURE the frontend — s8 (a11y axe + perf bundle-budget) and
#      s9 (obs · access-control · consume · browser, live Chromium) — via the engine (`run_station`:
#      the same law, real verdicts to the product's proof bus) WITHOUT re-deriving s0, so the
#      model-native artifact in build/ is never clobbered by templates;
#   2. boots the live app (dev_run.sh, fresh PG) and runs the design-floor proof (+ screenshots).
# The design-floor PROBE + form CONTRACT (DATA, not domain knowledge — ADR-012) are derived from the
# product's effective spec by tools/design_floor_probe.py, the SAME wrapper the s9 `frontend_design_floor`
# check runs, so this gate and the station share one source of the derivation.
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

# ── 2) live app (fresh PG) + design-floor over the LIVE app ──────────────────────────────────────────
# The design-floor PROBE + form CONTRACT are DATA derived from the product's effective spec (ADR-012). The
# derivation is single-sourced in tools/design_floor_probe.py — the SAME wrapper the s9 `frontend_design_floor`
# check runs — so this gate and the station can never drift. The wrapper self-locates design_floor_check.ts
# and runs it with cwd=frontend. On the template frontend it ends RED at design-floor (the arm-A baseline);
# arm B must end GREEN through this very command.
bash "$HERE/dev_run.sh" stop "$PRODUCT" >/dev/null 2>&1 || true
bash "$HERE/dev_run.sh" "$PRODUCT"
trap 'bash "$HERE/dev_run.sh" stop "$PRODUCT" >/dev/null 2>&1 || true' EXIT
URL="$(cat "${TMPDIR:-/tmp}/fsk-dev/$PRODUCT/url")"
python3 "$HERE/design_floor_probe.py" "$URL" "$FACTORY_DIR/products/$PRODUCT/factory.spec.yml" "${SHOT:--}"
echo "modelgen_ab_gate: design-floor green — full gate GREEN"
