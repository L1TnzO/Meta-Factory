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

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yaml

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
MIGRATED: tuple[str, ...] = ("dummy", "iot")


class CannotPlant(Exception):
    """A sabotage class found nothing to perturb in THIS target's line.

    It exists so a refusal can never be read as a catch. `rederive` returns False both when a planted
    defect was caught and when the run failed for its own reasons, so a class that simply could not
    plant — `product_broken` against a line with no `artifact_contains` rendered from a `render`, which
    is exactly `iot` — would otherwise be scored as a success it explicitly did not earn. INC-5's law,
    applied to the red side: a port may refuse to assert, but the N/A goes BESIDE the green, never
    inside it.
    """


@dataclass(frozen=True)
class Target:
    """One re-derivable unit: a factory's DEFAULT product, or a named INSTANCE (R1, ADR-015).

    v2 accepts a factory as `ci --rederive --all-products` — the default PLUS every instance under
    `products/*/product.yml`, each with its own root, its own pin and its own `.proof/`. Re-deriving
    only the factory root would leave an instance entirely unrun while the count went up, which is the
    shape of bug this repo keeps catching. `dummy` has no `products/` at all, so INC-7 could not have
    discovered this; `iot` has `fleet`, so INC-8 must.
    """

    slug: str
    product: str | None      # None == the DEFAULT product (the factory root itself)
    root: Path               # where builds write, checks run, and the pin to match lives
    chassis: Path            # where the stations and the generator live (== root for the default)

    @property
    def label(self) -> str:
        return f"{self.slug}/{self.product}" if self.product else self.slug


def targets(fdir: Path, slug: str) -> list[Target]:
    """The default product plus every named instance carrying a `product.yml` (the committed source).

    Instances are discovered, not enumerated: a factory that grows a product grows a target, and the
    count moves on its own. A factory with no `products/` yields exactly one target, so `dummy`'s
    number does not move — the port stays byte-honest about what it already proved.
    """
    found = [Target(slug, None, fdir, fdir)]
    pdir = fdir / "products"
    if pdir.is_dir():
        for p in sorted(pdir.iterdir()):
            if (p / "product.yml").is_file():
                found.append(Target(slug, p.name, p, fdir))
    return found


def materialize_instance(target: Target) -> None:
    """Derive an instance's effective `factory.spec.yml` from COMMITTED source, in the staged copy.

    The factory's generator reads its blueprint from `root/factory.spec.yml`; an instance's copy of
    that file is **gitignored** in v2 (`factories/*/products/*/factory.spec.yml`) and re-written by the
    CLI before every run. Since the staging manifest is git's tracked list, that file is legitimately
    absent here — so v3 derives it: the chassis spec with `domain.product` replaced by the instance's
    `product.yml`. That is a STRONGER claim than v2's, not a weaker one: the effective spec comes from
    two committed files rather than from whatever a working tree happens to be holding.

    `station_activation` is REFUSED, not ignored. It is a per-instance override of which stations run;
    silently dropping it would run a station this product meant to skip (or the reverse) and move a
    `proof_sha` with nobody deciding — the same failure `when` is refused for. No migrated line
    declares it today; the four `full-stack-kotlin`/`full-stack` products do, and they arrive with
    INC-9/INC-10.
    """
    blueprint = yaml.safe_load((target.root / "product.yml").read_text(encoding="utf-8")) or {}
    if isinstance(blueprint, dict) and "station_activation" in blueprint:
        raise ValueError(
            f"{target.label}: product.yml declares `station_activation`, which v3 does not implement "
            f"yet. It is REFUSED rather than ignored: ignoring it would run a station this instance "
            f"meant to skip (or skip one it meant to run) and move a proof_sha with nobody deciding")
    base = yaml.safe_load((target.chassis / "factory.spec.yml").read_text(encoding="utf-8")) or {}
    effective = copy.deepcopy(base)
    effective.setdefault("domain", {})["product"] = blueprint
    (target.root / "factory.spec.yml").write_text(
        yaml.safe_dump(effective, sort_keys=False, allow_unicode=True), encoding="utf-8")


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
    raise CannotPlant("the line declares no `artifact_contains` check whose file is produced by a "
                      "`render` build, so there is no marker to strip")


# ── the law ──────────────────────────────────────────────────────────────────────────────────
def rederive(root: Path, slug: str, *, product: str | None = None,
             sabotage: str = "") -> tuple[bool, list[str], dict]:
    """Stage, run, compare ONE target. Returns (ok, problems, counts). Never mutates the real factory.

    Raises `CannotPlant` when a sabotage class has nothing to perturb in this target — never a bool,
    because a bool would be indistinguishable from a catch.
    """
    if not root.is_absolute():
        raise ValueError(
            f"rederive needs an ABSOLUTE meta root; got {str(root)!r}. A relative root silently points "
            f"`pythonpath` at the staged copy instead of the platform, and the run then goes red for a "
            f"reason that has nothing to do with the subject — a plausible-looking false red, which is "
            f"worse than a crash (measured: it reported `s0: sha differs`)")
    with tempfile.TemporaryDirectory(prefix=f"v3-rederive-{slug}-") as tmp:
        staged = Path(tmp)
        fdir, copied = stage(root, slug, staged)
        if copied == 0:
            return False, [f"{slug}: git tracks ZERO files under factories/{slug} — a re-derivation "
                           f"from nothing is not a green (Lock #1)"], {"files": 0}

        target = next((t for t in targets(fdir, slug) if t.product == product), None)
        if target is None:
            return False, [f"{slug}: no target {product!r} (git tracks no products/{product}/product.yml)"], \
                {"files": copied}
        if target.product:
            materialize_instance(target)

        pin_path = target.root / "pinned_verdict.json"
        if not pin_path.exists():
            return False, [f"{target.label}: NOT PINNED (no committed pinned_verdict.json to compare "
                           f"against)"], {"files": copied}
        pinned = json.loads(pin_path.read_text(encoding="utf-8"))

        # The spec is the TARGET's (an instance's was just derived); the LINE is always the chassis's —
        # the station structure belongs to the factory, only the blueprint differs (R1).
        spec = load_spec(target.root / "factory.spec.yml")
        from ..host.line import load_stations   # noqa: PLC0415 — raw stations, for the red side only
        raw = load_stations(target.chassis)
        line = load_line(target.chassis, spec.subst)
        note = ""

        if sabotage == "product_broken":
            note = _strip_marker(fdir, raw)
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
            return False, [f"{target.label}: the line selected zero stations (Lock #1)"], {"files": copied}

        ctx = RunContext(root=target.root, home=root, proof_dir=target.root / ".proof",
                         pythonpath=str(root))
        build_ctx = BuildContext(root=target.root, meta_root=staged, subst=spec.subst,
                                 chassis=target.chassis)
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


