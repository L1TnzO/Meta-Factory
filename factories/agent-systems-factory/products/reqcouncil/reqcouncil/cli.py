"""reqcouncil CLI. H1 exposes `ingest`, H2 adds `eval e0`, H3 adds `run` + `eval e1`,
H5 adds the HITL review flags + the `review` catch-rate drill.

    python -m reqcouncil ingest datasets/inter2us/data/public_interview/int1.txt
    python -m reqcouncil eval e0                      # full 760-pair calibration (gate)
    python -m reqcouncil eval e0 --limit 10           # cheap smoke (never gate evidence)
    python -m reqcouncil eval e1                      # council over int1.txt (gate: fidelity)
    python -m reqcouncil eval e1 --baseline runs/pinned/e1-dsv4flash/run.json   # H4 gate
    python -m reqcouncil eval e4 --arm a --corpus interview   # ablation cell (Tabla 4.5)
    python -m reqcouncil eval gates                   # H6: pinned runs vs thresholds.yml
    python -m reqcouncil run meeting.txt              # council + interactive HITL review
    python -m reqcouncil run meeting.txt --review auto        # unattended (recorded)
    python -m reqcouncil review --draft runs/.../draft.json --decoys 3 --seed 7  # drill
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .ingest.parser import parse_transcript
from .ingest.chunker import chunk_turns
from .ingest.csv_io import chunks_to_csv


def _cmd_eval(args: argparse.Namespace) -> int:
    # Imported lazily: eval needs pyyaml + network config; ingest stays stdlib-only.
    from .config import load_models, load_thresholds
    from .eval.e0 import run_e0
    from .eval.golden import CORPORA
    from .llm import ChatClient

    if args.experiment == "gates":
        # H6 §7: hermetic, zero-LLM — pinned runs vs thresholds; exit 1 on any RED.
        # METAFACTORY_EVAL_EVIDENCE (ADR-025 §3, Meta-Factory `eval_floor` two-sided tooth): when set,
        # gate against THAT evidence dir instead of the default runs/pinned — lets the substrate swap in
        # a degraded fixture and demand the SAME command flip red, without touching gates.py.
        from .eval.gates import evaluate_gates
        import os
        pinned_dir = Path(os.environ["METAFACTORY_EVAL_EVIDENCE"]) if os.environ.get("METAFACTORY_EVAL_EVIDENCE") else None
        result = evaluate_gates(load_thresholds(), pinned_dir=pinned_dir)
        print(result.report)
        return 0 if result.green else 1
    if args.experiment == "e1":
        return _cmd_eval_e1(args)
    if args.experiment == "e2":
        return _cmd_eval_e2(args)
    if args.experiment == "e3":
        return _cmd_eval_e3(args)
    if args.experiment == "e4":
        return _cmd_eval_e4(args)
    if args.experiment != "e0":
        print(f"unknown experiment {args.experiment!r} (H6 ships e0, e1, e2, e3, e4, gates)",
              file=sys.stderr)
        return 2
    models_cfg = load_models()
    client = ChatClient.from_config(models_cfg, alternate=args.model)
    # Bare runs inherit the foundation model's arm slug (decisions/003), so a plain
    # `eval e0` RESUMES the foundation arm's cache instead of clobbering runs/e0.
    arm = args.model or models_cfg["foundation_model"].get("arm")
    corpora = CORPORA if args.corpus == "all" else (args.corpus,)
    result = run_e0(
        client,
        models_cfg,
        load_thresholds(),
        runs_dir=Path(default_runs_dir(args.runs_dir, arm)),
        corpora=corpora,
        limit=args.limit,
        workers=args.workers,
    )
    print(result.report)
    if args.limit is not None or args.corpus != "all":
        return 0  # partial runs never claim the gate, green or red
    return 0 if result.green else 1


def _cmd_eval_e1(args: argparse.Namespace) -> int:
    from .config import load_council, load_models, load_thresholds
    from .eval.e1 import run_e1

    models_cfg = load_models()
    arm = models_cfg["foundation_model"].get("arm")
    runs_dir = args.runs_dir
    if runs_dir == "runs/e0":  # the shared default belongs to e0; derive e1's own
        runs_dir = f"runs/e1-{arm}" if arm else "runs/e1"
    result = run_e1(
        models_cfg,
        load_council(),
        load_thresholds(),
        runs_dir=Path(runs_dir),
        use_store=not args.no_store,
        verify_workers=args.workers,
        baseline_path=Path(args.baseline) if args.baseline else None,
    )
    print(result.report)
    return 0 if result.green else 1


def _cmd_eval_e2(args: argparse.Namespace) -> int:
    from .config import load_council, load_models, load_thresholds
    from .eval.e2 import run_e2
    from .eval.wepgcomp import CORPORA as E2_CORPORA

    corpora = E2_CORPORA if args.corpus == "all" else (args.corpus,)
    for corpus in corpora:
        if corpus not in E2_CORPORA:
            print(f"e2 corpus must be one of {E2_CORPORA} (or all), got {corpus!r}",
                  file=sys.stderr)
            return 2
    ok = True
    for corpus in corpora:
        if args.runs_dir == "runs/e0":  # the shared default belongs to e0
            runs_dir = f"runs/e2-{corpus}"
        else:  # explicit dir: suffix per corpus only when running several
            runs_dir = args.runs_dir if len(corpora) == 1 else f"{args.runs_dir}-{corpus}"
        result = run_e2(
            load_models(), load_council(), load_thresholds(),
            corpus=corpus, runs_dir=Path(runs_dir),
            use_store=not args.no_store, verify_workers=args.workers,
        )
        print(result.report)
        ok = ok and result.green
    return 0 if ok else 1


def _cmd_eval_e3(args: argparse.Namespace) -> int:
    from .config import load_council, load_models, load_thresholds
    from .eval.e3 import run_e3

    runs_dir = args.runs_dir
    if runs_dir == "runs/e0":  # the shared default belongs to e0
        runs_dir = f"runs/e3-n{args.n}-seed{args.seed}"
    result = run_e3(
        load_models(), load_council(), load_thresholds(),
        runs_dir=Path(runs_dir), n=args.n, seed=args.seed,
        use_store=not args.no_store, verify_workers=args.workers,
    )
    print(result.report)
    return 0  # E3 is REPORTED, not gated (design/03 §3): summary + pins speak


def _cmd_eval_e4(args: argparse.Namespace) -> int:
    from .config import load_council, load_models, load_thresholds
    from .eval.e4 import ARMS, E4_CORPORA, run_e4

    corpora = E4_CORPORA if args.corpus == "all" else (args.corpus,)
    for corpus in corpora:
        if corpus not in E4_CORPORA:
            print(f"e4 corpus must be one of {E4_CORPORA} (or all), got {corpus!r}",
                  file=sys.stderr)
            return 2
    arms = ARMS if args.arm == "all" else (args.arm,)
    runs_dir = args.runs_dir
    if runs_dir == "runs/e0":  # the shared default belongs to e0
        runs_dir = "runs/e4"
    result = run_e4(
        load_models(), load_council(), load_thresholds(),
        runs_dir=Path(runs_dir), arms=arms, corpora=corpora,
        use_store=not args.no_store, verify_workers=args.workers,
    )
    print(result.report)
    if result.pending:
        print(f"{result.pending} cell(s) PENDING (see table notes)", file=sys.stderr)
    return 0  # E4 is REPORTED, not gated (design/03 §3): the table speaks


def _resolve_reviewer(args: argparse.Namespace):
    """HITL reviewer selection (H5). Explicit choice always wins; a TTY defaults to the
    interactive reviewer; a non-TTY run without an explicit choice is REFUSED — there
    is no silent unattended path (`--review auto` exists and is recorded as such)."""
    from .review import auto_reviewer, cli_reviewer, file_reviewer

    if getattr(args, "decisions", None):
        return file_reviewer(args.decisions)
    choice = getattr(args, "review", None)
    if choice is None:
        if sys.stdin.isatty():
            choice = "cli"
        else:
            print(
                "no TTY and no explicit review mode: pass --review auto (unattended, "
                "recorded as such) or --decisions decisions.json",
                file=sys.stderr,
            )
            return None
    return auto_reviewer if choice == "auto" else cli_reviewer()


def _cmd_run(args: argparse.Namespace) -> int:
    from .config import load_council, load_models, load_thresholds
    from .council.pipeline import execute_run

    reviewer = _resolve_reviewer(args)
    if reviewer is None:
        return 2
    source = args.source or Path(args.transcript).stem
    runs_dir = Path(args.runs_dir or f"runs/run-{source}")
    outcome = execute_run(
        Path(args.transcript).read_text(encoding="utf-8"),
        source,
        models_cfg=load_models(),
        council_cfg=load_council(),
        thresholds=load_thresholds(),
        runs_dir=runs_dir,
        dsn=args.dsn,
        verify_workers=args.workers,
        reviewer=reviewer,
    )
    grounded = sum(1 for c in outcome.final if c.grounded)
    print(
        f"{len(outcome.final)} requirements ({grounded} grounded) -> {runs_dir}/draft.json",
        file=sys.stderr,
    )
    print(json.dumps(outcome.draft["cardinality"], ensure_ascii=False), file=sys.stderr)
    return 0


def default_runs_dir(runs_dir: str, arm: str | None) -> str:
    """Each judge arm gets its own runs dir so reports/caches never collide.

    Explicit --runs-dir always wins; the derivation only fills the default. `arm` is
    the alternate name, or the foundation model's `arm:` slug for bare runs. Bare
    `runs/e0` survives only for arm-less configs (the legacy qwen dir predates arms;
    re-runs of it pass --runs-dir runs/e0 explicitly — see config/models.yml).
    """
    if arm is not None and runs_dir == "runs/e0":
        return f"runs/e0-{arm}"
    return runs_dir


def _cmd_review(args: argparse.Namespace) -> int:
    """Catch-rate drill (H5, report §4.3.d) — zero LLM, from a SAVED draft.json."""
    from .config import load_council
    from .review import cli_reviewer, file_reviewer
    from .review.drill import run_drill

    draft = json.loads(Path(args.draft).read_text(encoding="utf-8"))
    if args.transcript:
        transcript_path = Path(args.transcript)
    else:
        from .eval.golden import INTERVIEW, corpus_dir
        transcript_path = corpus_dir(INTERVIEW) / "int1.txt"

    if args.decisions:
        reviewer = file_reviewer(args.decisions)
    elif sys.stdin.isatty():
        reviewer = cli_reviewer()
    else:
        print("no TTY: the drill needs a human at the keyboard or --decisions file.json",
              file=sys.stderr)
        return 2

    low_confidence = float(
        (load_council().get("review") or {}).get("low_confidence", 0.6)
    )
    report = run_drill(
        draft,
        transcript_path.read_text(encoding="utf-8"),
        low_confidence=low_confidence,
        decoys=args.decoys,
        seed=args.seed,
        reviewer=reviewer,
        out_dir=Path(args.out),
    )
    rate = report["catch_rate"]
    print(
        f"decoys {len(report['caught'])}/{report['decoys_present']} caught"
        f" (catch_rate {rate if rate is not None else 'n/a'})"
        f" · false alarms {len(report['false_alarms'])}"
        f" -> {Path(args.out) / 'review-report.json'}",
        file=sys.stderr,
    )
    return 0


def _cmd_ingest(args: argparse.Namespace) -> int:
    text = Path(args.transcript).read_text(encoding="utf-8")
    source = args.source or Path(args.transcript).stem
    chunks = chunk_turns(parse_transcript(text))
    csv_text = chunks_to_csv(source, chunks)
    if args.out:
        Path(args.out).write_text(csv_text, encoding="utf-8")
        print(f"{len(chunks)} chunks -> {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(csv_text)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="reqcouncil")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="parse + chunk a transcript to chunks CSV")
    ingest.add_argument("transcript", help="path to a speaker-tagged transcript (.txt)")
    ingest.add_argument("--source", default=None, help="source id (default: file stem)")
    ingest.add_argument("--out", default=None, help="output CSV path (default: stdout)")
    ingest.set_defaults(func=_cmd_ingest)

    run = sub.add_parser("run", help="run the council over a transcript (H3)")
    run.add_argument("transcript", help="path to a speaker-tagged transcript (.txt)")
    run.add_argument("--source", default=None, help="source id (default: file stem)")
    run.add_argument("--runs-dir", default=None, help="output dir (default runs/run-<source>)")
    run.add_argument("--dsn", default=None, help="Postgres DSN for the traceability store")
    run.add_argument("--workers", type=int, default=8, help="parallel judge requests")
    run.add_argument(
        "--review",
        choices=["cli", "auto"],
        default=None,
        help="HITL reviewer: cli (interactive; default on a TTY) or auto (unattended, "
        "recorded as such). Without a TTY an explicit choice is REQUIRED.",
    )
    run.add_argument(
        "--decisions", default=None,
        help="decisions JSON file (batch review; overrides --review)",
    )
    run.set_defaults(func=_cmd_run)

    review = sub.add_parser(
        "review", help="catch-rate drill over a saved draft.json (H5, zero-LLM)"
    )
    review.add_argument("--draft", required=True, help="saved draft.json of a real run")
    review.add_argument(
        "--transcript", default=None, help="transcript path (default: golden int1.txt)"
    )
    review.add_argument("--decoys", type=int, default=3, help="seeded decoys to inject")
    review.add_argument("--seed", type=int, default=7, help="decoy RNG seed")
    review.add_argument("--decisions", default=None, help="decisions JSON file (batch)")
    review.add_argument(
        "--out", default="runs/review-drill", help="report dir (default runs/review-drill)"
    )
    review.set_defaults(func=_cmd_review)

    ev = sub.add_parser("eval", help="run an evaluation experiment (e0, e1, e2, e3, e4, gates)")
    ev.add_argument("experiment", help="experiment id (e0 | e1 | e2 | e3 | e4 | gates)")
    ev.add_argument(
        "--corpus",
        default="all",
        choices=["all", "interview", "system_desc", "wepgcomp", "maislugar"],
        help="restrict to one corpus (e0: partial exits 0; e2: wepgcomp|maislugar|all; "
        "e4: interview|wepgcomp|maislugar|all)",
    )
    ev.add_argument(
        "--arm",
        default="all",
        choices=["a", "b", "c", "d", "all"],
        help="e4: which ablation arm(s) to materialize (default all; d is reuse-only)",
    )
    ev.add_argument("--n", type=int, default=20, help="e3: sample size (default 20)")
    ev.add_argument("--seed", type=int, default=7, help="e3: sample seed (default 7)")
    ev.add_argument("--limit", type=int, default=None, help="judge only first N pairs per corpus")
    ev.add_argument(
        "--model",
        default=None,
        help="named alternate from config/models.yml (default: pinned foundation model)",
    )
    ev.add_argument(
        "--runs-dir",
        default="runs/e0",
        help="output/cache dir (default runs/e0, or runs/e0-<model> for an alternate)",
    )
    ev.add_argument(
        "--workers",
        type=int,
        default=8,
        help="parallel judge requests (default 8; use 1 for strict-sequential providers)",
    )
    ev.add_argument(
        "--no-store",
        action="store_true",
        help="e1: skip the ephemeral traceability store (recorded in run.json)",
    )
    ev.add_argument(
        "--baseline",
        default=None,
        help="e1: pinned run.json to beat (H4 gate: fidelity >= min AND coverage "
        "strictly up AND |CCI-1| strictly down)",
    )
    ev.set_defaults(func=_cmd_eval)
    return parser


def main(argv: list[str] | None = None) -> int:
    # H4 residual closed with H5: objection/resolution INFO logs are visible live.
    logging.basicConfig(level=logging.INFO)
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
