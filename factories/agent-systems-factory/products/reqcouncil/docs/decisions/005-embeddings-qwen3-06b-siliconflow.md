<!-- meta:doc sha=ab76928945915e8e16034670f876f3a989090e37 updated=2026-07-10T23:29Z -->
# 005 — Embeddings de dedup: Qwen3-Embedding-0.6B servido por SiliconFlow (2026-07-05)

**Decisión.** El embedder pluggable del diseño (design/04 §1: «bge/qwen-class sentence
embedder, pinned by name+version in config») se pinnea a **`Qwen/Qwen3-Embedding-0.6B`
@ SiliconFlow** (`config/models.yml` sección `embeddings:`). Uso en H3: dedup semántico del
Moderator (coseno > τ_dup ⇒ merge de candidatos). Uso futuro: blocking top-K (H4/H6).

**Motivo (regla del repo: cambiar `config/` exige motivo escrito).**
1. **Precio, la restricción dominante del proyecto (decisión 004)**: es el embedder más
   chico/barato del proveedor YA contratado — cero proveedores nuevos, misma key, mismos
   límites (500 RPM / 2M TPM).
2. **Medido antes de adoptar (spike vivo 2026-07-05, 3 frases, 46 tokens)**: dim 1024;
   par casi-duplicado cos = **0.9305** vs pares distintos cos = **0.4513 / 0.4617** —
   separación amplia para un umbral de dedup. τ_dup inicial = **0.88** (DATA en
   `config/council.yml`, revisable con motivo escrito si E1 muestra over/under-merge).
3. bge-m3 (el default sugerido por el diseño) NO está en el catálogo vivo de SiliconFlow
   (`/v1/models` 2026-07-05: solo la familia Qwen3-Embedding 0.6B/4B/8B) — se pinnea lo
   que existe donde ya pagamos.

**Trigger de reversa.** Si E1/E4 muestran dedup roto atribuible al embedder (merges
espurios con τ calibrado, o duplicados obvios con cos < 0.8), subir a
`Qwen3-Embedding-4B/8B` — mismo endpoint, un cambio de config.
