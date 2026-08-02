"""v3.host.verbs — the CLI verb BODIES for the run-shaped surface: `verify`, `station`, `product-run`,
`pin`, `promote`, `product`.

Extracted out of `v3.cli` (V3-INC12 P4, `.gen/CONTRACT-v3-tool-surface.md`) so the CLI and
`v3.control.tools`'s §10.3 tool surface call the exact SAME functions — `§10.3` is explicit: "The
`meta` CLI does not disappear ... it becomes a thin argparse shell over the same functions, so there
is exactly one implementation." A tool surface that re-implemented these bodies would be the second
implementation that sentence forbids.

A MOVE, not a redesign. Every body below is `v3.cli`'s former `_cmd_verify` / `_cmd_station` /
`_cmd_product_run` / `_cmd_pin` / `_cmd_promote` / `_cmd_product`, byte-for-byte, with exactly ONE
mechanical change throughout: each function now RETURNS its `Verdict` instead of calling `.emit()` on
it, so a caller decides how to surface it — `v3.cli.main()` still calls `.emit()` at its single call
site (identical printed output, identical exit code), while `v3.control.tools` reads the structured
fields directly (I-7: never captured stdout). `cli_parity`/`verb_census` never read this file: they
derive from `build_parser()`/`DISPATCH`, which stay in `v3.cli` untouched.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from ..kernel.report import Verdict

_ROOT = Path(__file__).resolve().parents[2]


def _load_line(root: Path, spec_path: Path, chassis: Path):
    """The (spec, resolved line) pair `station`/`verify` need — the DEFAULT-product half of
    `v3.verify.rederive`'s wiring (no instance materialization here: both verbs act on an already
    materialized `stations/` directory, exactly like `verify`'s `.proof/active.json` always names)."""
    from .line import load_stations, resolve_line
    from ..spec.loader import load_spec
    spec = load_spec(spec_path)
    raw = load_stations(chassis)
    return spec, resolve_line(raw, spec.subst)


