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


def _run_product_line(fdir: Path, meta_root: Path, slug: str, *, record_active: bool = True):
    """Run factory `slug`'s product line e2e on `fdir` (build a REAL product, compile+run it).
    Returns (rc, last_run). `record_active=False` keeps a hermetic re-derivation (the clean_runner
    gate) from leaking into the meta active-station pointer or the journal. Single source for both
    `product-run` and the two-verifier re-derivation (no divergence, ADR-005 §4)."""
    spec = load_spec(fdir / "factory.spec.yml")
    subst = _subst_for(spec, fdir)
    ctx = RunContext(root=fdir, meta_root=meta_root, slug=slug)
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


def cmd_product_run(args) -> int:
    """Run factory S's own product line e2e — builds a REAL product and compiles+runs it.
    This is what M8 calls; render-green alone cannot pass it (façade-trap closed)."""
    slug = args.factory
    fdir = _factory_dir(slug)
    rc, last = _run_product_line(fdir, _meta_root(), slug)
    if last is None:
        print("VEREDICTO  product-run — FAIL   (exit 1)\nRESUMEN    la fábrica no tiene línea de producto")
        return 1
    v = report.from_proof("product-run", last.proof,
                          next_pass=f"producto e2e OK · {last.gate.line()}",
                          next_fail=f"producto roto · {last.gate.line()}")
    _print_verdict(v)
    return 0 if rc == 0 else 1


def cmd_rtm(args) -> int:
    """Re-derive the build EVIDENCE TREE from artifacts only (I-10, C4): req → capability → station →
    proof → artifact. A requirement is SATISFIED iff every edge holds — its capability is real, every
    station's gate is OPEN (passing, recompute-clean proof), and every artifact its capability declares
    exists on disk. Single source `verify.rtm` (shared with the `rtm_tree` gate)."""
    from .verify import rtm
    slug = args.factory
    fdir = _factory_dir(slug)
    spec = load_spec(fdir / "factory.spec.yml")
    ctx = RunContext(root=fdir, meta_root=_meta_root(), slug=slug)
    nodes = rtm.build_tree(spec, ctx.verifier, fdir)
    print(rtm.render(slug, nodes))
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


def rederive_pinned(fdir: Path, meta_root: Path, slug: str, *, record_active: bool = True):
    """External re-derivation law (two-verifier doctrine, PF-10): wipe re-derivable state on
    `fdir`, rebuild the product line from source on a clean tree, recompute each proof_sha and
    demand the pinned verdict. ONE law shared by `meta ci`, the external CI and the clean_runner
    gate (M6). The gate runs it against a throwaway clone so custody is never the root of trust —
    replicability is. Returns (ok, mismatches, rc, has_pinned)."""
    fdir = Path(fdir)
    pinned_path = fdir / "pinned_verdict.json"
    if not pinned_path.exists():
        return False, [], 1, False
    pinned = json.loads(pinned_path.read_text(encoding="utf-8"))
    shutil.rmtree(fdir / ".proof", ignore_errors=True)
    shutil.rmtree(fdir / "build", ignore_errors=True)
    rc, _ = _run_product_line(fdir, meta_root, slug, record_active=record_active)
    v = RunContext(root=fdir, meta_root=meta_root, slug=slug).verifier
    mismatches = _compare_to_pinned(v, fdir, pinned)
    return (rc == 0 and not mismatches), mismatches, rc, True


def cmd_ci(args) -> int:
    """External re-derivation (two-verifier doctrine): wipe re-derivable state, rebuild the
    product line from source on a clean tree, and demand the pinned proof_sha. Any deviation
    (either direction) is red — a spontaneous PASS without proof is a façade, not a win."""
    slug = args.factory
    fdir = _factory_dir(slug)
    ok, mismatches, rc, has_pinned = rederive_pinned(fdir, _meta_root(), slug)
    if not has_pinned:
        print(f"VEREDICTO  ci --rederive — FAIL   (exit 1)\nRESUMEN    no hay pinned_verdict.json en {slug} (corré `meta pin`)")
        return 1
    pinned = json.loads((fdir / "pinned_verdict.json").read_text(encoding="utf-8"))
    print(f"VEREDICTO  ci --rederive {slug} — {'PASS' if ok else 'FAIL'}   (exit {0 if ok else 1})")
    print(f"RESUMEN    re-derivado en árbol limpio · {len(pinned) - len(mismatches)}/{len(pinned)} proof_sha == pineado")
    for m in mismatches[:5]:
        print(f"           {m}")
    if not ok and rc != 0:
        print("           product-run falló al reconstruir (producto roto en la fuente)")
    return 0 if ok else 1


