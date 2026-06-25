"""cli — `meta <verb>`. The operator surface and the first verdict-bus materializer.

Verbs:
  check                      self-check the Meta-Factory repo (bus verdict + log on disk)
  new <spec.yml>             register a factory target (factories/<slug>/) from a spec
  station <id> --factory S   run meta-station <id> (build->verify->gate) building factory S
  product-run --factory S    run factory S's own product line e2e (M8's honest e2e)
  rtm --factory S            re-derive the RTM from artifacts (SATISFIED/UNSATISFIED)
  ci --rederive              external re-derivation: rebuild on clean state, demand pinned
  pin --factory S            write the pinned verdict (committed honest constant)
  promote --factory S        Fase G: promote iff the engine passes a diverse scenario corpus AND no downstream verdict drops
  verify --rerun             re-verify the active station (Lock #3, used by the Stop hook)
  doc-sync                   stamp docs + regenerate INDEX (used by the PostToolUse hook)

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
        {"name": "suite", "kind": "command",
         "cmd": [py, "-m", "pytest", "-q", "tests"]},
    ]
    ctx = RunContext(root=root, meta_root=root, slug="meta")
    from .verify.checks.registry import resolve_check
    cmds = [{"name": c["name"], "cmd": resolve_check(c, ctx, _Synthetic("metacheck"), {})} for c in checks]
    proof = ctx.verifier.verify_station("metacheck", cmds, root, pythonpath=ctx.pythonpath)
    log = _copy_metacheck_log(proof)
    proof["log_path"] = log
    npass = "repo verde — listo para station/ci"
    nfacts = _unnarrated_count(root)
    if nfacts:
        npass += f" · {nfacts} hecho(s) sin narrar: `meta checkpoint`"
    from .memory import cadence
    if cadence.debt(root)[0]:
        npass += " · cadencia: código sin commitear (`meta increment status`)"
    v = report.from_proof("check", proof, next_pass=npass,
                          next_fail="abrí el ARTEFACTO o corré `triage` sobre él; no lo pegues al contexto")
    _print_verdict(v)
    return v.exit_code


def cmd_new(args) -> int:
    spec = load_spec(args.spec)
    problems = validate(spec)
    if not spec.slug:
        print("VEREDICTO  new — FAIL   (exit 1)\nRESUMEN    spec sin slug; no se puede registrar")
        return 1
    fdir = _factory_dir(spec.slug)
    fdir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.spec, fdir / "factory.spec.yml")
    (fdir / ".metafactory.json").write_text(
        json.dumps({"slug": spec.slug, "spec": "factory.spec.yml", "produces": spec.produces}, indent=2) + "\n",
        encoding="utf-8")
    status = "PASS" if not problems else "PROVISIONAL"
    print(f"VEREDICTO  new {spec.slug} — {status}   (exit 0)")
    print(f"RESUMEN    registrado en factories/{spec.slug}/ · M0 validate: {len(problems)} problema(s)")
    if problems:
        for p in problems[:5]:
            print(f"           {p}")
        print("PRÓXIMO    corregí el spec; `meta station m00` es la gate autoritativa")
    else:
        print("PRÓXIMO    meta station m00 --factory " + spec.slug)
    return 0


def _run_one(ctx, station, seq, subst, stations_dir, spec_path, *, verb, build=True) -> int:
    run = run_station(ctx, station, seq, subst, stations_dir=stations_dir, spec_path=spec_path, build=build)
    v = report.from_proof(f"{verb} {station.id}", run.proof,
                          next_pass=run.gate.line(),
                          next_fail=run.gate.line() + " — corregí y re-verificá")
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
        print(f"VEREDICTO  station {args.id} — FAIL   (exit 1)\nRESUMEN    meta-estación {args.id} no existe")
        return 1
    return _run_one(ctx, station, seq, subst, _meta_stations_dir(), fdir / "factory.spec.yml", verb="station")


def _run_product_line(fdir: Path, meta_root: Path, slug: str, *, record_active: bool = True,
                      chassis: Path | None = None):
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
    root, chassis = _resolve_target(slug, product)
    if product and not (root / "product.yml").is_file():
        print(f"VEREDICTO  product-run — FAIL   (exit 1)\nRESUMEN    no existe el producto {product!r} en {slug} "
              f"(creálo con `meta product new`)")
        return 1
    rc, last = _run_product_line(root, _meta_root(), slug, chassis=chassis)
    if last is None:
        print("VEREDICTO  product-run — FAIL   (exit 1)\nRESUMEN    la fábrica no tiene línea de producto")
        return 1
    label = f"product-run {slug}/{product}" if product else "product-run"
    v = report.from_proof(label, last.proof,
                          next_pass=f"producto e2e OK · {last.gate.line()}",
                          next_fail=f"producto roto · {last.gate.line()}")
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
        print(f"VEREDICTO  product — FAIL   (exit 1)\nRESUMEN    no existe la fábrica {slug!r}")
        return 1
    if args.prod_cmd == "list":
        products = _list_products(slug)
        print(f"VEREDICTO  product list {slug} — {len(products) + 1} producto(s)   (exit 0)")
        print(f"RESUMEN    default + {len(products)} instancia(s) (cada una con pin propio)")
        dpin = "pin ✓" if (fdir / "pinned_verdict.json").is_file() else "sin pin"
        print(f"           default (raíz de la fábrica) · {dpin}")
        for p in products:
            ppin = "pin ✓" if (_product_dir(slug, p) / "pinned_verdict.json").is_file() else "sin pin"
            print(f"           {p} (products/{p}/) · {ppin}")
        return 0
    # new
    name = args.name
    product_root = _product_dir(slug, name)
    if (product_root / "product.yml").is_file():
        print(f"VEREDICTO  product new — FAIL   (exit 1)\nRESUMEN    el producto {name!r} ya existe en {slug} "
              f"(no lo piso)")
        return 1
    blueprint_path = Path(args.blueprint)
    if not blueprint_path.is_file():
        print(f"VEREDICTO  product new — FAIL   (exit 1)\nRESUMEN    no existe el blueprint {args.blueprint}")
        return 1
    product_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(blueprint_path, product_root / "product.yml")
    rc, last = _run_product_line(product_root, meta_root, slug, chassis=fdir)
    if last is None or rc != 0:
        line = last.gate.line() if last is not None else "la fábrica no tiene línea de producto"
        print(f"VEREDICTO  product new {slug}/{name} — FAIL   (exit 1)\nRESUMEN    el producto no construye verde · {line}")
        print("PRÓXIMO    corregí el blueprint products/{0}/product.yml y reintentá".format(name))
        return 1
    pin_ok, info = _pin_from_proofs(product_root, meta_root, slug, chassis=fdir)
    if not pin_ok:
        print(f"VEREDICTO  product new {slug}/{name} — FAIL   (exit 1)\nRESUMEN    {info} sin proof verde al pinear")
        return 1
    print(f"VEREDICTO  product new {slug}/{name} — PASS   (exit 0)")
    print(f"RESUMEN    instancia products/{name}/ construida e2e + pineada ({len(info)} estaciones)")
    print(f"PRÓXIMO    re-derivá su pin con `meta ci --rederive --factory {slug} --product {name}`")
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
        return False, f"{label}: SIN PINEAR (no hay pinned_verdict.json; corré `meta pin`)"
    pinned = json.loads((root / "pinned_verdict.json").read_text(encoding="utf-8"))
    note = f"{label}: {len(pinned) - len(mismatches)}/{len(pinned)} proof_sha == pineado"
    if not ok:
        note += " · " + ("; ".join(mismatches[:3]) if mismatches else f"product-run rc={rc} (producto roto)")
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
        print(f"VEREDICTO  ci --rederive {slug} --all-products — {'PASS' if ok else 'FAIL'}   (exit {0 if ok else 1})")
        print(f"RESUMEN    {sum(r[0] for r in results)}/{len(results)} productos re-derivados == su pin")
        for _, note in results:
            print(f"           {note}")
        return 0 if ok else 1
    product = getattr(args, "product", None)
    ok, note = _ci_one(slug, product)
    label = f"{slug}/{product}" if product else slug
    print(f"VEREDICTO  ci --rederive {label} — {'PASS' if ok else 'FAIL'}   (exit {0 if ok else 1})")
    print(f"RESUMEN    re-derivado en árbol limpio · {note}")
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
    `--product <p>` pins a named INSTANCE (R1), writing products/<p>/pinned_verdict.json."""
    slug = args.factory
    product = getattr(args, "product", None)
    root, chassis = _resolve_target(slug, product)
    ok, info = _pin_from_proofs(root, _meta_root(), slug, chassis=chassis)
    if not ok:
        print(f"VEREDICTO  pin — FAIL   (exit 1)\nRESUMEN    {info} sin proof verde; corré product-run primero")
        return 1
    label = f"pin {slug}/{product}" if product else f"pin {slug}"
    print(f"VEREDICTO  {label} — PASS   (exit 0)\nRESUMEN    pineados {len(info)} proof_sha en pinned_verdict.json")
    return 0


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
        print(f"VEREDICTO  promote {slug} — FAIL   (exit 1)\n"
              f"RESUMEN    {slug} no está en el baseline ({args.baseline}); "
              f"agregalo con `meta pin`+baseline antes de promover una mejora")
        return 1

    # 0. G2 gate — the engine must still behave across the DIVERSE scenario corpus before ANY promotion
    #    (G-8 root: diverse spec shapes exercise the engine; `SELF-IMPROVEMENT.md §4`). This protects the
    #    engine's BEHAVIOR (vs blast_radius, which protects the downstream verdicts); a regressed engine
    #    makes every promotion unsafe, so it precedes the downstream sweep.
    corpus_path = meta_root / "scenarios" / "corpus.yml"
    if not corpus_path.exists():
        print(f"VEREDICTO  promote {slug} — FAIL   (exit 2)\n"
              f"RESUMEN    no hay corpus de scenarios ({corpus_path}); G2 exige ejercitar el motor "
              f"en N formas diversas antes de promover")
        return 2
    corpus_dir, scenarios = SC.load_corpus(corpus_path)
    c_action, c_detail = SC.decide(corpus_dir, scenarios)
    if c_action != "ok":
        print(f"VEREDICTO  promote {slug} — BLOQUEADA   (exit 2)\n"
              f"RESUMEN    el motor no pasa el corpus de scenarios diversos "
              f"(pin y baseline INTACTOS):")
        for r in (c_detail if isinstance(c_detail, list) else [c_detail])[:6]:
            print(f"           {r}")
        return 2

    # 1. Re-derive the whole downstream sweep ONCE (the candidate is part of it) on clean clones,
    #    then take the PURE decision (the law shared with the tests).
    candidates = BR.sweep(meta_root, baseline)
    cand_x = candidates[slug]
    action, detail = BR.decide(candidates, baseline, slug, allow_hold=args.allow_hold)
    if action == "facade":   # §4: a hold/regression of the target itself is nothing to promote.
        print(f"VEREDICTO  promote {slug} — FAIL   (exit 2)\n"
              f"RESUMEN    nada que promover: {detail} "
              f"[{slug} candidato {cand_x.get('rtm_satisfied')}/{cand_x.get('rtm_total')} "
              f"vs baseline {baseline[slug].get('rtm_satisfied')}/{baseline[slug].get('rtm_total')}]")
        return 2
    if action == "blast":    # a downstream factory would lower its verdict — pin/baseline INTACTOS.
        print(f"VEREDICTO  promote {slug} — BLOQUEADA   (exit 2)\n"
              f"RESUMEN    blast-radius: la promoción bajaría el veredicto de una fábrica downstream "
              f"(pin y baseline INTACTOS):")
        for r in detail[:6]:
            print(f"           {r}")
        return 2
    if action == "decorative":
        print(f"VEREDICTO  promote {slug} — FAIL   (exit 2)\n"
              f"RESUMEN    gate decorativo: la ley de dominación no tiene dientes (no se promueve a ciegas)")
        return 2

    # 2. PROMOTE: refresh the candidate's REAL proofs, re-pin, and bump the baseline. No commit —
    #    the diff (improvement + pin + baseline) ascends reviewed (§4).
    improved = detail
    fdir = _factory_dir(slug)
    rc, _ = _run_product_line(fdir, meta_root, slug)
    if rc != 0:
        print(f"VEREDICTO  promote {slug} — FAIL   (exit 1)\n"
              f"RESUMEN    la línea real de {slug} no reconstruye al re-pinear (no debería tras el barrido)")
        return 1
    pin_ok, info = _pin_from_proofs(fdir, meta_root, slug)
    if not pin_ok:
        print(f"VEREDICTO  promote {slug} — FAIL   (exit 1)\nRESUMEN    {info} sin proof verde al re-pinear")
        return 1
    baseline[slug] = cand_x
    V.save_baseline(baseline_path, baseline)
    verb = "mejoró" if improved else "mantuvo (--allow-hold)"
    print(f"VEREDICTO  promote {slug} — PASS   (exit 0)\n"
          f"RESUMEN    {slug} {verb} a {cand_x.get('rtm_satisfied')}/{cand_x.get('rtm_total')}; "
          f"re-pineado ({len(info)} estaciones) + baseline subido; corpus verde "
          f"({len(scenarios)} scenarios diversos) + blast-radius verde "
          f"({len(baseline)} fábricas, ninguna bajó). Promoción NO committeada (subí por diff revisado, §4).")
    return 0


