"""v3's own ported gate CHECKS — the executor bodies `v3.verify.kinds`'s argv points at.

Each module here takes no CLI arguments and is a process whose exit code IS the evidence (I-1):
it is registered as a `Gate` in `v3.verify.suite.build_registry`, never imported for its return
value by another check (a check calls the graph/property modules it needs directly; checks do not
call each other in-process — the only cross-check import is `suite_sweep`'s read of the registry
itself, to enumerate what to re-run, not to call another check's `main`).
"""