def _all_targets(root: Path) -> list[tuple[str, str | None]]:
    """Every (slug, product) v3 claims to re-derive. Derived from MIGRATED and from what git tracks —
    so the red side's scope grows with the green side's, instead of being frozen at the first name."""
    pairs: list[tuple[str, str | None]] = []
    for slug in MIGRATED:
        products = [None]
        pdir = root / "factories" / slug / "products"
        if pdir.is_dir():
            products += [p.name for p in sorted(pdir.iterdir())
                         if (p / "product.yml").is_file()
                         and tracked(root, f"factories/{slug}/products/{p.name}/product.yml")]
        pairs += [(slug, p) for p in products]
    return pairs


def _run_sabotage(root: Path) -> int:
    """Every class against EVERY target, scored in THREE outcomes: caught / N-A / missed.

    Two things this fixes, both invisible while `dummy` was the only migrated factory. (1) The scope
    was `MIGRATED[0]`: adding a factory doubled P1 and left P2 exactly where it was, so the red side
    would have gone stale precisely as the green side grew. (2) A class that could not plant returned
    the same `False` as a class that caught something, so a REFUSAL was scored as a CATCH — and
    `product_broken` refuses on `iot`, which declares no `artifact_contains` fed by a `render`.

    The control matters as much as the plants: if a target's clean run does not match its pin, every
    catch on it is unattributable — the line would be red for its own reasons and the sabotage would
    be taking credit for it.
    """
    pairs = _all_targets(root)
    caught: list[str] = []
    na: list[str] = []
    missed: list[str] = []

    for slug, product in pairs:
        label = f"{slug}/{product}" if product else slug
        ok, problems, _ = rederive(root, slug, product=product)
        if not ok:
            return Verdict("v3-rederive (SABOTAGE)", 1,
                           f"{label}: the clean run does not match the pin, so no catch on it is "
                           f"attributable: {problems[0] if problems else '?'}").emit()
        for name in _CLASSES:
            try:
                planted_ok, _, _ = rederive(root, slug, product=product, sabotage=name)
            except CannotPlant:
                na.append(f"{label}:{name}")      # honest N/A — never counted as a catch
                continue
            (caught if not planted_ok else missed).append(f"{label}:{name}")

    if missed:
        return Verdict("v3-rederive (SABOTAGE)", 1,
                       f"GATE DECORATIVO: {len(caught)} caught · {len(na)} n/a · "
                       f"{len(missed)} MISSED {missed}").emit()
    # A class that is N/A on EVERY target perturbs nothing anywhere: it is decoration, not a witness.
    for name in _CLASSES:
        if all(f"{f'{s}/{p}' if p else s}:{name}" in na for s, p in pairs):
            return Verdict("v3-rederive (SABOTAGE)", 1,
                           f"GATE DECORATIVO: class {name!r} is N/A on ALL {len(pairs)} target(s) — "
                           f"a witness that can never plant is not a witness").emit()
    return Verdict("v3-rederive (SABOTAGE)", 0,
                   f"{len(caught)} planted defect(s) caught across {len(pairs)} target(s) · "
                   f"{len(na)} n/a ({', '.join(na) or 'none'}) · 0 missed",
                   counts={"targets": len(pairs), "caught": len(caught), "na": len(na)}).emit()


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

    pairs = [t for t in _all_targets(_ROOT) if t[0] in slugs]
    lines, failures, total = [], [], {"matched": 0, "pinned": 0, "targets": len(pairs)}
    for slug, product in pairs:
        label = f"{slug}/{product}" if product else slug
        ok, problems, counts = rederive(_ROOT, slug, product=product)
        total["matched"] += counts.get("matched", 0)
        total["pinned"] += counts.get("pinned", 0)
        lines.append(f"{label}: {counts.get('matched', 0)}/{counts.get('pinned', 0)} == pin")
        if not ok:
            failures.extend(f"{label}: {p}" for p in problems)

    if failures:
        return Verdict("v3-rederive", 1,
                       f"{total['matched']}/{total['pinned']} station(s) re-derived == pin across "
                       f"{len(pairs)} target(s)", counts=total, failures=tuple(failures)).emit()
    return Verdict("v3-rederive", 0,
                   f"{'; '.join(lines)} — {total['matched']}/{total['pinned']} station(s) across "
                   f"{len(pairs)} target(s), re-derived on v3 from committed source in a staged copy",
                   counts=total).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
