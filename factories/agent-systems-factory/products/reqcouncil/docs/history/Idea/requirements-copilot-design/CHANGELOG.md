# Changelog

All notable changes to this design specification are recorded here. This document is meant to be version-controlled; bump the version and add an entry whenever a design decision changes.

The format follows a lightweight Keep-a-Changelog convention. Use semantic-ish versioning for a design doc: MAJOR for a decision that invalidates downstream work, MINOR for a new component or expanded section, PATCH for clarifications and fixes.

## [1.0.0] — initial design baseline

### Added
- Full architecture across five planes plus two cross-cutting substrates (`00`).
- Build roadmap with staged gates (Stage 0–3) and threshold triggers (`00` §4).
- Standing decision log (`00` §5).
- Ingestion and anchoring plane: WhisperX three-stage pipeline, visual track, the immutable anchor contract (`01`).
- Retrieval plane: boundary-aware chunking, provenance payload, hybrid search, the feed/trace fork (`02`).
- Council orchestration: LangGraph internals, blackboard, eight researchers, adversarial trio, synthesizer, checkpointing, interrupts, time-travel, the Claude Agent SDK alternative (`03`).
- Attribution ladder: four layers, NLI faithfulness, ContextCite, grounded/inferred flags, reasoning capture (`04`).
- Traceability substrate: OTel GenAI conventions and attributes, Langfuse, Phoenix, W3C PROV + PAV in Neo4j, the join key, the bidirectional walk (`05`).
- Human checkpoint: review packet, worst-first ordering, cognitive forcing function, edit re-entry (`06`).
- Evaluation and quality: grounding metrics, critical-recall, ISO 29148 / 25010 rubric, DSPy optimization, CI harness (`07`).
- Caveats and limits: CoT faithfulness, omission risk, the three hard limits, multi-agent cost, automation bias, privacy, licensing (`08`).

### Notes
- Tooling versions and semantic conventions reflect the 2024–2026 state. The OpenTelemetry GenAI conventions are in "Development" status and should be re-verified on upgrade.
- Open questions deferred to implementation: the requirement-versioning schema (settle in Stage 1 before drawing the operational ERD); the concrete embedding model choice; whether to introduce a vision-language model in the visual track.

<!-- Template for the next entry:

## [x.y.z] — YYYY-MM-DD

### Changed
- ...

### Added
- ...

### Deprecated / Removed
- ...
-->
