#!/usr/bin/env python3
"""proof_protect (PreToolUse: Write|Edit|MultiEdit|Bash) — Lock 1 of the column.
Denies every MODEL write to `.proof/` (the verdict artifacts). Only the verifier
(file-IO inside `meta station`/`verify`, not a tool call) may write there. exit 2 = deny."""
import json
import re
import sys

# WRITE vectors to `.proof/`. Inherently incomplete denylist (the real root of trust is the
# RE-DERIVATION on a clean clone, where .proof/ does not exist); it covers the known ones. Each pattern
# binds a write operator to a TARGET inside `.proof/`, NOT to `.proof/` anywhere in the command: so it
# does not fire on READ-ONLY redirections (`2>&1`, `2>/dev/null`) nor on `.proof/` mentioned as a read
# argument (`ls .proof/`, `cat .proof/x`) or as text (a commit message with `.proof/` and arrows `->`).
# Before, the loose OR made it over-zealous.
# Operand bounded with `[ \t]`/`[^ \t\n…]` (NOT `\s`/`[^|;&]`): the target must be a token on the
# SAME line, separated by spaces. So a write verb mentioned in PROSE (e.g. a multi-line commit message
# that names `cp`/`tee` and, on another line, `.proof/`) does not "reach" that `.proof/`.
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
    """True if the command tries to WRITE to `.proof/` via shell or interpreter. Reads
    (including the redirections `2>&1`/`2>/dev/null`) and mentions as argument or text do not
    count: the root of trust is re-derivation, not catching every mention of `.proof/`."""
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
            return deny(f"denied: {path} is a verdict artifact; only the verifier writes there (Lock 1)")
    if tool == "Bash":
        if bash_writes_to_proof(ti.get("command", "")):
            return deny("denied: the command WRITES to .proof/ (Lock 1; the real root is re-derivation)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
