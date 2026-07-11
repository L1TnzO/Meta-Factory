#!/usr/bin/env python3
"""proof_protect (inherited) — Lock 1 of the agent-systems-factory factory's column. Denies every
model write to `.proof/` (the verdicts). Self-contained (zero deps). exit 2 = deny."""
import json
import re
import sys

# WRITE vectors to `.proof/` (incomplete denylist; the real root is re-derivation on a clean
# clone). Each pattern binds a write operator to a TARGET inside `.proof/`, so it does NOT fire on
# read-only redirections (`2>&1`, `2>/dev/null`) nor on `.proof/` as a read argument or text (a
# message with `.proof/` and arrows `->`).
# Operand bounded to a token on the SAME line ([ \t]/[^ \t\n…], not \s/[^|;&]): a write verb mentioned
# in multi-line prose does not "reach" a `.proof/` on another line (over-block of the 1st attempt).
_PROOF_WRITE = re.compile(
    r"""(?x)
    (?: >>? [ \t]* ['"]? [^\s'"|&;<>]* \.proof/ )                       # redirection: > .proof/x , >> dir/.proof/x
  | (?: \b(?:tee|cp|mv|install|truncate|dd)\b                           # verbs that write a file-arg...
        (?: [ \t]+ [^ \t\n|;&]+ )*? [ \t]+ ['"]? [^ \t\n'"|;&]* \.proof/ )   # ...a target-arg in .proof/
  | (?: \bsed [ \t]+ -i\S* (?: [ \t]+ [^ \t\n|;&]+ )*? [ \t]+ ['"]? [^ \t\n'"|;&]* \.proof/ )  # sed -i ... .proof/x
  | (?: \bln  [ \t]+ -s\S* (?: [ \t]+ [^ \t\n|;&]+ )*? [ \t]+ ['"]? [^ \t\n'"|;&]* \.proof/ )  # ln -s ... .proof/x
  | (?: \bopen \s* \( \s* ['"] [^'"]* \.proof/ )                        # open('.proof/..', …)  (interpreter)
    """
)


def bash_writes_to_proof(cmd: str) -> bool:
    """True if the command tries to WRITE to `.proof/` (not reads nor mentions)."""
    return bool(_PROOF_WRITE.search(cmd))


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    tool = data.get("tool_name", "")
    ti = data.get("tool_input", {}) or {}

    def deny(msg: str) -> int:
        print(f"proof_protect: {msg}", file=sys.stderr)
        return 2

    if tool in ("Write", "Edit", "MultiEdit"):
        path = (ti.get("file_path") or ti.get("path") or "").replace("\\", "/")
        if "/.proof/" in path or path.endswith("/.proof") or path.startswith(".proof/"):
            return deny(f"denied: {path} is a verdict; only the verifier writes there (Lock 1)")
    if tool == "Bash":
        if bash_writes_to_proof(ti.get("command", "")):
            return deny("denied: the command WRITES to .proof/ (Lock 1; the real root is re-derivation)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
