"""spec.cli — subprocess entrypoint the check registry (M0 checks) routes to. PORTED from v2's
`spec/cli.py` (V3-INC4, Phase 4), narrowed to the two commands this port's brief scopes: `validate`
and `design-review` — the ONLY dispatch this module carries (no new logic; `rtm-closure` and
`design-coverage` are v2 commands this port does not expose, even though the underlying functions are
ported and reachable via `v3.spec`, because they are outside this increment's declared CLI scope).

`v3.verify.kinds.resolve_check` already hardcodes `v3.spec.cli` as the executor for the `spec_validate`
and `design_review` check kinds (`v3.verify.kinds_parity` proves that mapping); this module is where
those subprocess calls land.

  validate <spec>         exit 0 iff the whole spec is well-formed (schema+substrate+rtm+grammar_v2)
  design-review <spec>    exit 0 iff the design blueprint is COMPLETE (plan+criterios) — M0's design gate (B2)

Problems print one per line as `field: reason` so the verdict bus can surface file:line."""
from __future__ import annotations

import sys

from .design import design_review
from .loader import load_spec
from .validator import validate

_CMDS = ("validate", "design-review")


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in _CMDS:
        print(f"usage: v3.spec.cli [{'|'.join(_CMDS)}] <spec.yml>", file=sys.stderr)
        return 2
    cmd, spec_path = argv[0], argv[1]
    spec = load_spec(spec_path)
    problems = validate(spec) if cmd == "validate" else design_review(spec)
    for p in problems:
        print(f"{spec_path}: {p}")
    print(f"{cmd}: {len(problems)} problem(s) for {spec.slug or spec_path}")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