def cmd_verify(args) -> int:
    """Re-verify the active station (Lock #3). Used by the Stop hook: exit≠0 => block turn."""
    active_path = _meta_root() / ".proof" / "active.json"
    if not active_path.exists():
        print("VEREDICTO  verify --rerun — PASS   (exit 0)\nRESUMEN    no hay estación activa que re-verificar")
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
        print("VEREDICTO  verify --rerun — PASS   (exit 0)\nRESUMEN    estación activa desconocida; nada que bloquear")
        return 0
    return _run_one(ctx, station, seq, subst, stations_dir, spec_path, verb="verify", build=False)


def cmd_doc_sync(args) -> int:
    changed = docs_manifest.sync(_meta_root())
    print(f"doc-sync: {len(changed)} doc(s) re-stamped; INDEX.md regenerated")
    return 0


# ── incremento (disciplina de commit, ADR-010) ───────────────────────────────
_INCREMENT_SCAFFOLD = """# Incremento {slug}

> **Doc de gobierno.** Estado: **ABIERTO** (creado {ts}). Cerralo con `meta increment close`
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
        print("VEREDICTO  increment — FAIL   (exit 1)\nRESUMEN    --product requiere --factory")
        return 1
    workdir = _work_dir(root, factory, product)
    label = _level_label(factory, product)
    wd_rel = workdir.relative_to(root)
    if args.inc_cmd == "status":
        inc = cadence.open_increment_in(workdir) or "ninguno"
        has_debt, reason = cadence.debt(root)
        print(f"VEREDICTO  increment status [{label}] — {'DEUDA' if has_debt else 'OK'}   (exit 0)")
        print(f"RESUMEN    incremento abierto ({wd_rel}/): {inc}")
        print(f"CADENCIA   {reason}")
        return 0
    if args.inc_cmd == "open":
        cur = cadence.open_increment_in(workdir)
        if cur is not None:
            print("VEREDICTO  increment open — FAIL   (exit 1)")
            print(f"RESUMEN    ya hay un incremento abierto en [{label}]: {cur} (cerralo primero)")
            return 1
        name = f"{args.slug.upper()}-INCREMENT.md"
        path = workdir / name
        if path.exists():
            print("VEREDICTO  increment open — FAIL   (exit 1)")
            print(f"RESUMEN    {wd_rel}/{name} ya existe; no lo piso")
            return 1
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_INCREMENT_SCAFFOLD.format(slug=args.slug.upper(), ts=_now_min()), encoding="utf-8")
        docs_manifest.sync(root)        # sella el doc nuevo (si es meta) + regenera INDEX
        projection.refresh(root)        # la proyección de STATE refleja el incremento meta abierto
        docs_manifest.sync(root)        # re-sella STATE
        print(f"VEREDICTO  increment open {args.slug} [{label}] — PASS   (exit 0)")
        print(f"RESUMEN    abierto {wd_rel}/{name} (Estado ABIERTO); editá Objetivo/Fases")
        print("PRÓXIMO    ya podés tocar código del nivel; cerralo con `meta increment close` (gateado)")
        return 0
    # close
    cur = cadence.open_increment_in(workdir)
    if cur is None:
        print(f"VEREDICTO  increment close — FAIL   (exit 1)\nRESUMEN    no hay incremento abierto en [{label}]")
        return 1
    has_debt, reason = cadence.debt(root)
    if has_debt:
        print("VEREDICTO  increment close — FAIL   (exit 1)")
        print(f"RESUMEN    no podés cerrar con deuda: {reason}")
        print("PRÓXIMO    commiteá el trabajo probado (mensaje con trailers I-10) y reintentá")
        return 1
    if not _active_station_green(root):
        print("VEREDICTO  increment close — FAIL   (exit 1)")
        print("RESUMEN    la estación activa no recompone verde; no se cierra trabajo roto")
        return 1
    path = workdir / cur
    text = path.read_text(encoding="utf-8")
    path.write_text(re.sub(r"Estado:\s*\*\*ABIERTO\*\*", f"Estado: **CERRADO** ({_now_min()})", text, count=1),
                    encoding="utf-8")
    docs_manifest.sync(root)
    projection.refresh(root)
    docs_manifest.sync(root)
    print(f"VEREDICTO  increment close {cur} — PASS   (exit 0)")
    print(f"RESUMEN    {cur} → CERRADO; proyección de STATE refrescada")
    print("PRÓXIMO    narrá el episodio en LOG (`meta checkpoint` te ofrece los hechos sin narrar)")
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
    print(f"VEREDICTO  checkpoint — {'proyección refrescada' if changed else 'proyección al día'}   (exit 0)")
    print(f"RESUMEN    STATE proyectado de hechos · desde el último LOG ({last}): "
          f"{len(runs)} station_run · {len(delegs)} delegation · {len(commits)} commit")
    if runs or commits or delegs:
        print("PRÓXIMO    el juicio NO se fuerza, se OFRECE — agregá el SIGNIFICADO al LOG. Hechos sin narrar:")
        print(f"           ## {journal.now()[:16]}Z — <título: qué cambió y por qué>")
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
            print(f"           - delegación: {d.get('subagent_type')}/{d.get('model')} — {d.get('description', '')}")
    else:
        print("PRÓXIMO    nada nuevo que narrar desde el último episodio de LOG")
    return 0


def cmd_journal(args) -> int:
    root = _meta_root()
    from .memory import journal
    evs = journal.read(root, limit=args.tail)
    print(f"VEREDICTO  journal — {len(evs)} evento(s) (tail {args.tail})   (exit 0)")
    for e in evs:
        extra = {k: v for k, v in e.items() if k not in ("ts", "kind")}
        print(f"  {e['ts']} {e['kind']}  {extra}")
    return 0


def cmd_metrics(args) -> int:
    root = _meta_root()
    from .memory import metrics
    print(metrics.render(root, transcript=getattr(args, "transcript", None)))
    return 0


def cmd_recall(args) -> int:
    root = _meta_root()
    from .memory import recall
    query = " ".join(args.query)
    print(recall.render(root, query, recall.recall(root, query, k=args.k)))
    return 0


def cmd_rehydrate(args) -> int:
    from .memory import rehydrate
    print(rehydrate.build_payload(_meta_root()))
    return 0


def cmd_graph(args) -> int:
    """Project-spine (ADR-017): build the content-addressed graph, query it 2-hop (no LLM), repo-map."""
    from .graph.cli import run_graph
    return run_graph(args, _meta_root())


def cmd_billing(args) -> int:
    """Show the delegation split (Opus·Sonnet·Haiku) of a billing-ledger (ADR-017, Fase 5)."""
    from .graph.cli import run_billing
    return run_billing(args, _meta_root())


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
    p = argparse.ArgumentParser(prog="meta", description="Meta-Factory — la fábrica que fabrica fábricas")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check").set_defaults(func=cmd_check)
    sp = sub.add_parser("new"); sp.add_argument("spec"); sp.set_defaults(func=cmd_new)
    sp = sub.add_parser("station"); sp.add_argument("id"); sp.add_argument("--factory", required=True); sp.set_defaults(func=cmd_station)
    sp = sub.add_parser("product-run"); sp.add_argument("--factory", required=True); sp.add_argument("--product", default=None); sp.set_defaults(func=cmd_product_run)
    pp = sub.add_parser("product"); pp.set_defaults(func=cmd_product)
    psub = pp.add_subparsers(dest="prod_cmd", required=True)
    pn = psub.add_parser("new"); pn.add_argument("--factory", required=True); pn.add_argument("--name", required=True); pn.add_argument("blueprint")
    pl = psub.add_parser("list"); pl.add_argument("--factory", required=True)
    sp = sub.add_parser("rtm"); sp.add_argument("--factory", required=True); sp.add_argument("--product", default=None); sp.set_defaults(func=cmd_rtm)
    sp = sub.add_parser("ci"); sp.add_argument("--rederive", action="store_true"); sp.add_argument("--factory", default="dummy")
    sp.add_argument("--product", default=None); sp.add_argument("--all-products", action="store_true"); sp.set_defaults(func=cmd_ci)
    sp = sub.add_parser("pin"); sp.add_argument("--factory", required=True); sp.add_argument("--product", default=None); sp.set_defaults(func=cmd_pin)
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
    sp = sub.add_parser("metrics"); sp.add_argument("--transcript", default=None); sp.set_defaults(func=cmd_metrics)
    sp = sub.add_parser("recall"); sp.add_argument("query", nargs="+"); sp.add_argument("--k", type=int, default=5); sp.set_defaults(func=cmd_recall)
    sub.add_parser("rehydrate").set_defaults(func=cmd_rehydrate)
    gp = sub.add_parser("graph"); gp.set_defaults(func=cmd_graph)
    gsub = gp.add_subparsers(dest="graph_cmd", required=True)
    gb = gsub.add_parser("build"); gb.add_argument("--factory", action="append", default=None)
    gq = gsub.add_parser("query"); gq.add_argument("--symbol", required=True)
    gr = gsub.add_parser("repomap"); gr.add_argument("--budget", type=int, default=4000)
    bp = sub.add_parser("billing"); bp.add_argument("ledger", nargs="?", default=None); bp.set_defaults(func=cmd_billing)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
