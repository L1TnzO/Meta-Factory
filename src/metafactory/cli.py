"""cli — `meta <verb>`. The operator surface and the first verdict-bus materializer.

Verbs:
  check                      self-check the Meta-Factory repo (bus verdict + log on disk)
  new <spec.yml>             register a factory target (factories/<slug>/) from a spec
  station <id> --factory S   run meta-station <id> (build->verify->gate) building factory S
  product-run --factory S    run factory S's own product line e2e (M8's honest e2e)
  rtm --factory S            re-derive the RTM from artifacts (SATISFIED/UNSATISFIED)
  ci --rederive              external re-derivation: rebuild on clean state, demand pinned
  pin --factory S            write the pinned verdict (committed honest constant); --verify also re-derives (B11)
  promote --factory S        Fase G: promote iff the engine passes a diverse scenario corpus AND no downstream verdict drops
  verify --rerun             re-verify the active station (Lock #3, used by the Stop hook)
  doc-sync                   stamp docs + regenerate INDEX (used by the PostToolUse hook)
  doc slice <doc> [§|title]  print ONE section of a doc (or --abstract) instead of the whole file (C16)
  jdk-run [--root D] -- CMD  ensure JDK 21 + run CMD, 1-line VERDICT + log (collapses toolchain+gate, B11)

Every expensive verb returns a BOUNDED verdict (≤10 lines) + a pointer to the disk log.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

from . import docs_manifest
from ._seed import repo_root
from .engine import RunContext, load_sequence, run_station
from .spec import load_spec, validate
from .verify import report


# ── helpers ──────────────────────────────────────────────────────────────────
def _meta_root() -> Path:
    return repo_root()


def _factory_dir(slug: str) -> Path:
    return _meta_root() / "factories" / slug


def _products_dir(slug: str) -> Path:
    return _factory_dir(slug) / "products"


def _product_dir(slug: str, product: str) -> Path:
    return _products_dir(slug) / product


def _list_products(slug: str) -> list[str]:
    """The named product instances of a factory (R1): a dir under `products/` carrying a `product.yml`
    (its domain blueprint, the committed source). The DEFAULT product (factory root) is not listed here."""
    pdir = _products_dir(slug)
    if not pdir.is_dir():
        return []
    return sorted(p.name for p in pdir.iterdir() if (p / "product.yml").is_file())


def _norm_activation(v) -> str:
    """Canonicalize a station activation override to the engine's vocabulary ("off" = inactive, else
    active). YAML 1.1 parses a bare `off`/`no` as the bool False, so normalize bools/strings alike — a
    raw False would stringify to "False" and (being != "off") read as ACTIVE, the opposite of intent."""
    if v is False or str(v).strip().lower() in ("off", "false", "no", "0"):
        return "off"
    if v is True or str(v).strip().lower() in ("on", "always", "true", "yes", "1"):
        return "always"
    return str(v)


def ensure_product_instance(chassis: Path, product_root: Path, meta_root: Path, slug: str) -> None:
    """R1 (ADR-015) — materialize a product instance's DERIVED root from its committed source.

    A product instance commits only two files: `product.yml` (its `domain.product` blueprint — the sole
    point of variation between a factory's products) and `pinned_verdict.json` (its pin). Everything else
    is re-derivable: this writes the EFFECTIVE spec (the factory's base spec with `domain.product` replaced
    by the instance's blueprint) and re-materializes the instance's `stations/` from it (reusing the engine's
    `_materialize_line`, single source — the line STRUCTURE is the factory's; only the blueprint differs).
    Idempotent: safe to call before every run (`ci --rederive`, the gate's clean clone), so a fresh checkout
    that carries only `product.yml` rebuilds the whole instance. The substrate names no tech (ADR-012)."""
    import copy

    import yaml

    from .codegen.renderer import _materialize_line
    from .engine import RunContext

    chassis, product_root = Path(chassis).resolve(), Path(product_root).resolve()
    base = yaml.safe_load((chassis / "factory.spec.yml").read_text(encoding="utf-8")) or {}
    blueprint = yaml.safe_load((product_root / "product.yml").read_text(encoding="utf-8")) or {}
    # Reserved instance-config key (popped so it never reaches the scaffold's domain.product): per-instance
    # station ACTIVATION overrides. A product legitimately may not run a station the demo does — e.g. a live
    # station with no provider key for THIS instance (the `live_run` check itself sanctions activation:off as
    # the honest deferral, vs faking green). General + visible (it lives in the committed product.yml).
    overrides = blueprint.pop("station_activation", {}) if isinstance(blueprint, dict) else {}
    effective = copy.deepcopy(base)
    effective.setdefault("domain", {})["product"] = blueprint
    for st in effective.get("domain", {}).get("station_sequence", []) or []:
        if isinstance(st, dict) and st.get("id") in overrides:
            st["activation"] = _norm_activation(overrides[st["id"]])
    product_root.mkdir(parents=True, exist_ok=True)
    (product_root / "factory.spec.yml").write_text(
        yaml.safe_dump(effective, sort_keys=False, allow_unicode=True), encoding="utf-8")
    eff_spec = load_spec(product_root / "factory.spec.yml")
    ctx = RunContext(root=product_root, meta_root=meta_root, slug=slug, chassis=chassis)
    _materialize_line(ctx, {"action": "materialize_line", "dest": "stations"}, _subst_for(eff_spec, product_root))


def _meta_stations_dir() -> Path:
    return _meta_root() / "src" / "metafactory" / "stations"


def _subst_for(spec, fdir: Path) -> dict:
    s = dict(spec.subst)
    s.update({
        "slug": spec.slug,
        "factory_root": str(fdir.resolve()),
        "meta_root": str(_meta_root()),
        "spec_path": "factory.spec.yml",
        "max_lines": int((spec.substrate.get("verdict_bus", {}) or {}).get("max_lines", 10)),
    })
    return s


def _print_verdict(v) -> None:
    print(report.format_verdict(v))


def _copy_metacheck_log(proof: dict) -> str:
    """Mirror the verifier log into .meta_check/<ts>.log (B2) and return that path."""
    src = proof.get("log_path", "")
    dst_dir = _meta_root() / ".meta_check"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / Path(src).name if src else dst_dir / "metacheck.log"
    if src and Path(src).exists():
        shutil.copy2(src, dst)
    return str(dst)


# ── verbs ────────────────────────────────────────────────────────────────────
def cmd_check(args) -> int:
    """Self-check the meta repo: compile + docs consistency + isolation + suite.
    First materializer of the verdict bus (I-7)."""
    root = _meta_root()
    py = sys.executable
    checks = [
        {"name": "compile", "kind": "command",
         "cmd": [py, "-m", "compileall", "-q", "src/metafactory", "seed"]},
        {"name": "docs", "kind": "docs_check"},
        {"name": "projection", "kind": "command",
         "cmd": [py, "-m", "metafactory.memory.projection", "check"]},
        {"name": "isolation", "kind": "command",
         "cmd": [py, "-m", "pytest", "-q", "tests/test_isolation.py"]},
        {"name": "generality", "kind": "command",       # ADR-014 (MAT-0): ningún mecanismo de sustrato
         "cmd": [py, "-m", "metafactory.verify.checks.generality_parity", str(root)]},  # `general` sin paridad de 2 dominios
        {"name": "quality", "kind": "command",           # ADR-017 (Fase 1): gate SWE determinista sobre el
         "cmd": [py, "-m", "metafactory.verify.checks.quality_gate", str(root)]},  # grafo (tamaño/acoplamiento), dogfood dos-lados
        {"name": "pbt", "kind": "command",               # ADR-017 (Fase 2): property-based gate sobre el grafo,
         "cmd": [py, "-m", "metafactory.verify.checks.pbt_gate", str(root)]},      # dos-lados (sabotage debe morder)
        {"name": "evidence_liveness", "kind": "command",  # ADR-026 (F1, DOC-GRAPH-LIVENESS): las referencias
         "cmd": [py, "-m", "metafactory.verify.checks.evidence_liveness", str(root)]},  # de un doc VIVO resuelven, dos-lados
        {"name": "security", "kind": "command",          # ADR-017 (Fase 3): scan de secretos heredable, dos-lados
         "cmd": [py, "-m", "metafactory.verify.checks.security_scan", str(root)]},
        {"name": "deferred", "kind": "command",          # ADR-017 (Fase 4): declared-deferred con dientes +
         "cmd": [py, "-m", "metafactory.verify.checks.declared_deferred", str(root)]},  # acumulación medida
        {"name": "benchmark", "kind": "command",          # ADR-017 (Fase 4): sweet-spot como TARGET verificable,
         "cmd": [py, "-m", "metafactory.verify.checks.benchmark_gate", str(root)]},  # dos-lados (techo debe fallar)
        {"name": "dial", "kind": "command",                # ADR-017 (Fase 4): el dial draft→harden adoptado con
         "cmd": [py, "-m", "metafactory.verify.checks.dial_gate", str(root)]},  # dientes (all-harden = decorativo → rojo)
        {"name": "column_parity", "kind": "command",      # ADR-018 (Fase 2 §1): la columna heredada de cada
         "cmd": [py, "-m", "metafactory.verify.checks.column_parity", str(root)]},   # fábrica ≡ proyección de M1 (drift = rojo)
        {"name": "least_priv", "kind": "command",          # ADR-018 (§3, LEAST-PRIV-DECOUPLE): la columna de la
         "cmd": [py, "-m", "metafactory.verify.checks.least_priv", str(root)]},  # fábrica = scope mínimo-privilegio ⊊ meta (sobre-priv = rojo)
        {"name": "roles", "kind": "command",               # ADR-020 (Fase D): los agentes se especializan por ROL,
         "cmd": [py, "-m", "metafactory.verify.checks.role_hygiene", str(root)]},  # no por dominio (nombre fuera del vocab cerrado = rojo)
        {"name": "kinds", "kind": "command",                # D-3 (VOCAB-FREEZE, COUNCIL-360): el vocabulario de check-
         "cmd": [py, "-m", "metafactory.verify.checks.kind_hygiene", str(root)]},  # kinds está CONGELADO (kind fuera de registry.KINDS = rojo)
        {"name": "codegen_freeze", "kind": "command",       # ADR-023 §3 (CODEGEN-FREEZE-TOOTH): el codegen de templates
         "cmd": [py, "-m", "metafactory.verify.checks.codegen_freeze", str(root)]},  # está CONGELADO (diff sin waiver = rojo; waiver sin diff = rojo)
        {"name": "plan", "kind": "command",                 # ADR-021 (INC-4, PLAN-EXECUTE-SPLIT): plan-como-DATA
         "cmd": [py, "-m", "metafactory.verify.checks.plan_gate", str(root)]},  # bien formado, dos-lados (slot sin gate/ciclo/diferido-sin-razón = rojo)
        {"name": "state_snapshot", "kind": "command",      # ADR-019 (§3, M1): «Ahora» de STATE es snapshot,
         "cmd": [py, "-m", "metafactory.verify.checks.state_snapshot", str(root)]},  # no log (presupuesto + cierre rancio = rojo)
        {"name": "state_fidelity", "kind": "command",      # ADR-019 (§4, M3): «Ahora» no CONTRADICE el RTM
         "cmd": [py, "-m", "metafactory.verify.checks.state_fidelity", str(root)]},  # re-derivado de `.proof/` (faithfulness, no frescura)
        {"name": "suite", "kind": "command",
         "cmd": [py, "-m", "pytest", "-q", "tests"]},
    ]
    skip = [s.strip() for s in (getattr(args, "skip", "") or "").split(",") if s.strip()]
    known = {c["name"] for c in checks}
    unknown = sorted(set(skip) - known)
    if unknown:
        print(f"VERDICT    check — FAIL   (exit 1)\nSUMMARY    unknown --skip: {', '.join(unknown)}"
              f" (gates: {', '.join(sorted(known))})")
        return 1
    if skip:
        checks = [c for c in checks if c["name"] not in skip]
        # The skip is VISIBLE and adds no greens: a skipped gate never shows up in COUNTS as ok.
        print(f"SKIPPED    {', '.join(skip)} — by invocation (--skip): evidence not re-derivable in "
              f"this environment (clean clone with no `.proof/`); they do NOT count as green")
    ctx = RunContext(root=root, meta_root=root, slug="meta")
    from .verify.checks.registry import resolve_check
    cmds = [{"name": c["name"], "cmd": resolve_check(c, ctx, _Synthetic("metacheck"), {})} for c in checks]
    proof = ctx.verifier.verify_station("metacheck", cmds, root, pythonpath=ctx.pythonpath)
    from .memory import instrument
    instrument.record_fidelity_from_proof(root, proof)  # serie de fidelidad (ADR-019 §5, M5; observador)
    log = _copy_metacheck_log(proof)
    proof["log_path"] = log
    npass = "green repo — ready for station/ci"
    nfacts = _unnarrated_count(root)
    if nfacts:
        npass += f" · {nfacts} unnarrated fact(s): `meta checkpoint`"
    from .memory import cadence
    if cadence.debt(root)[0]:
        npass += " · cadence: uncommitted code (`meta increment status`)"
    v = report.from_proof("check", proof, next_pass=npass,
                          next_fail="open the ARTIFACT or run `triage` over it; do not paste it into context")
    _print_verdict(v)
    return v.exit_code


def cmd_new(args) -> int:
    spec = load_spec(args.spec)
    problems = validate(spec)
    if not spec.slug:
        print("VERDICT    new — FAIL   (exit 1)\nSUMMARY    spec has no slug; cannot register")
        return 1
    fdir = _factory_dir(spec.slug)
    fdir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.spec, fdir / "factory.spec.yml")
    (fdir / ".metafactory.json").write_text(
        json.dumps({"slug": spec.slug, "spec": "factory.spec.yml", "produces": spec.produces}, indent=2) + "\n",
        encoding="utf-8")
    status = "PASS" if not problems else "PROVISIONAL"
    print(f"VERDICT    new {spec.slug} — {status}   (exit 0)")
    print(f"SUMMARY    registered under factories/{spec.slug}/ · M0 validate: {len(problems)} problem(s)")
    if problems:
        for p in problems[:5]:
            print(f"           {p}")
        print("NEXT       fix the spec; `meta station m00` is the authoritative gate")
    else:
        print("NEXT       meta station m00 --factory " + spec.slug)
    return 0


def _run_one(ctx, station, seq, subst, stations_dir, spec_path, *, verb, build=True) -> int:
    run = run_station(ctx, station, seq, subst, stations_dir=stations_dir, spec_path=spec_path, build=build)
    v = report.from_proof(f"{verb} {station.id}", run.proof,
                          next_pass=run.gate.line(),
                          next_fail=run.gate.line() + " — fix it and re-verify")
    _print_verdict(v)
    print(run.gate.line())
    return 0 if (run.passed and run.gate.opened) else 1


def cmd_station(args) -> int:
    slug = args.factory
    fdir = _factory_dir(slug)
    spec = load_spec(fdir / "factory.spec.yml")
    subst = _subst_for(spec, fdir)
    ctx = RunContext(root=fdir, meta_root=_meta_root(), slug=slug)
    seq = load_sequence(_meta_stations_dir())
    station = seq.get(args.id)
    if station is None:
        print(f"VERDICT    station {args.id} — FAIL   (exit 1)\nSUMMARY    meta-station {args.id} does not exist")
        return 1
    return _run_one(ctx, station, seq, subst, _meta_stations_dir(), fdir / "factory.spec.yml", verb="station")


def _run_product_line(fdir: Path, meta_root: Path, slug: str, *, record_active: bool = True,
                      chassis: Path | None = None, dial: str = "harden"):
    """Run factory `slug`'s product line e2e on `fdir` (build a REAL product, compile+run it).
    Returns (rc, last_run). `record_active=False` keeps a hermetic re-derivation (the clean_runner
    gate) from leaking into the meta active-station pointer or the journal. Single source for both
    `product-run` and the two-verifier re-derivation (no divergence, ADR-005 §4).

    `chassis` (R1, ADR-015): when `fdir` is a PRODUCT INSTANCE (`products/<p>/`) its generator lives in
    the factory chassis, not in `fdir`. Passing it (a) re-derives the instance's effective spec + line from
    its committed `product.yml` and (b) runs the line with `RunContext(root=fdir, chassis=chassis)` so the
    `generate` slot finds the shared generator. For the DEFAULT product chassis defaults to fdir (1:1, byte-identical)."""
    fdir = Path(fdir).resolve()
    chassis = Path(chassis).resolve() if chassis else fdir
    if chassis != fdir:
        ensure_product_instance(chassis, fdir, meta_root, slug)
    spec = load_spec(fdir / "factory.spec.yml")
    subst = _subst_for(spec, fdir)
    ctx = RunContext(root=fdir, meta_root=meta_root, slug=slug, chassis=chassis)
    pseq = load_sequence(fdir / "stations")
    # draft→harden DIAL (ADR-017 Fase 4): in draft, defer the harden-tier (rigor) stations — exactly like
    # `activation: off`, so the sequence's transparent predecessor fall-through skips them. Harden (default)
    # is byte-identical to no dial. The substrate names no station; `tier` is DATA on the line.
    if dial == "draft":
        for st in pseq.stations:
            if not st.active_in("draft"):
                st.activation = "off"
    if not pseq.active:
        return 1, None
    last, ok = None, True
    for st in pseq.active:
        run = run_station(ctx, st, pseq, subst, stations_dir=fdir / "stations",
                          spec_path=fdir / "factory.spec.yml", record_active=record_active)
        last = run
        if not (run.passed and run.gate.opened):
            ok = False
            break
    return (0 if ok else 1), last


def _resolve_target(slug: str, product: str | None):
    """(root, chassis) for a factory's DEFAULT product or a named INSTANCE (R1, ADR-015). Default:
    root == factory dir, chassis None (1:1, byte-identical). Instance: root == products/<p>, chassis
    == factory dir (the shared generator). The substrate names no factory/tech — `product` is DATA."""
    if product:
        return _product_dir(slug, product), _factory_dir(slug)
    return _factory_dir(slug), None


def cmd_product_run(args) -> int:
    """Run factory S's own product line e2e — builds a REAL product and compiles+runs it.
    This is what M8 calls; render-green alone cannot pass it (façade-trap closed). `--product <p>`
    runs a named INSTANCE's line (R1) instead of the default product."""
    slug = args.factory
    product = getattr(args, "product", None)
    dial = getattr(args, "mode", None) or "harden"
    root, chassis = _resolve_target(slug, product)
    if product and not (root / "product.yml").is_file():
        print(f"VERDICT    product-run — FAIL   (exit 1)\nSUMMARY    no such product {product!r} in {slug} "
              f"(create it with `meta product new`)")
        return 1
    rc, last = _run_product_line(root, _meta_root(), slug, chassis=chassis, dial=dial)
    if last is None:
        print("VERDICT    product-run — FAIL   (exit 1)\nSUMMARY    the factory has no product line")
        return 1
    label = f"product-run {slug}/{product}" if product else "product-run"
    deferred = [s.id for s in load_sequence(root / "stations").stations if s.tier == "harden"] if dial == "draft" else []
    draft_note = (f" · DIAL=draft (draft, NOT hardened — {len(deferred)} harden station(s) deferred: "
                  f"{','.join(deferred)}; harden with --mode harden before pinning/shipping)" if dial == "draft" else "")
    v = report.from_proof(label, last.proof,
                          next_pass=f"product e2e OK · {last.gate.line()}{draft_note}",
                          next_fail=f"broken product · {last.gate.line()}{draft_note}")
    _print_verdict(v)
    return 0 if rc == 0 else 1


def cmd_product(args) -> int:
    """R1 (ADR-015) — the product-instance lifecycle verb: a factory is a REUSABLE target (1:N).

    `new --factory F --name P <blueprint.yml>` registers a NEW product instance: it commits the
    blueprint as products/P/product.yml (the sole point of variation — a `domain.product` subtree),
    materializes the instance from it, runs the factory's line e2e on the instance's OWN evidence root
    and pins it. `list --factory F` shows the default product + every instance with its pin status.
    The substrate names no factory/tech (ADR-012); instances are DATA, not branches in the codegen."""
    slug = args.factory
    meta_root = _meta_root()
    fdir = _factory_dir(slug)
    if not (fdir / "factory.spec.yml").is_file():
        print(f"VERDICT    product — FAIL   (exit 1)\nSUMMARY    no such factory {slug!r}")
        return 1
    if args.prod_cmd == "list":
        products = _list_products(slug)
        print(f"VERDICT    product list {slug} — {len(products) + 1} product(s)   (exit 0)")
        print(f"SUMMARY    default + {len(products)} instance(s) (each with its own pin)")
        dpin = "pin ✓" if (fdir / "pinned_verdict.json").is_file() else "no pin"
        print(f"           default (factory root) · {dpin}")
        for p in products:
            ppin = "pin ✓" if (_product_dir(slug, p) / "pinned_verdict.json").is_file() else "no pin"
            print(f"           {p} (products/{p}/) · {ppin}")
        return 0
    # new
    name = args.name
    product_root = _product_dir(slug, name)
    if (product_root / "product.yml").is_file():
        print(f"VERDICT    product new — FAIL   (exit 1)\nSUMMARY    product {name!r} already exists in {slug} "
              f"(not overwriting it)")
        return 1
    blueprint_path = Path(args.blueprint)
    if not blueprint_path.is_file():
        print(f"VERDICT    product new — FAIL   (exit 1)\nSUMMARY    no such blueprint {args.blueprint}")
        return 1
    product_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(blueprint_path, product_root / "product.yml")
    rc, last = _run_product_line(product_root, meta_root, slug, chassis=fdir)
    if last is None or rc != 0:
        line = last.gate.line() if last is not None else "the factory has no product line"
        print(f"VERDICT    product new {slug}/{name} — FAIL   (exit 1)\nSUMMARY    the product does not build green · {line}")
        print("NEXT       fix the blueprint products/{0}/product.yml and retry".format(name))
        return 1
    pin_ok, info = _pin_from_proofs(product_root, meta_root, slug, chassis=fdir)
    if not pin_ok:
        print(f"VERDICT    product new {slug}/{name} — FAIL   (exit 1)\nSUMMARY    {info} has no green proof to pin")
        return 1
    print(f"VERDICT    product new {slug}/{name} — PASS   (exit 0)")
    print(f"SUMMARY    instance products/{name}/ built e2e + pinned ({len(info)} stations)")
    print(f"NEXT       re-derive its pin with `meta ci --rederive --factory {slug} --product {name}`")
    return 0


def cmd_rtm(args) -> int:
    """Re-derive the build EVIDENCE TREE from artifacts only (I-10, C4): req → capability → station →
    proof → artifact. A requirement is SATISFIED iff every edge holds — its capability is real, every
    station's gate is OPEN (passing, recompute-clean proof), and every artifact its capability declares
    exists on disk. Single source `verify.rtm` (shared with the `rtm_tree` gate)."""
    from .verify import rtm
    slug = args.factory
    product = getattr(args, "product", None)
    fdir, chassis = _resolve_target(slug, product)
    if product:
        ensure_product_instance(chassis, fdir, _meta_root(), slug)
    spec = load_spec(fdir / "factory.spec.yml")
    ctx = RunContext(root=fdir, meta_root=_meta_root(), slug=slug, chassis=chassis)
    nodes = rtm.build_tree(spec, ctx.verifier, fdir)
    print(rtm.render(f"{slug}/{product}" if product else slug, nodes))
    return 0 if rtm.is_complete(nodes) else 1


def _compare_to_pinned(verifier, fdir: Path, pinned: dict) -> list[str]:
    """The two-verifier COMPARISON law (single source, ADR-005 §4): every pinned station's
    re-derived proof_sha must equal the pinned constant. A deviation in EITHER direction
    (re-derived proof distinto O pin distinto) is a mismatch -> red. Reused by `meta ci` and
    by the clean_runner gate, so the gate cannot drift from the command it enforces."""
    mismatches = []
    for sid, want in pinned.items():
        proof = verifier.load_proof(fdir, sid)
        got = proof.get("proof_sha") if proof else None
        if got != want:
            mismatches.append(f"{sid}: pinned {str(want)[:12]} != re-derived {str(got)[:12]}")
    return mismatches


def rederive_pinned(fdir: Path, meta_root: Path, slug: str, *, record_active: bool = True,
                    chassis: Path | None = None):
    """External re-derivation law (two-verifier doctrine, PF-10): wipe re-derivable state on
    `fdir`, rebuild the product line from source on a clean tree, recompute each proof_sha and
    demand the pinned verdict. ONE law shared by `meta ci`, the external CI and the clean_runner
    gate (M6). The gate runs it against a throwaway clone so custody is never the root of trust —
    replicability is. `chassis` (R1): re-derive a PRODUCT INSTANCE whose generator lives in the
    factory chassis (`fdir` = `products/<p>/`). Returns (ok, mismatches, rc, has_pinned)."""
    fdir = Path(fdir)
    pinned_path = fdir / "pinned_verdict.json"
    if not pinned_path.exists():
        return False, [], 1, False
    pinned = json.loads(pinned_path.read_text(encoding="utf-8"))
    shutil.rmtree(fdir / ".proof", ignore_errors=True)
    shutil.rmtree(fdir / "build", ignore_errors=True)
    rc, _ = _run_product_line(fdir, meta_root, slug, record_active=record_active, chassis=chassis)
    v = RunContext(root=fdir, meta_root=meta_root, slug=slug, chassis=chassis).verifier
    mismatches = _compare_to_pinned(v, fdir, pinned)
    return (rc == 0 and not mismatches), mismatches, rc, True


def _ci_one(slug: str, product: str | None) -> tuple[bool, str]:
    """Re-derive ONE product (default or instance) and return (ok, one-line summary). Single
    re-derivation law (`rederive_pinned`); each product has its OWN root, so the products are
    isolated — re-deriving B never reads A's `.proof/` (R1 isolation, ADR-015)."""
    root, chassis = _resolve_target(slug, product)
    label = f"{slug}/{product}" if product else slug
    ok, mismatches, rc, has_pinned = rederive_pinned(root, _meta_root(), slug, chassis=chassis)
    if not has_pinned:
        return False, f"{label}: NOT PINNED (no pinned_verdict.json; run `meta pin`)"
    pinned = json.loads((root / "pinned_verdict.json").read_text(encoding="utf-8"))
    note = f"{label}: {len(pinned) - len(mismatches)}/{len(pinned)} proof_sha == pinned"
    if not ok:
        note += " · " + ("; ".join(mismatches[:3]) if mismatches else f"product-run rc={rc} (broken product)")
    return ok, note


def cmd_ci(args) -> int:
    """External re-derivation (two-verifier doctrine): wipe re-derivable state, rebuild the
    product line from source on a clean tree, and demand the pinned proof_sha. Any deviation
    (either direction) is red — a spontaneous PASS without proof is a façade, not a win.

    `--product <p>` re-derives a named INSTANCE (R1); `--all-products` re-derives the DEFAULT
    plus EVERY instance, each demanding its own pin — one product's failure never masks another's,
    and their separate roots make the re-derivations isolated (ADR-015)."""
    slug = args.factory
    if getattr(args, "all_products", False):
        targets: list[str | None] = [None, *_list_products(slug)]
        results = [_ci_one(slug, p) for p in targets]
        ok = all(r[0] for r in results)
        print(f"VERDICT    ci --rederive {slug} --all-products — {'PASS' if ok else 'FAIL'}   (exit {0 if ok else 1})")
        print(f"SUMMARY    {sum(r[0] for r in results)}/{len(results)} products re-derived == their pin")
        for _, note in results:
            print(f"           {note}")
        return 0 if ok else 1
    product = getattr(args, "product", None)
    ok, note = _ci_one(slug, product)
    label = f"{slug}/{product}" if product else slug
    print(f"VERDICT    ci --rederive {label} — {'PASS' if ok else 'FAIL'}   (exit {0 if ok else 1})")
    print(f"SUMMARY    re-derived on a clean tree · {note}")
    return 0 if ok else 1


def _pin_from_proofs(fdir: Path, meta_root: Path, slug: str, *, chassis: Path | None = None):
    """Single source for writing the pinned verdict from the CURRENT (honest) proofs of the
    product line. Returns (ok, pinned_or_badstation). Reused by `meta pin` and `meta promote`.
    `chassis` (R1): pin a PRODUCT INSTANCE (`fdir` = `products/<p>/`) whose pin lives beside it."""
    ctx = RunContext(root=fdir, meta_root=meta_root, slug=slug, chassis=chassis)
    pseq = load_sequence(fdir / "stations")
    pinned = {}
    for st in pseq.active:
        proof = ctx.verifier.load_proof(fdir, st.id)
        if proof is None or not proof.get("passed"):
            return False, st.id
        pinned[st.id] = proof["proof_sha"]
    (fdir / "pinned_verdict.json").write_text(json.dumps(pinned, indent=2) + "\n", encoding="utf-8")
    return True, pinned


def cmd_pin(args) -> int:
    """Write the pinned verdict from the current (honest) proofs of the product line.
    `--product <p>` pins a named INSTANCE (R1), writing products/<p>/pinned_verdict.json.

    `--verify` (B11 / CONTEXT-LEAN-TEETH fase 5): collapse the measured 2-command sequence
    `meta pin` + `meta ci --rederive` (pin, then separately confirm the pin re-derives on a
    clean tree) into ONE verb/turn. Pure composition over `_pin_from_proofs`/`_ci_one` (both
    already exercised elsewhere) — no new verification logic, just one fewer round trip."""
    slug = args.factory
    product = getattr(args, "product", None)
    root, chassis = _resolve_target(slug, product)
    ok, info = _pin_from_proofs(root, _meta_root(), slug, chassis=chassis)
    if not ok:
        print(f"VERDICT    pin — FAIL   (exit 1)\nSUMMARY    {info} has no green proof; run product-run first")
        return 1
    label = f"pin {slug}/{product}" if product else f"pin {slug}"
    if not getattr(args, "verify", False):
        print(f"VERDICT    {label} — PASS   (exit 0)\nSUMMARY    pinned {len(info)} proof_sha in pinned_verdict.json")
        return 0
    ci_ok, ci_note = _ci_one(slug, product)
    status = "PASS" if ci_ok else "FAIL"
    print(f"VERDICT    {label} --verify — {status}   (exit {0 if ci_ok else 1})")
    print(f"SUMMARY    pinned {len(info)} proof_sha · clean-tree re-derivation: {ci_note}")
    return 0 if ci_ok else 1


def cmd_promote(args) -> int:
    """Fase G — the improvement loop's PROMOTE phase, gated by blast-radius (`SELF-IMPROVEMENT.md §4`).

    "Regenerate-to-improve replaces the pin only if it re-passes the gate WITHOUT lowering any
    downstream verdict." Refuses unless THREE things hold: (0, G2) the engine still BEHAVES across the
    diverse scenario corpus (a regressed engine makes every promotion unsafe — `scenario_corpus`,
    closes G-8 at root), (1) the candidate ACTUALLY improved its baseline (a hold is a façade), and
    (2) NO factory in the baseline lowered its verdict (the blast radius, re-derived on clean clones —
    custody is never the root of trust). On green it re-pins the candidate and bumps the baseline; it
    does NOT commit — the promotion ascends by a REVIEWED diff (§4), never spontaneously."""
    from .verify import verdict as V
    from .verify.checks import blast_radius as BR
    from .verify.checks import scenario_corpus as SC

    slug = args.factory
    meta_root = _meta_root()
    baseline_path = meta_root / args.baseline
    baseline = V.load_baseline(baseline_path)
    if slug not in baseline:
        print(f"VERDICT    promote {slug} — FAIL   (exit 1)\n"
              f"SUMMARY    {slug} is not in the baseline ({args.baseline}); "
              f"add it with `meta pin`+baseline before promoting an improvement")
        return 1

    # 0. G2 gate — the engine must still behave across the DIVERSE scenario corpus before ANY promotion
    #    (G-8 root: diverse spec shapes exercise the engine; `SELF-IMPROVEMENT.md §4`). This protects the
    #    engine's BEHAVIOR (vs blast_radius, which protects the downstream verdicts); a regressed engine
    #    makes every promotion unsafe, so it precedes the downstream sweep.
    corpus_path = meta_root / "scenarios" / "corpus.yml"
    if not corpus_path.exists():
        print(f"VERDICT    promote {slug} — FAIL   (exit 2)\n"
              f"SUMMARY    no scenario corpus ({corpus_path}); G2 demands exercising the engine "
              f"in N diverse ways before promoting")
        return 2
    corpus_dir, scenarios = SC.load_corpus(corpus_path)
    c_action, c_detail = SC.decide(corpus_dir, scenarios)
    if c_action != "ok":
        print(f"VERDICT    promote {slug} — BLOCKED   (exit 2)\n"
              f"SUMMARY    the engine does not pass the diverse scenario corpus "
              f"(pin and baseline INTACT):")
        for r in (c_detail if isinstance(c_detail, list) else [c_detail])[:6]:
            print(f"           {r}")
        return 2

    # 1. Re-derive the whole downstream sweep ONCE (the candidate is part of it) on clean clones,
    #    then take the PURE decision (the law shared with the tests).
    candidates = BR.sweep(meta_root, baseline)
    cand_x = candidates[slug]
    action, detail = BR.decide(candidates, baseline, slug, allow_hold=args.allow_hold)
    if action == "facade":   # §4: a hold/regression of the target itself is nothing to promote.
        print(f"VERDICT    promote {slug} — FAIL   (exit 2)\n"
              f"SUMMARY    nothing to promote: {detail} "
              f"[{slug} candidate {cand_x.get('rtm_satisfied')}/{cand_x.get('rtm_total')} "
              f"vs baseline {baseline[slug].get('rtm_satisfied')}/{baseline[slug].get('rtm_total')}]")
        return 2
    if action == "blast":    # a downstream factory would lower its verdict — pin/baseline INTACT.
        print(f"VERDICT    promote {slug} — BLOCKED   (exit 2)\n"
              f"SUMMARY    blast-radius: the promotion would lower a downstream factory's verdict "
              f"(pin and baseline INTACT):")
        for r in detail[:6]:
            print(f"           {r}")
        return 2
    if action == "decorative":
        print(f"VERDICT    promote {slug} — FAIL   (exit 2)\n"
              f"SUMMARY    decorative gate: the domination law has no teeth (never promote blindly)")
        return 2

    # 2. PROMOTE: refresh the candidate's REAL proofs, re-pin, and bump the baseline. No commit —
    #    the diff (improvement + pin + baseline) ascends reviewed (§4).
    improved = detail
    fdir = _factory_dir(slug)
    rc, _ = _run_product_line(fdir, meta_root, slug)
    if rc != 0:
        print(f"VERDICT    promote {slug} — FAIL   (exit 1)\n"
              f"SUMMARY    {slug}'s real line does not rebuild while re-pinning (should not happen after the sweep)")
        return 1
    pin_ok, info = _pin_from_proofs(fdir, meta_root, slug)
    if not pin_ok:
        print(f"VERDICT    promote {slug} — FAIL   (exit 1)\nSUMMARY    {info} has no green proof to re-pin")
        return 1
    baseline[slug] = cand_x
    V.save_baseline(baseline_path, baseline)
    verb = "improved" if improved else "held (--allow-hold)"
    print(f"VERDICT    promote {slug} — PASS   (exit 0)\n"
          f"SUMMARY    {slug} {verb} to {cand_x.get('rtm_satisfied')}/{cand_x.get('rtm_total')}; "
          f"re-pinned ({len(info)} stations) + baseline bumped; corpus green "
          f"({len(scenarios)} diverse scenarios) + blast-radius green "
          f"({len(baseline)} factories, none dropped). Promotion NOT committed (ascend via a reviewed diff, §4).")
    return 0


def cmd_verify(args) -> int:
    """Re-verify the active station (Lock #3). Used by the Stop hook: exit≠0 => block turn."""
    active_path = _meta_root() / ".proof" / "active.json"
    if not active_path.exists():
        print("VERDICT    verify --rerun — PASS   (exit 0)\nSUMMARY    no active station to re-verify")
        return 0
    active = json.loads(active_path.read_text(encoding="utf-8"))
    root = Path(active["root"])
    stations_dir = Path(active["stations_dir"])
    spec_path = Path(active["spec"]) if active.get("spec") else None
    spec = load_spec(spec_path) if spec_path and spec_path.exists() else None
    subst = _subst_for(spec, root) if spec else {}
    ctx = RunContext(root=root, meta_root=_meta_root(), slug=active.get("slug", "meta"))
    seq = load_sequence(stations_dir)
    station = seq.get(active["station"])
    if station is None:
        print("VERDICT    verify --rerun — PASS   (exit 0)\nSUMMARY    unknown active station; nothing to block")
        return 0
    return _run_one(ctx, station, seq, subst, stations_dir, spec_path, verb="verify", build=False)


def cmd_doc_sync(args) -> int:
    changed = docs_manifest.sync(_meta_root())
    print(f"doc-sync: {len(changed)} doc(s) re-stamped; INDEX.md regenerated")
    return 0


# ── incremento (disciplina de commit, ADR-010) ───────────────────────────────
_INCREMENT_SCAFFOLD = """# Incremento {slug}

> **Doc de gobierno.** Status: **OPEN** (creado {ts}). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
<qué deja TERMINADO este incremento — una frase>

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | <…> | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. <…>
"""


def _now_min() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def _work_dir(root: Path, factory: str | None = None, product: str | None = None) -> Path:
    """The `docs/work/` of the ADDRESSED level (ADR-016). `--product` requires `--factory`."""
    if product:
        return root / "factories" / factory / "products" / product / "docs" / "work"
    if factory:
        return root / "factories" / factory / "docs" / "work"
    return root / "docs" / "work"


def _level_label(factory: str | None, product: str | None) -> str:
    if product:
        return f"factories/{factory}/products/{product}"
    return f"factories/{factory}" if factory else "meta"


def _active_station_green(root: Path) -> bool:
    """True si no hay estación activa o si recompone verde (reusa el seed verifier, como commit_guard)."""
    active = root / ".proof" / "active.json"
    if not active.exists():
        return True
    try:
        from ._seed import load_seed_verifier
        a = json.loads(active.read_text(encoding="utf-8"))
        v = load_seed_verifier()
        proof = v.load_proof(Path(a["root"]), a["station"])
    except Exception:
        return True
    return proof is None or v.gate_recompute_ok(proof)[0]


def cmd_increment(args) -> int:
    """Lifecycle de incrementos (ADR-010 + ADR-016, level-aware): la unidad dentro de la cual vive todo
    cambio de código. `open` abre uno (rehúsa si ya hay en ESE nivel), `close` lo cierra gateado, `status`
    muestra abierto + deuda. `--factory`/`--product` direccionan el nivel (default: meta `docs/work/`)."""
    root = _meta_root()
    from .memory import cadence, projection
    factory = getattr(args, "factory", None)
    product = getattr(args, "product", None)
    if product and not factory:
        print("VERDICT    increment — FAIL   (exit 1)\nSUMMARY    --product requires --factory")
        return 1
    workdir = _work_dir(root, factory, product)
    label = _level_label(factory, product)
    wd_rel = workdir.relative_to(root)
    if args.inc_cmd == "status":
        inc = cadence.open_increment_in(workdir) or "none"
        has_debt, reason = cadence.debt(root)
        print(f"VERDICT    increment status [{label}] — {'DEBT' if has_debt else 'OK'}   (exit 0)")
        print(f"SUMMARY    open increment ({wd_rel}/): {inc}")
        print(f"CADENCE    {reason}")
        return 0
    if args.inc_cmd == "open":
        cur = cadence.open_increment_in(workdir)
        if cur is not None:
            print("VERDICT    increment open — FAIL   (exit 1)")
            print(f"SUMMARY    an increment is already open in [{label}]: {cur} (close it first)")
            return 1
        name = f"{args.slug.upper()}-INCREMENT.md"
        path = workdir / name
        if path.exists():
            print("VERDICT    increment open — FAIL   (exit 1)")
            print(f"SUMMARY    {wd_rel}/{name} already exists; not overwriting it")
            return 1
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_INCREMENT_SCAFFOLD.format(slug=args.slug.upper(), ts=_now_min()), encoding="utf-8")
        docs_manifest.sync(root)        # sella el doc nuevo (si es meta) + regenera INDEX
        projection.refresh(root)        # la proyección de STATE refleja el incremento meta abierto
        docs_manifest.sync(root)        # re-sella STATE
        print(f"VERDICT    increment open {args.slug} [{label}] — PASS   (exit 0)")
        print(f"SUMMARY    opened {wd_rel}/{name} (Status OPEN); edit Objetivo/Fases")
        print("NEXT       you can now touch this level's code; close it with `meta increment close` (gated)")
        return 0
    # close
    cur = cadence.open_increment_in(workdir)
    if cur is None:
        print(f"VERDICT    increment close — FAIL   (exit 1)\nSUMMARY    no open increment in [{label}]")
        return 1
    has_debt, reason = cadence.debt(root)
    if has_debt:
        print("VERDICT    increment close — FAIL   (exit 1)")
        print(f"SUMMARY    cannot close with debt: {reason}")
        print("NEXT       commit the proven work (message with I-10 trailers) and retry")
        return 1
    if not _active_station_green(root):
        print("VERDICT    increment close — FAIL   (exit 1)")
        print("SUMMARY    the active station does not recompute green; broken work is not closed")
        return 1
    path = workdir / cur
    text = path.read_text(encoding="utf-8")
    path.write_text(re.sub(r"(?:Estado|Status):\s*\*\*(?:ABIERTO|OPEN)\*\*",
                           f"Status: **CLOSED** ({_now_min()})", text, count=1),
                    encoding="utf-8")
    docs_manifest.sync(root)
    projection.refresh(root)
    docs_manifest.sync(root)
    print(f"VERDICT    increment close {cur} — PASS   (exit 0)")
    print(f"SUMMARY    {cur} → CLOSED; STATE projection refreshed")
    print("NEXT       narrate the episode in LOG (`meta checkpoint` offers you the unnarrated facts)")
    return 0


# ── memoria (Tier 0/1/2) ─────────────────────────────────────────────────────
def _parse_ts(s: str):
    from datetime import datetime
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%MZ"):
        try:
            return datetime.strptime(s, fmt)
        except (ValueError, TypeError):
            pass
    return __import__("datetime").datetime.min


def _last_log_ts(root: Path) -> str:
    log = root / "docs" / "LOG.md"
    if not log.exists():
        return "0000-01-01T00:00Z"
    m = re.search(r"^##\s+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z)", log.read_text(encoding="utf-8"), re.MULTILINE)
    return m.group(1) if m else "0000-01-01T00:00Z"


def _git_commits_since(root: Path, ts: str) -> list[str]:
    import subprocess
    try:
        out = subprocess.run(["git", "log", f"--since={ts}", "--format=%h %s"],
                             cwd=root, capture_output=True, text=True)
        return [ln for ln in out.stdout.splitlines() if ln.strip()]
    except OSError:
        return []


def cmd_checkpoint(args) -> int:
    """El disparador NO-discrecional (fix de G-M1): refresca la proyección determinista de STATE
    (hechos) y le ENTREGA al modelo los hechos sin narrar para que escriba el SIGNIFICADO. La parte
    mecánica es un comando; el juicio se OFRECE (esqueleto), no se fuerza (ADR-023)."""
    root = _meta_root()
    from .memory import journal, projection
    changed = projection.refresh(root)
    docs_manifest.sync(root)  # re-sella STATE + regenera INDEX
    last = _last_log_ts(root)
    runs = [e for e in journal.read(root, kinds={"station_run"}) if _parse_ts(e["ts"]) > _parse_ts(last)]
    delegs = [e for e in journal.read(root, kinds={"delegation"}) if _parse_ts(e["ts"]) > _parse_ts(last)]
    commits = _git_commits_since(root, last)
    print(f"VERDICT    checkpoint — {'projection refreshed' if changed else 'projection up to date'}   (exit 0)")
    print(f"SUMMARY    STATE projected from facts · since the last LOG ({last}): "
          f"{len(runs)} station_run · {len(delegs)} delegation · {len(commits)} commit")
    if runs or commits or delegs:
        print("NEXT       judgment is NOT forced, it's OFFERED — add the MEANING to LOG. Unnarrated facts:")
        print(f"           ## {journal.now()[:16]}Z — <title: what changed and why>")
        for c in commits[:6]:
            print(f"           - commit: {c}")
        seen = set()
        for r in runs:
            k = (r.get("slug"), r.get("station"), r.get("passed"))
            if k in seen:
                continue
            seen.add(k)
            print(f"           - station {r.get('station')} ({r.get('slug')}) passed={r.get('passed')} "
                  f"gate={'OPEN' if r.get('gate_open') else 'SHUT'}")
        for d in delegs:
            print(f"           - delegation: {d.get('subagent_type')}/{d.get('model')} — {d.get('description', '')}")
    else:
        print("NEXT       nothing new to narrate since the last LOG episode")
    return 0


def cmd_journal(args) -> int:
    root = _meta_root()
    from .memory import journal
    evs = journal.read(root, limit=args.tail)
    print(f"VERDICT    journal — {len(evs)} event(s) (tail {args.tail})   (exit 0)")
    for e in evs:
        extra = {k: v for k, v in e.items() if k not in ("ts", "kind")}
        print(f"  {e['ts']} {e['kind']}  {extra}")
    return 0


def cmd_metrics(args) -> int:
    root = _meta_root()
    from .memory import instrument, metrics
    print(metrics.render(root, transcript=getattr(args, "transcript", None)))
    # SPLIT de tokens por tier (DELEG-MEASURE): el KPI de costo de la activación de delegación — a dónde
    # van los tokens. Máquina-global (stats-cache), best-effort: ausente → línea honesta.
    print(metrics.render_model_split(metrics.model_split()))
    # Serie del path de INYECCIÓN (ADR-019 §5, M5): footprint·thrashing·fidelidad, acotado.
    for ln in instrument.summarize(root):
        print(ln)
    # Solapamiento de la TERCERA memoria (ADR-019 §5/§Consec., M6): note-store de auto-memoria vs
    # docs/. Observador on-demand (NO gate: la auto-memoria vive fuera del árbol git). --mem-dir
    # sobreescribe la ubicación; ausente → una línea honesta (portable en clon limpio).
    if getattr(args, "overlap", False):
        from .memory import overlap
        for ln in overlap.summarize(root, explicit=getattr(args, "mem_dir", None)):
            print(ln)
    return 0


def cmd_recall(args) -> int:
    """Tombstone (ADR-019 §2, M2). `meta recall` se RETIRÓ: se midió 1×/0-hit en toda la vida del
    proyecto — camino muerto, redundante con Grep/Read (retrieval SOTA-competitivo, Letta). No puntúa;
    redirige. La serie histórica `recall` del journal se conserva (T0, la medición vive)."""
    query = " ".join(getattr(args, "query", []) or []).strip()
    topic = f" «{query}»" if query else ""
    print(f"VERDICT    recall — RETIRED (ADR-019 §2)   (exit 0)")
    print(f"SUMMARY    `meta recall` measured 1×/0-hit and was retired: Grep/Read is the retrieval surface.")
    print(f"NEXT       to find{topic}: `grep -rn …` over docs/ · re-verify state with `meta check`")
    return 0


def cmd_rehydrate(args) -> int:
    from .memory import rehydrate
    print(rehydrate.build_payload(_meta_root()))
    return 0


def cmd_graph(args) -> int:
    """Project-spine (ADR-017): build the content-addressed graph, query it 2-hop (no LLM), repo-map."""
    from .graph.cli import run_graph
    from .memory import journal
    root = _meta_root()
    # Observer for the 30-days-at-0 rule (COUNCIL-360 §2.6 / VOCAB-FREEZE): every NAVIGATION use of the
    # graph surface leaves a fact. 30 days with zero `graph_query` facts ⇒ archive the navigation surface
    # (the internals stay: they feed quality/pbt/billing). Best-effort like every journal write.
    journal.append(root, "graph_query", verb=str(getattr(args, "graph_cmd", "") or ""))
    return run_graph(args, root)


def cmd_doc_slice(args) -> int:
    """`meta doc slice <doc> [selector] [--abstract]` (C16 / CONTEXT-LEAN-TEETH): print ONE section of a
    long `.md` (by number `§2.3` or by title substring), or `--abstract` for a 2-line summary + § map —
    instead of loading the whole doc into context. Thin CLI glue over `metafactory.doc_slice` (the gated
    module); composition only, no new logic here."""
    from . import doc_slice
    root = _meta_root()
    path = Path(args.doc)
    if not path.is_absolute():
        path = root / path
    if not path.is_file():
        print(f"error: no such doc: {args.doc}", file=sys.stderr)
        return 1
    text = path.read_text(encoding="utf-8")
    if args.abstract:
        print(doc_slice.abstract(text))
        return 0
    if not args.selector:
        print("error: missing <selector> (§N.N or a title substring) — or pass --abstract", file=sys.stderr)
        return 1
    out = doc_slice.slice(text, args.selector)
    if out is None:
        print(f"error: section not found: {args.selector!r} in {args.doc}", file=sys.stderr)
        return 1
    print(out)
    return 0


def cmd_doc_orphans(args) -> int:
    """Non-gating observer (ADR-026 F1): prints Doc nodes unreachable from live roots, oldest-first, as
    archive CANDIDATES for the human-owned F3 DRIFT-AUDIT — never a red exit."""
    root = _meta_root()
    from .graph.model import Graph
    from .graph.doc_graph import ingest_docs, ingest_doc_edges, orphan_docs
    graph = Graph()
    ingest_docs(graph, root)
    ingest_doc_edges(graph, root)
    orphans = orphan_docs(graph, root)
    print(f"VERDICT    doc orphans — {len(orphans)} candidate(s)   (exit 0)")
    for o in orphans:
        print(f"  {o['relpath']}  (last_edit={o['last_edit'] or '?'})")
    print("SUMMARY    not reachable from live roots (STATE/CLAUDE.md/open increments) via CITES —"
          " archive candidates (F4), not red")
    return 0


def cmd_jdk_run(args) -> int:
    """`meta jdk-run [--root DIR] [--label L] -- <cmd...>` (B11 / CONTEXT-LEAN-TEETH fase 5): collapse the
    measured 2-step sequence `eval "$(bash tools/toolchain.sh ensure)" && <verbose gradle/npm cmd>`
    (HARNESS-FAST-GATE fase-5 bonus evidence — resolve the JDK-21 toolchain, THEN run a verbose build/test,
    often across separate turns) into ONE verb: resolve JAVA_HOME/PATH and run `cmd` with a single
    VERDICT line + full log artifact (reusing the C18 discipline). Thin CLI glue over
    `metafactory.toolchain_run` (the gated module); composition only, no new logic here."""
    from . import toolchain_run
    cmd = list(args.cmd)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        print("error: missing the command to run (e.g. `meta jdk-run -- ./gradlew test`)", file=sys.stderr)
        return 1
    root = Path(args.root) if args.root else Path.cwd()
    return toolchain_run.run(cmd, root, label=args.label)


def cmd_billing(args) -> int:
    """Show the delegation split (Opus·Sonnet·Haiku) of a billing-ledger (ADR-017, Fase 5)."""
    from .graph.cli import run_billing
    return run_billing(args, _meta_root())


def cmd_outcome(args) -> int:
    """Per-increment OUTCOME (ADR-017 §4, Fase 4): re-derive RTM coverage + deferral debt per factory and
    point at the billing-ledger, so "done" and "worth it" are decidable, not narrated. `--baseline` diffs
    RTM (ΔRTM); `--save` writes a snapshot to diff a future close against; `--billing` attaches the cost."""
    from .verify import outcome
    root = _meta_root()
    snap = outcome.snapshot(root)
    baseline = outcome.load(Path(args.baseline)) if getattr(args, "baseline", None) else None
    ledger_path = Path(args.billing) if getattr(args, "billing", None) else None
    digest = None
    if ledger_path and ledger_path.exists():
        from .graph.billing import BillingLedger, render_split
        digest = render_split(BillingLedger.load(ledger_path)).splitlines()[1].strip()  # the TOTAL line
    # E30 (ADR-021, PRICING-LEDGER): passing `root` appends the per-increment cost block; `--transcript`
    # measures cache expirations + tools/turn (honest "sin medir" for whatever axis has no data).
    transcript = Path(args.transcript) if getattr(args, "transcript", None) else None
    print(outcome.render(snap, baseline=baseline, ledger_path=ledger_path, ledger_digest=digest,
                         root=root, transcript=transcript))
    if getattr(args, "save", None):
        outcome.save(snap, Path(args.save))
        print(f"\n(snapshot saved to {args.save} — baseline for a future `meta outcome --baseline`)")
    return 0


def _unnarrated_count(root: Path) -> int:
    """Hechos (station_run/delegation/commit) posteriores al último episodio de LOG. Surface,
    no se fuerza: el modelo decide narrar (ADR-023). Lo determinista es DETECTAR, no coaccionar."""
    from .memory import journal
    last = _last_log_ts(root)
    runs = [e for e in journal.read(root, kinds={"station_run", "delegation"}) if _parse_ts(e["ts"]) > _parse_ts(last)]
    return len(runs) + len(_git_commits_since(root, last))


# ── tiny utilities ───────────────────────────────────────────────────────────
class _Synthetic:
    def __init__(self, id):
        self.id = id


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="meta", description="Meta-Factory — the factory that manufactures factories")
    sub = p.add_subparsers(dest="cmd", required=True)
    p_check = sub.add_parser("check")
    p_check.add_argument("--skip", default="", help=(
        "gates to skip (comma-separated) when their evidence is NOT re-derivable in this environment "
        "(e.g. a clean clone with no local `.proof/`: projection,generality). The skip is PRINTED as "
        "SKIPPED — it never counts as green (EXTERNAL-CI-GREEN, COUNCIL-360 H-1)."))
    p_check.set_defaults(func=cmd_check)
    sp = sub.add_parser("new"); sp.add_argument("spec"); sp.set_defaults(func=cmd_new)
    sp = sub.add_parser("station"); sp.add_argument("id"); sp.add_argument("--factory", required=True); sp.set_defaults(func=cmd_station)
    sp = sub.add_parser("product-run"); sp.add_argument("--factory", required=True); sp.add_argument("--product", default=None)
    sp.add_argument("--mode", choices=["draft", "harden"], default="harden")  # draft→harden DIAL (ADR-017 Fase 4)
    sp.set_defaults(func=cmd_product_run)
    pp = sub.add_parser("product"); pp.set_defaults(func=cmd_product)
    psub = pp.add_subparsers(dest="prod_cmd", required=True)
    pn = psub.add_parser("new"); pn.add_argument("--factory", required=True); pn.add_argument("--name", required=True); pn.add_argument("blueprint")
    pl = psub.add_parser("list"); pl.add_argument("--factory", required=True)
    sp = sub.add_parser("rtm"); sp.add_argument("--factory", required=True); sp.add_argument("--product", default=None); sp.set_defaults(func=cmd_rtm)
    sp = sub.add_parser("ci"); sp.add_argument("--rederive", action="store_true"); sp.add_argument("--factory", default="dummy")
    sp.add_argument("--product", default=None); sp.add_argument("--all-products", action="store_true"); sp.set_defaults(func=cmd_ci)
    sp = sub.add_parser("pin"); sp.add_argument("--factory", required=True); sp.add_argument("--product", default=None)
    sp.add_argument("--verify", action="store_true", help="after pinning, re-derive on a clean tree and confirm == pin (B11: collapses `pin`+`ci --rederive` into 1 verb)")
    sp.set_defaults(func=cmd_pin)
    sp = sub.add_parser("promote"); sp.add_argument("--factory", required=True)
    sp.add_argument("--baseline", default="baseline_verdicts.json"); sp.add_argument("--allow-hold", action="store_true")
    sp.set_defaults(func=cmd_promote)
    sp = sub.add_parser("verify"); sp.add_argument("--rerun", action="store_true"); sp.set_defaults(func=cmd_verify)
    sub.add_parser("doc-sync").set_defaults(func=cmd_doc_sync)
    ip = sub.add_parser("increment"); ip.set_defaults(func=cmd_increment)
    isub = ip.add_subparsers(dest="inc_cmd", required=True)
    for _name in ("open", "close", "status"):
        _sp = isub.add_parser(_name)
        if _name == "open":
            _sp.add_argument("slug")
        _sp.add_argument("--factory", default=None)        # nivel fábrica: factories/<f>/docs/work
        _sp.add_argument("--product", default=None)        # nivel producto (requiere --factory)
    sub.add_parser("checkpoint").set_defaults(func=cmd_checkpoint)
    sp = sub.add_parser("journal"); sp.add_argument("--tail", type=int, default=12); sp.set_defaults(func=cmd_journal)
    sp = sub.add_parser("metrics"); sp.add_argument("--transcript", default=None)
    sp.add_argument("--overlap", action="store_true")  # M6: solapamiento auto-memoria vs docs/ (observador)
    sp.add_argument("--mem-dir", default=None)          # override de la ubicación del note-store
    sp.set_defaults(func=cmd_metrics)
    sp = sub.add_parser("recall")  # RETIRADO (ADR-019 §2): tombstone que redirige a Grep/`meta check`
    sp.add_argument("query", nargs="*"); sp.add_argument("--k", type=int, default=5); sp.set_defaults(func=cmd_recall)
    sub.add_parser("rehydrate").set_defaults(func=cmd_rehydrate)
    gp = sub.add_parser("graph"); gp.set_defaults(func=cmd_graph)
    gsub = gp.add_subparsers(dest="graph_cmd", required=True)
    gb = gsub.add_parser("build"); gb.add_argument("--factory", action="append", default=None)
    gq = gsub.add_parser("query"); gq.add_argument("--symbol", required=True)
    gr = gsub.add_parser("repomap"); gr.add_argument("--budget", type=int, default=4000)
    dp = sub.add_parser("doc"); dsub = dp.add_subparsers(dest="doc_cmd", required=True)
    ds = dsub.add_parser("slice"); ds.add_argument("doc"); ds.add_argument("selector", nargs="?", default=None)
    ds.add_argument("--abstract", action="store_true"); ds.set_defaults(func=cmd_doc_slice)
    do = dsub.add_parser("orphans"); do.set_defaults(func=cmd_doc_orphans)  # ADR-026 F1: non-gating observer
    jr = sub.add_parser("jdk-run"); jr.add_argument("--root", default=None); jr.add_argument("--label", default=None)
    jr.add_argument("cmd", nargs=argparse.REMAINDER); jr.set_defaults(func=cmd_jdk_run)
    bp = sub.add_parser("billing"); bp.add_argument("ledger", nargs="?", default=None); bp.set_defaults(func=cmd_billing)
    op = sub.add_parser("outcome"); op.add_argument("--baseline", default=None); op.add_argument("--save", default=None)
    op.add_argument("--billing", default=None); op.add_argument("--transcript", default=None); op.set_defaults(func=cmd_outcome)
    bm = sub.add_parser("benchmark"); bm.add_argument("name", nargs="?", default=None); bm.set_defaults(func=cmd_benchmark)
    sub.add_parser("dial").set_defaults(func=cmd_dial)
    plp = sub.add_parser("plan"); plp.set_defaults(func=cmd_plan)
    plsub = plp.add_subparsers(dest="plan_cmd", required=True)
    for _pc in ("check", "next", "status"):
        plsub.add_parser(_pc)
    return p


def cmd_benchmark(args) -> int:
    """REAIM-SWEET-SPOT (ADR-017 §4): measure product(s) against a product-class TARGET, re-derived from
    committed state (factory spec + product.yml + pin). `meta benchmark [name]` reports each declared
    product's profile vs the sweet-spot target; a `ceiling` that meets the target (decorative bound) or a
    `sweet_spot` that regressed is FAIL. With no benchmark file → N/A (honest). Same law as the gate."""
    from .verify.benchmark import evaluate, load_benchmark, render
    root = _meta_root()
    glob = f"benchmarks/{args.name}.yml" if getattr(args, "name", None) else "benchmarks/*.yml"
    files = sorted(root.glob(glob))
    if not files:
        print(f"VERDICT    benchmark — N/A   (exit 0)\nSUMMARY    no benchmarks ({glob})")
        return 0
    rc = 0
    for i, path in enumerate(files):
        bench = load_benchmark(path)
        results = evaluate(root, bench)
        if i:
            print()
        print(render(bench, results))
        if not (results and all(r.ok for r in results)):
            rc = 1
    return rc


def cmd_dial(args) -> int:
    """DIAL-MEASURE (ADR-017 §4): measure the draft→harden DIAL adoption, re-derived from committed state
    (each factory's station_sequence `tier`). Reports, per factory, the core/harden split — how many
    stations `--mode draft` defers (the rigor layer) vs runs (the spine). An adopted dial must defer a
    non-empty PROPER subset (≥1 core + ≥1 harden); all-harden is decorative → FAIL. Same law as the gate."""
    from .verify import dial
    print(dial.render(_meta_root()))
    return 0 if not [pr for f in dial.factories(_meta_root()) for pr in dial.gate_problems(_meta_root(), f)] else 1


def cmd_plan(args) -> int:
    """`meta plan check|next|status` (ADR-021 INC-4, PLAN-EXECUTE-SPLIT): the console for plan-as-DATA
    execution. `check` re-runs the `plan` gate's validator on `.gen/plan.json` standalone. `next` prints the
    next actionable WorkOrder as a slot manifest an S2 (Sonnet) session drops into `generate-slot`. `status`
    shows lifecycle counts + open escalations an S3 (Opus) close reads. Thin glue over `metafactory.plan`."""
    from . import plan as planmod
    root = _meta_root()
    p = planmod.load_plan(root)
    if p is None:
        print("VERDICT    plan — N/A   (exit 0)")
        print("SUMMARY    no `.gen/plan.json` — planning is opt-in (S1 writes it; see PLAN-EXECUTE-RUNBOOK)")
        return 0

    if args.plan_cmd == "check":
        problems = planmod.plan_problems(p)
        if problems:
            print("VERDICT    plan check — FAIL   (exit 1)")
            print(f"SUMMARY    {len(problems)} problem(s) in `.gen/plan.json`")
            for x in problems[:10]:
                print(f"           {x}")
            return 1
        s = planmod.status_summary(p)
        print("VERDICT    plan check — PASS   (exit 0)")
        print(f"SUMMARY    well-formed plan · {s['total']} WorkOrders · {len(s['done'])} done · next={s['next']}")
        return 0

    if args.plan_cmd == "next":
        wo = planmod.next_slot(p)
        if wo is None:
            s = planmod.status_summary(p)
            done = s["complete"]
            print(f"VERDICT    plan next — {'DONE' if done else 'BLOCKED'}   (exit 0)")
            if done:
                print("SUMMARY    plan complete — every WorkOrder is done/deferred; close it with S3")
            else:
                print(f"SUMMARY    blocked frontier: {s['blocked']} waiting on a not-done dep "
                      f"(did a dep end up `deferred`? check `meta plan status`)")
            return 0
        print("VERDICT    plan next — READY   (exit 0)")
        print(f"SUMMARY    next slot: {wo['slot_id']} — {wo.get('single_responsibility', '')}")
        print("NEXT       write this WorkOrder to `.gen/active_slot.json` (skill generate-slot) → verdict → "
              f"commit «{wo.get('commit', '<no commit planned>')}»")
        print("--- WorkOrder (slot manifest) ---")
        print(json.dumps(wo, indent=2, ensure_ascii=False))
        return 0

    # status
    s = planmod.status_summary(p)
    escs = planmod.load_escalations(root)
    broken = [(n, e) for n, e in escs if "_error" in e or planmod.escalation_problems(e)]
    print(f"VERDICT    plan status — {'ESCALADO' if escs else 'OK'}   (exit 0)")
    print(f"SUMMARY    {s['total']} WorkOrders · done {len(s['done'])} · pending {len(s['pending'])} · "
          f"deferred {len(s['deferred'])} · blocked {len(s['blocked'])} · next={s['next']}")
    if s["blocked"]:
        print(f"BLOQUEADOS {s['blocked']}")
    if escs:
        print(f"ESCALACIONES ({len(escs)}) — S3 (Opus) las revisa:")
        for name, e in escs:
            if "_error" in e:
                print(f"           {name}: MALFORMADA ({e['_error']})")
            else:
                print(f"           {name}: {e.get('slot_id', '?')} — {e.get('failure', '')[:70]} "
                      f"(intentos {e.get('attempts', '?')})")
        if broken:
            print("           ⚠ hay escalación(es) malformada(s) — el diente `plan` cae rojo hasta corregirlas")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
