# Memoria — Full-Stack Factory
> tipo: reference · esquema heredado ADR-021 (estable) · re-derivable, no narrado.

Esta fábrica NO confía en lo que narra: RE-DERIVA su estado de artefactos. Si esta página contradice
los artefactos, GANAN los artefactos (re-derivá; no la edites a mano).

- **RTM** — `meta rtm --factory full-stack` re-deriva, por requisito, SATISFIED/UNSATISFIED desde los
  proofs de `.proof/`: un requisito está SATISFIED iff toda estación que lo satisface tiene una gate
  recomputable-OK. Corromper un proof CAMBIA el RTM — la gate `rtm_rederive` (M5) lo exige por bloqueo.
- **Evidencia / journal** — los hechos derivan del ledger (`.proof/ledger.json`, una entrada por gate
  abierta con su `proof_sha`) y de git, no de prosa. El ledger es re-derivable; la custodia no es la
  raíz de confianza, la re-derivación en un clon limpio sí (PF-10).
- **Métricas (ADR-008)** — captura gratis (file-IO + tabla de precios × tokens, cero llamadas al
  modelo), vista con `meta metrics`. Display puro: se mide antes de forzar umbrales.