def _pin_from_proofs(fdir: Path, meta_root: Path, slug: str):
    """Single source for writing the pinned verdict from the CURRENT (honest) proofs of the
    product line. Returns (ok, pinned_or_badstation). Reused by `meta pin` and `meta promote`."""
    ctx = RunContext(root=fdir, meta_root=meta_root, slug=slug)
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
    """Write the pinned verdict from the current (honest) proofs of the product line."""
    slug = args.factory
    ok, info = _pin_from_proofs(_factory_dir(slug), _meta_root(), slug)
    if not ok:
        print(f"VEREDICTO  pin — FAIL   (exit 1)\nRESUMEN    {info} sin proof verde; corré product-run primero")
        return 1
    print(f"VEREDICTO  pin {slug} — PASS   (exit 0)\nRESUMEN    pineados {len(info)} proof_sha en pinned_verdict.json")
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


def _work_dir(root: Path) -> Path:
    return root / "docs" / "work"


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
    """Lifecycle de incrementos (ADR-010): la unidad dentro de la cual vive todo cambio de código.
    `open` abre uno (rehúsa si ya hay), `close` lo cierra gateado, `status` muestra abierto + deuda."""
    root = _meta_root()
    from .memory import cadence, projection
    if args.inc_cmd == "status":
        inc = projection.open_increment(root) or "ninguno"
        has_debt, reason = cadence.debt(root)
        print(f"VEREDICTO  increment status — {'DEUDA' if has_debt else 'OK'}   (exit 0)")
        print(f"RESUMEN    incremento abierto: {inc}")
        print(f"CADENCIA   {reason}")
        return 0
    if args.inc_cmd == "open":
        cur = projection.open_increment(root)
        if cur is not None:
            print("VEREDICTO  increment open — FAIL   (exit 1)")
            print(f"RESUMEN    ya hay un incremento abierto: {cur} (cerralo: `meta increment close`)")
            return 1
        name = f"{args.slug.upper()}-INCREMENT.md"
        path = _work_dir(root) / name
        if path.exists():
            print("VEREDICTO  increment open — FAIL   (exit 1)")
            print(f"RESUMEN    docs/work/{name} ya existe; no lo piso")
            return 1
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_INCREMENT_SCAFFOLD.format(slug=args.slug.upper(), ts=_now_min()), encoding="utf-8")
        docs_manifest.sync(root)        # sella el doc nuevo + regenera INDEX
        projection.refresh(root)        # la proyección de STATE refleja el incremento abierto
        docs_manifest.sync(root)        # re-sella STATE
        print(f"VEREDICTO  increment open {args.slug} — PASS   (exit 0)")
        print(f"RESUMEN    abierto docs/work/{name} (Estado ABIERTO); editá Objetivo/Fases")
        print("PRÓXIMO    ya podés tocar código; cerralo con `meta increment close` (gateado)")
        return 0
    # close
    cur = projection.open_increment(root)
    if cur is None:
        print("VEREDICTO  increment close — FAIL   (exit 1)\nRESUMEN    no hay incremento abierto")
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
    path = _work_dir(root) / cur
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
    sp = sub.add_parser("product-run"); sp.add_argument("--factory", required=True); sp.set_defaults(func=cmd_product_run)
    sp = sub.add_parser("rtm"); sp.add_argument("--factory", required=True); sp.set_defaults(func=cmd_rtm)
    sp = sub.add_parser("ci"); sp.add_argument("--rederive", action="store_true"); sp.add_argument("--factory", default="dummy"); sp.set_defaults(func=cmd_ci)
    sp = sub.add_parser("pin"); sp.add_argument("--factory", required=True); sp.set_defaults(func=cmd_pin)
    sp = sub.add_parser("promote"); sp.add_argument("--factory", required=True)
    sp.add_argument("--baseline", default="baseline_verdicts.json"); sp.add_argument("--allow-hold", action="store_true")
    sp.set_defaults(func=cmd_promote)
    sp = sub.add_parser("verify"); sp.add_argument("--rerun", action="store_true"); sp.set_defaults(func=cmd_verify)
    sub.add_parser("doc-sync").set_defaults(func=cmd_doc_sync)
    ip = sub.add_parser("increment"); ip.set_defaults(func=cmd_increment)
    isub = ip.add_subparsers(dest="inc_cmd", required=True)
    isub.add_parser("open").add_argument("slug")
    isub.add_parser("close")
    isub.add_parser("status")
    sub.add_parser("checkpoint").set_defaults(func=cmd_checkpoint)
    sp = sub.add_parser("journal"); sp.add_argument("--tail", type=int, default=12); sp.set_defaults(func=cmd_journal)
    sp = sub.add_parser("metrics"); sp.add_argument("--transcript", default=None); sp.set_defaults(func=cmd_metrics)
    sp = sub.add_parser("recall"); sp.add_argument("query", nargs="+"); sp.add_argument("--k", type=int, default=5); sp.set_defaults(func=cmd_recall)
    sub.add_parser("rehydrate").set_defaults(func=cmd_rehydrate)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
