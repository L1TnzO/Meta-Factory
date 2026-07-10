"""Council package (docs/design/01): personas, Round-0 roles, pipeline.

LangGraph/psycopg live in the [council] extra — import this package lazily from
surfaces (CLI) that must keep working without it.
"""

from .schema import Candidate, CandidateParseError, parse_candidates

__all__ = ["Candidate", "CandidateParseError", "parse_candidates"]