def verify(ns) -> Verdict:
    """Re-run the ACTIVE station `.proof/active.json` names (Lock #3). No active station, or one that
    no longer names anything real, is a PASS — never a failure: there is nothing to block on."""
    from .builds import BuildContext, apply_builds
    from .runner import RunContext, run_station

    active_path = _ROOT / ".proof" / "active.json"
    if not active_path.is_file():
        return Verdict("verify", 0, "no active station to re-verify")
    try:
        active = json.loads(active_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return Verdict("verify", 0, f"no active station to re-verify (active.json unreadable: "
                       f"{exc!r})")

    root = Path(active.get("root") or "")
    station_id = active.get("station")
    spec_path = Path(active["spec"]) if active.get("spec") else (root / "factory.spec.yml")
    if not root.is_dir() or not station_id or not spec_path.is_file():
        return Verdict("verify", 0, "no active station to re-verify (active.json incomplete)")

    spec, line = _load_line(root, spec_path, root)
    target_station = next((s for s in line if str(s.get("id")) == str(station_id)), None)
    if target_station is None:
        return Verdict("verify", 0, f"unknown active station {station_id!r}; nothing to block")

    ctx = RunContext(root=root, home=_ROOT, proof_dir=root / ".proof", pythonpath=str(_ROOT))
    build_ctx = BuildContext(root=root, meta_root=_ROOT, subst=spec.subst, chassis=root)
    ctx.builder = lambda st, _ctx: apply_builds(st, build_ctx)
    outcome = run_station(target_station, line, ctx)
    if not outcome.ran:
        return Verdict("verify", 1, f"{station_id}: may not run — "
                       f"{'; '.join(outcome.blockers) or 'blocked'}")
    return Verdict("verify", 0 if outcome.passed else 1,
                   f"{station_id}: re-verified {'green' if outcome.passed else 'RED'}",
                   counts={"attempts": outcome.attempts})


def station(ns) -> Verdict:
    from .builds import BuildContext, apply_builds
    from .runner import RunContext, run_station

    fdir = _ROOT / "factories" / ns.factory
    spec_path = fdir / "factory.spec.yml"
    if not spec_path.is_file():
        return Verdict(f"station {ns.id}", 1, f"no such factory {ns.factory!r} "
                       f"({spec_path} not found)")
    spec, line = _load_line(fdir, spec_path, fdir)
    target_station = next((s for s in line if str(s.get("id")) == ns.id), None)
    if target_station is None:
        return Verdict(f"station {ns.id}", 1, f"station {ns.id} does not exist in "
                       f"{ns.factory}'s line")

    ctx = RunContext(root=fdir, home=_ROOT, proof_dir=fdir / ".proof", pythonpath=str(_ROOT))
    build_ctx = BuildContext(root=fdir, meta_root=_ROOT, subst=spec.subst, chassis=fdir)
    ctx.builder = lambda st, _ctx: apply_builds(st, build_ctx)
    outcome = run_station(target_station, line, ctx)
    if not outcome.ran:
        return Verdict(f"station {ns.id}", 1, f"{ns.id}: may not run — "
                       f"{'; '.join(outcome.blockers) or 'blocked'}")
    # On RED only: the run log's bounded line is the escape hatch (INC-12 P1) — a caller reads this
    # one line, then goes to the log itself if it needs more; the full text never rides the verdict.
    next_action = outcome.log_summary if not outcome.passed and outcome.log_summary else None
    return Verdict(f"station {ns.id}", 0 if outcome.passed else 1,
                   f"{ns.id}: {'green' if outcome.passed else 'RED'}",
                   counts={"attempts": outcome.attempts}, next_action=next_action)


def product_run(ns) -> Verdict:
    from .builds import BuildContext, apply_builds
    from .line import load_stations, materialize_stations, resolve_line
    from .runner import RunContext, run_line
    from ..spec.loader import load_spec
    from ..verify.rederive import apply_activation, materialize_instance, targets

    fdir = _ROOT / "factories" / ns.factory
    if not fdir.is_dir():
        return Verdict("product-run", 1, f"no such factory {ns.factory!r}")
    target = next((t for t in targets(fdir, ns.factory) if t.product == ns.product), None)
    if target is None:
        return Verdict("product-run", 1, f"no such product {ns.product!r} in {ns.factory!r}")

    overrides: dict[str, str] = {}
    if target.product:
        overrides = materialize_instance(target)
    spec = load_spec(target.root / "factory.spec.yml")
    raw = materialize_stations(spec) if target.product else load_stations(target.chassis)
    line = resolve_line(raw, spec.subst)
    if overrides:
        line = apply_activation(line, overrides, target.label)
    if not line:
        return Verdict("product-run", 1, f"{target.label}: the line selects zero stations")

    ctx = RunContext(root=target.root, home=_ROOT, proof_dir=target.root / ".proof",
                     pythonpath=str(_ROOT), dial=ns.mode)
    build_ctx = BuildContext(root=target.root, meta_root=_ROOT, subst=spec.subst, chassis=target.chassis)
    ctx.builder = lambda st, _ctx: apply_builds(st, build_ctx)

    outcomes = run_line(line, ctx)
    label = f"product-run {target.label}"
    if not outcomes:
        return Verdict(label, 1, "the line selected zero stations")
    last = outcomes[-1]
    ok = all(o.ran and o.passed for o in outcomes)
    if ok:
        return Verdict(label, 0, f"{last.station}: line green ({len(outcomes)} station(s) run)",
                       counts={"stations": len(outcomes)})
    reason = "; ".join(last.blockers) if last.blockers else f"{last.station} failed its checks"
    # On RED only, same escape hatch as `station` (INC-12 P1): "" when the station never ran.
    return Verdict(label, 1, f"{last.station}: {reason}", counts={"stations": len(outcomes)},
                   next_action=last.log_summary or None)


def _pin_from_line(target, line: list[dict]) -> tuple[bool, dict | str]:
    """Assemble a `{station: proof_sha}` map from the CURRENT established proofs of `target`'s ACTIVE
    stations — v2's `_pin_from_proofs`, composed from ported v3 primitives rather than a second law:
    `kernel.sequence.active_in` picks the active set, `host.runner.established` is the Lock #2 belief
    check (proof present + recomputes + passed), `RunContext.load_proofs` reads what a prior
    `station`/`product-run` run already left on disk. Returns `(True, the map)`, or `(False, the id of
    the first station with no established proof)` — it never invents one by running anything itself."""
    from .runner import RunContext, established
    from ..kernel.sequence import active_in

    ctx = RunContext(root=target.root, home=_ROOT, proof_dir=target.root / ".proof",
                     pythonpath=str(_ROOT))
    proofs = ctx.load_proofs()
    pinned: dict[str, str] = {}
    for st in line:
        if not active_in(st):
            continue
        sid = str(st.get("id"))
        proof = proofs.get(sid)
        if not established(proof):
            return False, sid
        pinned[sid] = proof["proof_sha"]
    return True, pinned


def pin(ns) -> Verdict:
    """Write the pinned verdict from the target's current (honest, on-disk) proofs. `--verify`
    (B11-equivalent): after pinning, re-derive it on a staged clean copy and confirm it matches
    (`v3.verify.rederive.rederive` — the SAME resolution `ci`/`product-run` use, not a second one)."""
    from .line import load_stations, materialize_stations, resolve_line
    from ..spec.loader import load_spec
    from ..verify.rederive import apply_activation, materialize_instance, targets

    fdir = _ROOT / "factories" / ns.factory
    if not fdir.is_dir():
        return Verdict("pin", 1, f"no such factory {ns.factory!r}")
    target = next((t for t in targets(fdir, ns.factory) if t.product == ns.product), None)
    if target is None:
        return Verdict("pin", 1, f"no such product {ns.product!r} in {ns.factory!r}")

    overrides = materialize_instance(target) if target.product else {}
    spec = load_spec(target.root / "factory.spec.yml")
    raw = materialize_stations(spec) if target.product else load_stations(target.chassis)
    line = resolve_line(raw, spec.subst)
    if overrides:
        line = apply_activation(line, overrides, target.label)
    if not line:
        return Verdict("pin", 1, f"{target.label}: the line selects zero stations")

    ok, pinned_or_station = _pin_from_line(target, line)
    if not ok:
        return Verdict("pin", 1,
                       f"{target.label}: {pinned_or_station} has no established green proof — run "
                       f"`v3 station {pinned_or_station} --factory {ns.factory}` or `v3 product-run "
                       f"--factory {ns.factory}` first")
    (target.root / "pinned_verdict.json").write_text(
        json.dumps(pinned_or_station, indent=2) + "\n", encoding="utf-8")
    label = f"pin {target.label}"
    if not ns.verify:
        return Verdict(label, 0,
                       f"pinned {len(pinned_or_station)} proof_sha in pinned_verdict.json")

    from ..verify.rederive import rederive
    ok2, problems, counts = rederive(_ROOT, ns.factory, product=ns.product)
    return Verdict(f"{label} --verify", 0 if ok2 else 1,
                   f"pinned {len(pinned_or_station)} proof_sha; clean-tree re-derivation: "
                   f"{counts.get('matched', 0)}/{counts.get('pinned', 0)} == pin",
                   failures=() if ok2 else tuple(problems))


def promote(ns) -> Verdict:
    """v2's `promote` drives `verify.checks.blast_radius` (a clean-clone sweep of every downstream
    factory) + `verify.checks.scenario_corpus` (G2: the engine still behaves across a diverse
    scenario corpus) + a `baseline_verdicts.json` store — the whole Fase-G improvement-loop safety
    net. NONE of that has a v3 port: there is no `v3.verify.blast_radius`, no
    `v3.verify.scenario_corpus`, and no baseline-verdicts machinery (that is the META improvement
    loop, out of this slot's scope). Faking a promotion by skipping the blast-radius sweep would be
    exactly the defect this slot exists to refuse, so this REFUSES — names precisely what is missing —
    rather than returning 0 having done nothing."""
    return Verdict(f"promote {ns.factory}", 2,
                   "v3 has no blast-radius sweep, no scenario-corpus gate and no baseline-verdicts "
                   "store — the whole Fase-G safety net `promote` depends on. Porting the META "
                   "improvement loop is out of this slot's scope; refusing rather than promoting "
                   "unguarded")


def product(ns) -> Verdict:
    """`new --factory F --name N <blueprint>` registers a new product instance: commits the blueprint
    as `products/N/product.yml`, materializes it, runs the factory's line e2e on the instance's own
    evidence root, and pins it (reusing `_pin_from_line`, the same law `pin` uses — no second one).
    `list --factory F` shows the default product + every instance with its pin status.

    Both sub-verbs REQUIRE `--factory` at the parser, as in v2. A draft of this slot loosened `list`
    with a silent `dummy` fallback to satisfy a smoke invocation; reverted for the same reason as
    `rtm` — a verb that answers about a factory the caller never named is a green that means
    something else."""
    from ..verify.rederive import materialize_instance, targets

    factory = ns.factory
    fdir = _ROOT / "factories" / factory
    if not (fdir / "factory.spec.yml").is_file():
        return Verdict("product", 1, f"no such factory {factory!r}")

    if ns.prod_cmd == "list":
        found = targets(fdir, factory)
        lines = []
        for t in found:
            label = "default (factory root)" if t.product is None else t.label
            pin_status = "pin ✓" if (t.root / "pinned_verdict.json").is_file() else "no pin"
            lines.append(f"{label} · {pin_status}")
        return Verdict(f"product list {factory}", 0,
                       f"{len(found)} product(s): " + "; ".join(lines))

    # new
    from .builds import BuildContext, apply_builds
    from .line import materialize_stations, resolve_line
    from .runner import RunContext, run_line
    from ..spec.loader import load_spec
    from ..verify.rederive import apply_activation

    product_root = fdir / "products" / ns.name
    if (product_root / "product.yml").is_file():
        return Verdict("product new", 1,
                       f"product {ns.name!r} already exists in {factory} (not overwriting it)")
    blueprint_path = Path(ns.blueprint)
    if not blueprint_path.is_file():
        return Verdict("product new", 1, f"no such blueprint {ns.blueprint}")
    product_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(blueprint_path, product_root / "product.yml")

    target = next((t for t in targets(fdir, factory) if t.product == ns.name), None)
    if target is None:
        return Verdict("product new", 1,
                       f"products/{ns.name}/product.yml was written but is not discovered as a "
                       f"target")
    overrides = materialize_instance(target)
    spec = load_spec(target.root / "factory.spec.yml")
    raw = materialize_stations(spec)
    line = resolve_line(raw, spec.subst)
    if overrides:
        line = apply_activation(line, overrides, target.label)
    if not line:
        return Verdict(f"product new {target.label}", 1,
                       "the factory's line selects zero stations for this product")

    ctx = RunContext(root=target.root, home=_ROOT, proof_dir=target.root / ".proof",
                     pythonpath=str(_ROOT))
    build_ctx = BuildContext(root=target.root, meta_root=_ROOT, subst=spec.subst,
                             chassis=target.chassis)
    ctx.builder = lambda st, _ctx: apply_builds(st, build_ctx)
    outcomes = run_line(line, ctx)
    if not outcomes or not all(o.ran and o.passed for o in outcomes):
        last = outcomes[-1] if outcomes else None
        reason = ("; ".join(last.blockers) if last and last.blockers
                  else f"{last.station} failed its checks" if last else "the line selected zero "
                                                                        "stations")
        return Verdict(f"product new {target.label}", 1,
                       f"the instance does not build green: {reason}",
                       next_action=f"fix products/{ns.name}/product.yml and retry")

    ok, pinned_or_station = _pin_from_line(target, line)
    if not ok:
        return Verdict(f"product new {target.label}", 1,
                       f"{pinned_or_station} has no established green proof to pin")
    (target.root / "pinned_verdict.json").write_text(
        json.dumps(pinned_or_station, indent=2) + "\n", encoding="utf-8")
    return Verdict(f"product new {target.label}", 0,
                   f"instance products/{ns.name}/ built e2e + pinned "
                   f"({len(pinned_or_station)} station(s))",
                   next_action=f"re-derive its pin with `v3 ci --rederive --factory {factory}`")
