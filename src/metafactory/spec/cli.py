"""spec.cli — subprocess entrypoints used by the check registry (M0 checks) and the design skill.
  validate <spec>         exit 0 iff the whole spec is well-formed (schema+substrate+rtm+grammar_v2)
  rtm-closure <spec>      exit 0 iff every requirement maps to an active station
  design-coverage <spec>  exit 0 iff the design declares a tech for every required primitive (B1, design-time)
Problems print one per line as `field: reason` so the verdict bus can surface file:line."""
from __future__ import annotations

import sys

from .design import design_coverage
from .loader import load_spec
from .validator import rtm_closure, validate

_CMDS = ("validate", "rtm-closure", "design-coverage")


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in _CMDS:
        print(f"usage: spec.cli [{'|'.join(_CMDS)}] <spec.yml>", file=sys.stderr)
        return 2
    cmd, spec_path = argv[0], argv[1]
    spec = load_spec(spec_path)
    if cmd == "validate":
        problems = validate(spec)
    elif cmd == "rtm-closure":
        problems = rtm_closure(spec)
    else:
        problems = design_coverage(spec)
    for p in problems:
        print(f"{spec_path}: {p}")
    print(f"{cmd}: {len(problems)} problem(s) for {spec.slug or spec_path}")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
