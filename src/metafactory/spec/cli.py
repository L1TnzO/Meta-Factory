"""spec.cli — subprocess entrypoints used by the check registry (M0 checks).
  validate <spec>       exit 0 iff the whole spec is well-formed (schema+substrate+rtm)
  rtm-closure <spec>    exit 0 iff every requirement maps to an active station
Problems print one per line as `field: reason` so the verdict bus can surface file:line."""
from __future__ import annotations

import sys

from .loader import load_spec
from .validator import rtm_closure, validate


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in ("validate", "rtm-closure"):
        print("usage: spec.cli [validate|rtm-closure] <spec.yml>", file=sys.stderr)
        return 2
    cmd, spec_path = argv[0], argv[1]
    spec = load_spec(spec_path)
    problems = validate(spec) if cmd == "validate" else rtm_closure(spec)
    for p in problems:
        print(f"{spec_path}: {p}")
    print(f"{cmd}: {len(problems)} problem(s) for {spec.slug or spec_path}")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
