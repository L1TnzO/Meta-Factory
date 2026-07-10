"""Traceability store (docs/design/02 §3): schema.sql + DAO + ephemeral-PG harness.

Imported lazily by callers that need it — `psycopg` lives in the `[council]` extra,
and ingest/eval-e0 must keep working without it.
"""

from .pgtemp import PgUnavailable, binaries_available, ephemeral_postgres

__all__ = ["PgUnavailable", "binaries_available", "ephemeral_postgres"]
