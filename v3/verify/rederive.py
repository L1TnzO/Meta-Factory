#!/usr/bin/env python3
"""rederive — does a FACTORY, run end to end on v3, reproduce its committed pin?

    python3 -m v3.verify.rederive                        # every migrated factory
    python3 -m v3.verify.rederive dummy                  # one of them
    V3_REDERIVE_SABOTAGE=1 python3 -m v3.verify.rederive # the red side; must ALSO exit 0

This is the first gate in the rebuild whose SUBJECT is a product rather than v3 itself. Everything
before it verified the platform against an oracle: the kernel reproduces a sha, the registry refuses
a toothless gate, the census accounts for v2's surface. Here v3 loads a factory's stations, applies
its builds, runs its checks as real processes, computes each `proof_sha` and compares the set against
`pinned_verdict.json`. P1 of §11.2, for one factory at a time.

THE COPY, AND WHY IT IS NOT v2's WIPE. v2 re-derives by `rmtree`-ing the factory's `.proof/` and
`build/` in place and rebuilding there. That works and costs two things it does not have to: it
destroys the evidence in order to check the evidence (a run that dies halfway leaves nothing to
compare against), and it clears exactly two directories, so any residue a previous run left elsewhere
is still present and can be holding the green up. Here the subject is staged into a temporary tree
from **git's tracked file list**, which makes the claim the stronger one: re-derived from COMMITTED
SOURCE, not from the working tree minus two directories. If something untracked turns out to be
load-bearing, this goes red — and that is a finding, not a defect of the port.

WHAT IS COPIED AND WHAT IS NOT — the boundary this gate exists to keep. The FACTORY is copied: its
stations, its sources, its spec, its pin. **v3 is not.** The platform stays where it lives and reaches
the staged subject through `PYTHONPATH`. Copying the platform alongside the subject would mean
re-deriving against whatever version of v3 happened to land in that copy, which is a different (and
much weaker) claim than the one on the label.

THE LIMIT, STATED RATHER THAN DISCOVERED (§11.2 ⚠️). `proof_sha` hashes check NAMES and EXIT CODES —
not the command, not the implementation, not the output. So `5/5 == pin` is satisfied by any port
whose checks keep their names and still exit 0, INCLUDING one whose executors were hollowed out. P1
alone would accept exactly the rebuild this project is trying not to build. That is why the red side
below breaks the PRODUCT rather than breaking v3: the only way to prove the checks still check is to
give them something that must make them fail.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from ..host.builds import BuildContext, apply_builds
from ..host.line import load_line
from ..host.runner import RunContext, run_line
from ..kernel.pin import pin_matches
from ..kernel.report import Verdict
from ..spec.loader import load_spec

_V3 = Path(__file__).resolve().parent.parent
_ROOT = _V3.parent

#: The factories v3 can RUN, as a closed constant rather than a discovery. INC-7 migrates `dummy`;
#: INC-8 adds `iot`, INC-9 `full-stack-kotlin`, INC-10 the two frozen ones. Keeping it a literal is
#: what makes the count add up: a factory believed migrated but absent here is simply never run, and
#: that is the shape of bug this repo keeps catching. Adding a name means running its line.
MIGRATED: tuple[str, ...] = ("dummy",)


def tracked(root: Path, rel: str) -> list[str]:
    """The repo-relative paths git TRACKS under `rel`. The staging manifest, and the reason the
    claim is "from committed source" rather than "from whatever is lying around"."""
    out = subprocess.run(["git", "ls-files", "--", rel], cwd=root, capture_output=True, text=True)
    return [line for line in out.stdout.splitlines() if line.strip()]


def stage(root: Path, slug: str, dest: Path) -> tuple[Path, int]:
    """Copy the factory's tracked files into `dest`, preserving repo-relative paths.

    Paths are preserved because a station's `render` names its source relative to the META root
    (`factories/<slug>/domain/…`); flattening the copy would make those sources unreachable and the
    line would fail for a reason that has nothing to do with what is being measured.
    """
    files = tracked(root, f"factories/{slug}")
    for rel in files:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, target)
    return dest / "factories" / slug, len(files)


# ── the sabotage: break the PRODUCT, never the platform ──────────────────────────────────────
def _strip_marker(fdir: Path, raw_stations: list) -> str:
    """Remove the first declared `artifact_contains` marker from the SOURCE that renders its file.

    Derived end to end from station DATA: find the check, find the `render` whose `dest` is the file
    that check reads, and strip the marker from that render's `src`. Nothing about `dummy` is spelled
    here. Returns a description, or "" when the line declares no such pair — in which case the caller
    must refuse rather than report a catch it did not earn.
    """
    for station in raw_stations:
        for check in station.get("checks") or ():
            if check.get("kind") != "artifact_contains":
                continue
            wanted, marker = str(check.get("file", "")), str(check.get("marker", ""))
            for other in raw_stations:
                for build in other.get("builds") or ():
                    if build.get("action") != "render" or str(build.get("dest")) != wanted:
                        continue
                    src = fdir.parent.parent / str(build["src"])
                    text = src.read_text(encoding="utf-8")
                    if marker not in text:
                        continue
                    src.write_text(text.replace(marker, "REDACTED_BY_SABOTAGE"), encoding="utf-8")
                    return f"stripped {marker!r} from {build['src']} (the source of {wanted})"
    return ""


# ── the law ──────────────────────────────────────────────────────────────────────────────────
def rederive(root: Path, slug: str, *, sabotage: str = "") -> tuple[bool, list[str], dict]:
    """Stage, run, compare. Returns (ok, problems, counts). Never mutates the real factory."""
    with tempfile.TemporaryDirectory(prefix=f"v3-rederive-{slug}-") as tmp:
        staged = Path(tmp)
        fdir, copied = stage(root, slug, staged)
        if copied == 0:
            return False, [f"{slug}: git tracks ZERO files under factories/{slug} — a re-derivation "
                           f"from nothing is not a green (Lock #1)"], {"files": 0}

        pin_path = fdir / "pinned_verdict.json"
        if not pin_path.exists():
            return False, [f"{slug}: NOT PINNED (no committed pinned_verdict.json to compare against)"], \
                {"files": copied}
        pinned = json.loads(pin_path.read_text(encoding="utf-8"))

        spec = load_spec(fdir / "factory.spec.yml")
        from ..host.line import load_stations   # noqa: PLC0415 — raw stations, for the red side only
        raw = load_stations(fdir)
        line = load_line(fdir, spec.subst)
        note = ""

        if sabotage == "product_broken":
            note = _strip_marker(fdir, raw)
            if not note:
                return False, [f"{slug}: the red side found no artifact_contains marker rendered from "
                               f"a source, so it could not plant anything — refusing to report a "
                               f"catch it did not earn"], {"files": copied}
        elif sabotage == "station_vanished":
            line, note = line[:-1], f"dropped {line[-1]['id']} from the line"
        elif sabotage == "check_renamed":
            line = [dict(s) for s in line]
            first = next(s for s in line if s.get("checks"))
            first["checks"] = [{**c} for c in first["checks"]]
            was = first["checks"][0]["name"]
            first["checks"][0]["name"] = was + "_renamed"
            note = f"renamed {first['id']}/{was} without touching what it runs"
        elif sabotage == "empty_line":
            line, note = [], "selected zero stations"

        if not line and sabotage != "empty_line":
            return False, [f"{slug}: the line selected zero stations (Lock #1)"], {"files": copied}

        ctx = RunContext(root=fdir, home=root, proof_dir=fdir / ".proof", pythonpath=str(root))
        build_ctx = BuildContext(root=fdir, meta_root=staged, subst=spec.subst)
        ctx.builder = lambda station, _ctx: apply_builds(station, build_ctx)

        outcomes = run_line(line, ctx)
        rederived = {o.station: o.proof_sha for o in outcomes if o.proof_sha}
        ok, problems = pin_matches(pinned, rederived)
        red = [o.station for o in outcomes if o.ran and not o.passed]
        counts = {"files": copied, "pinned": len(pinned), "rederived": len(rederived),
                  "matched": len(pinned) - len(problems), "red_stations": len(red)}
        if note:
            problems = [f"sabotage: {note}", *problems]
        return ok, problems, counts


_CLASSES = ("product_broken", "station_vanished", "check_renamed", "empty_line")
_SLUG = MIGRATED[0]


def _run_sabotage(root: Path) -> int:
    """Four planted defects, each naming the non-empty value it perturbs.

    The control matters as much as the plants: if the clean run does NOT match the pin, every catch
    below is unattributable — the line would be red for its own reasons and the sabotage would be
    taking credit for it.
    """
    ok, problems, _ = rederive(root, _SLUG)
    if not ok:
        return Verdict("v3-rederive (SABOTAGE)", 1,
                       f"the clean run does not match the pin, so no catch is attributable: "
                       f"{problems[0] if problems else '?'}").emit()

    caught = []
    for name in _CLASSES:
        planted_ok, _, _ = rederive(root, _SLUG, sabotage=name)
        if not planted_ok:
            caught.append(name)

    if len(caught) == len(_CLASSES):
        return Verdict("v3-rederive (SABOTAGE)", 0,
                       f"{len(caught)}/{len(_CLASSES)} planted defect(s) caught "
                       f"({', '.join(caught)})").emit()
    missed = [c for c in _CLASSES if c not in caught]
    return Verdict("v3-rederive (SABOTAGE)", 1,
                   f"GATE DECORATIVO: {len(caught)}/{len(_CLASSES)} caught "
                   f"({', '.join(caught) or 'none'}) — missed {missed}").emit()


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        return Verdict("v3-rederive", 2, f"takes at most one factory slug; got {argv!r}").emit()
    if os.environ.get("V3_REDERIVE_SABOTAGE") == "1":
        return _run_sabotage(_ROOT)

    slugs = (argv[0],) if argv else MIGRATED
    unknown = [s for s in slugs if s not in MIGRATED]
    if unknown:
        return Verdict("v3-rederive", 2,
                       f"{unknown} is not in MIGRATED {list(MIGRATED)}: a factory v3 has not migrated "
                       f"cannot be re-derived by it, and pretending otherwise is how a count stops "
                       f"adding up").emit()

    lines, failures, total = [], [], {"matched": 0, "pinned": 0}
    for slug in slugs:
        ok, problems, counts = rederive(_ROOT, slug)
        total["matched"] += counts.get("matched", 0)
        total["pinned"] += counts.get("pinned", 0)
        lines.append(f"{slug}: {counts.get('matched', 0)}/{counts.get('pinned', 0)} == pin "
                     f"({counts.get('files', 0)} tracked file(s))")
        if not ok:
            failures.extend(f"{slug}: {p}" for p in problems)

    if failures:
        return Verdict("v3-rederive", 1,
                       f"{total['matched']}/{total['pinned']} station(s) re-derived == pin across "
                       f"{len(slugs)} factory/factories", counts=total,
                       failures=tuple(failures)).emit()
    return Verdict("v3-rederive", 0,
                   f"{'; '.join(lines)} — re-derived on v3 from committed source, in a staged copy",
                   counts=total).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
