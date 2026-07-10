"""Evaluation harness (docs/design/03): golden loaders, metrics, and the E0..E4 runners.

H2 ships E0 (judge calibration). Runners write to runs/ (gitignored); pinned evidence
lives under runs/pinned/ (tracked — the `no_regression` gate needs a previous green run).
"""
