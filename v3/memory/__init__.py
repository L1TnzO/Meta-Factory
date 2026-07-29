"""v3.memory — the docs-consistency law (ADR-009), ported one module at a time from the legacy
substrate. See `docs_manifest.py` for the port itself and what changed.

The legacy package's path is deliberately not spelled anywhere under `v3/`
(`v3.verify.import_boundary` rule 3): a string is how a dynamic import or a path injection hides,
so v3 describes what it ported without naming where it came from.
"""
