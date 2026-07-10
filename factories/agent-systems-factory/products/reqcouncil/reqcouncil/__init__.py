"""ReqCouncil — requirements elicitation from meeting transcripts.

Multi-agent (DeepSeek v4-pro) system: a transcript arrives as text and a council
of personas deliberates to a calibrated, evidence-traceable draft SRS. See docs/design/
for the canonical architecture. This package is built milestone by milestone
(docs/design/04); H1 = the zero-LLM ingest layer below (`reqcouncil.ingest`).
"""

__version__ = "0.1.0"  # H1: ingest + chunk-parity gate
