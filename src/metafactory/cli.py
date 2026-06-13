"""cli — `meta <verb>`. The operator surface and the first verdict-bus materializer.

Verbs:
  check                      self-check the Meta-Factory repo (bus verdict + log on disk)
  new <spec.yml>             register a factory target (factories/<slug>/) from a spec
  station <id> --factory S   run meta-station <id> (build->verify->gate) building factory S
  product-run --factory S    run factory S's own product line e2e (M8's honest e2e)
  rtm --factory S            re-derive the RTM from artifacts (SATISFIED/UNSATISFIED)
  ci --rederive              external re-derivation: rebuild on clean state, demand pinned
  pin --factory S            write the pinned verdict (committed honest constant)
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
        {"name": "suite", "kind": "command",
         "cmd": [py, "-m", "pytest", "-q", "tests"]},
    ]
    ctx = RunContext(root=root, meta_root=root, slug="meta")
    from .verify.checks.registry import resolve_check
    cmds = [{"name": c["name"], "cmd": resolve_check(c, ctx, _Synthetic("metacheck"), {})} for c in checks]
    proof = ctx.verifier.verify_station("metacheck", cmds, root, pythonpath=ctx.pythonpath)
    log = _copy_metacheck_log(proof)
    proof["log_path"] = log
    v = report.from_proof("check", proof,
                          next_pass="repo verde — listo para station/ci",
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


def cmd_product_run(args) -> int:
    """Run factory S's own product line e2e — builds a REAL product and compiles+runs it.
    This is what M8 calls; render-green alone cannot pass it (façade-trap closed)."""
    slug = args.factory
    fdir = _factory_dir(slug)
    spec = load_spec(fdir / "factory.spec.yml")
    subst = _subst_for(spec, fdir)
    ctx = RunContext(root=fdir, meta_root=_meta_root(), slug=slug)
    pseq = load_sequence(fdir / "stations")
    if not pseq.active:
        print("VEREDICTO  product-run — FAIL   (exit 1)\nRESUMEN    la fábrica no tiene línea de producto")
        return 1
    last = None
    ok = True
    for st in pseq.active:
        run = run_station(ctx, st, pseq, subst, stations_dir=fdir / "stations", spec_path=fdir / "factory.spec.yml")
        last = run
        if not (run.passed and run.gate.opened):
            ok = False
            break
    v = report.from_proof("product-run", last.proof,
                          next_pass=f"producto e2e OK · {last.gate.line()}",
                          next_fail=f"producto roto · {last.gate.line()}")
    _print_verdict(v)
    return 0 if ok else 1


def cmd_rtm(args) -> int:
    """Re-derive the RTM from artifacts only (I-10): a requirement is SATISFIED iff every
    station in its satisfied_by has an OPEN gate (a passing, recompute-clean proof)."""
    slug = args.factory
    fdir = _factory_dir(slug)
    spec = load_spec(fdir / "factory.spec.yml")
    ctx = RunContext(root=fdir, meta_root=_meta_root(), slug=slug)
    rows, unsat = [], 0
    for req in spec.requirements:
        sat = True
        for sid in req.satisfied_by:
            proof = ctx.verifier.load_proof(fdir, sid)
            ok = proof is not None and ctx.verifier.gate_recompute_ok(proof)[0]
            sat = sat and ok
        status = "SATISFIED" if (sat and req.satisfied_by) else "UNSATISFIED"
        if status != "SATISFIED":
            unsat += 1
        rows.append((req.id, status, ",".join(req.satisfied_by)))
    print(f"VEREDICTO  rtm {slug} — {'COMPLETE' if unsat == 0 else 'INCOMPLETE'}   (exit {0 if unsat == 0 else 1})")
    print(f"RESUMEN    {len(rows) - unsat}/{len(rows)} requisitos SATISFIED (re-derivado de artefactos)")
    for rid, status, by in rows:
        print(f"           {rid} {status} <- {by}")
    return 0 if unsat == 0 else 1


def cmd_ci(args) -> int:
    """External re-derivation (two-verifier doctrine): wipe re-derivable state, rebuild the
    product line from source on a clean tree, and demand the pinned proof_sha. Any deviation
    (either direction) is red — a spontaneous PASS without proof is a façade, not a win."""
    slug = args.factory
    fdir = _factory_dir(slug)
    pinned_path = fdir / "pinned_verdict.json"
    if not pinned_path.exists():
        print(f"VEREDICTO  ci --rederive — FAIL   (exit 1)\nRESUMEN    no hay pinned_verdict.json en {slug} (corré `meta pin`)")
        return 1
    pinned = json.loads(pinned_path.read_text(encoding="utf-8"))
    shutil.rmtree(fdir / ".proof", ignore_errors=True)
    shutil.rmtree(fdir / "build", ignore_errors=True)
    rc = cmd_product_run(_ns(factory=slug))
    ctx = RunContext(root=fdir, meta_root=_meta_root(), slug=slug)
    mismatches = []
    for sid, want in pinned.items():
        proof = ctx.verifier.load_proof(fdir, sid)
        got = proof.get("proof_sha") if proof else None
        if got != want:
            mismatches.append(f"{sid}: pinned {str(want)[:12]} != re-derived {str(got)[:12]}")
    ok = rc == 0 and not mismatches
    print(f"VEREDICTO  ci --rederive {slug} — {'PASS' if ok else 'FAIL'}   (exit {0 if ok else 1})")
    print(f"RESUMEN    re-derivado en árbol limpio · {len(pinned) - len(mismatches)}/{len(pinned)} proof_sha == pineado")
    for m in mismatches[:5]:
        print(f"           {m}")
    if not ok and rc != 0:
        print("           product-run falló al reconstruir (producto roto en la fuente)")
    return 0 if ok else 1


def cmd_pin(args) -> int:
    """Write the pinned verdict from the current (honest) proofs of the product line."""
    slug = args.factory
    fdir = _factory_dir(slug)
    spec = load_spec(fdir / "factory.spec.yml")
    ctx = RunContext(root=fdir, meta_root=_meta_root(), slug=slug)
    pseq = load_sequence(fdir / "stations")
    pinned = {}
    for st in pseq.active:
        proof = ctx.verifier.load_proof(fdir, st.id)
        if proof is None or not proof.get("passed"):
            print(f"VEREDICTO  pin — FAIL   (exit 1)\nRESUMEN    {st.id} sin proof verde; corré product-run primero")
            return 1
        pinned[st.id] = proof["proof_sha"]
    (fdir / "pinned_verdict.json").write_text(json.dumps(pinned, indent=2) + "\n", encoding="utf-8")
    print(f"VEREDICTO  pin {slug} — PASS   (exit 0)\nRESUMEN    pineados {len(pinned)} proof_sha en pinned_verdict.json")
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


# ── tiny utilities ───────────────────────────────────────────────────────────
class _Synthetic:
    def __init__(self, id):
        self.id = id


def _ns(**kw):
    import types
    return types.SimpleNamespace(**kw)


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
    sp = sub.add_parser("verify"); sp.add_argument("--rerun", action="store_true"); sp.set_defaults(func=cmd_verify)
    sub.add_parser("doc-sync").set_defaults(func=cmd_doc_sync)
    sub.add_parser("checkpoint").set_defaults(func=cmd_checkpoint)
    sp = sub.add_parser("journal"); sp.add_argument("--tail", type=int, default=12); sp.set_defaults(func=cmd_journal)
    sp = sub.add_parser("metrics"); sp.add_argument("--transcript", default=None); sp.set_defaults(func=cmd_metrics)
    sp = sub.add_parser("recall"); sp.add_argument("query", nargs="+"); sp.add_argument("--k", type=int, default=5); sp.set_defaults(func=cmd_recall)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
