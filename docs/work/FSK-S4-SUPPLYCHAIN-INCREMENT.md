<!-- meta:doc sha=dc5431ced5cdb3b6255dff691c4bf64adf465eb3 updated=2026-06-19T02:16Z -->
# Incremento FSK-S4-SUPPLYCHAIN — Full-Stack Kotlin · seguridad de la cadena de suministro (s4)

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-19T01:59Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
> **AUTOCONTENIDO A PROPÓSITO.** Asumí que el contexto de la sesión que lo escribió murió. Otro orquestador
> construye desde acá. Si algo no está acá (o en la spec/handoff que referencia), no existe. Orden de lectura: §0.

## 0. Si llegás sin contexto, leé en este orden
1. Este doc entero (el plan + handoff de la QUINTA estación de build de la fábrica FSK).
2. `docs/work/FSK-S3-CURRENCY-INCREMENT.md` (**CERRADO**) — la estación anterior: el patrón del oráculo
   pineado + linter determinista stdlib (sin LLM) + diente negativo EMBEBIDO (probe sucio + grep,
   fail-closed) y cómo s3 compuso sobre `product_env` con diff 0. s4 cuelga de s3 (`depends_on: [s3]`) y
   reusa EXACTAMENTE esa forma (un mecanismo general por DATA, dos ejes/ecosistemas).
3. `docs/work/FULLSTACK-KOTLIN-INCREMENT.md §4–§6` (DISEÑO, **CERRADO**) — DES-13 y la línea s0–s10 / DAG.
4. `factories/full-stack-kotlin/factory.spec.yml` — el blueprint BUILDABLE. Acá vive la cap
   `seguridad_cadena_suministro` (DES-13) y la estación s4 con su check `supply_chain_gate`.
5. `factories/full-stack-kotlin/codegen/scaffold_product.py` — el codegen (DATA de la fábrica, ADR-012) que
   emite el oráculo de advisories + el SBOM + el scanner determinista + los probes negativos.

## 1. Objetivo (qué deja TERMINADO este incremento — una frase)
**s4 en `built` por proof real**: el producto Kotlin/TS gana un gate de **seguridad de la cadena de
suministro (DES-13)** donde el producto **no shippea dependencias con vulnerabilidades conocidas ni secretos
hardcodeados** — un **SBOM** (`sbom.json`, CycloneDX-lite, inventario de lo que se shippea) + un **oráculo de
advisories pineado** (`config/supply-chain.lock`: advisories `coordinate@rango-vulnerable → CVE` por
ecosistema + patrones de secretos) + un **scanner DETERMINISTA** (`tools/supply_chain_scan.py`, stdlib, **sin
red, sin LLM** — I-3) que (a) cruza el SBOM contra los advisories y (b) escanea el código autorado por
secretos. Una dep en un rango vulnerable (p.ej. `postgresql < 42.7.2` / CVE-2024-1597) o un secreto
(`AKIA…`) → **build rojo**, con un **diente negativo embebido** que exige que el scanner MUERDA fixtures
sucios cada corrida (fail-closed). Cuelga de s3; precede a s5 (auth/rutas).

## 2. Alcance EXACTO — capability, primitiva, proof_checks (de la spec, no inventar)
| capability (L1) | DES | proof_check (s4) | runs_in | requisito |
| --- | --- | --- | --- | --- |
| `seguridad_cadena_suministro` | DES-13 | `supply_chain_gate` (el scanner cruza `sbom.json` vs `config/supply-chain.lock` → exit 0 + escanea `src/main/kotlin`+`frontend/src` por secretos → exit 0; sobre `probe/security/vuln-sbom.json`+`probe/security` el scanner DEBE morder (`lodash` **y** `aws-access-key`) o decorativo→rojo) | product_env | REQ-NF-004 (re-añadir) |

- La cap arranca `status: planned`; flipea a `built` **sólo** con `proof` real recompuesto (SAFE-7) — el
  `increment_guard`/columna lo impiden, no es disciplina. Re-añadir **REQ-NF-004** (`satisfied_by: [s4]`,
  `verified_by: [supply_chain_gate]`, capability `seguridad_cadena_suministro`) — hoy DIFERIDA en la spec.
- **NO** tocar s5–s10 (cuelgan de s4; son sus propios incrementos, "capacidad por capacidad").

## 3. Decisiones de build (refinan §4–§6 del diseño; ojos propios)
1. **UN scanner general por DATA, no N herramientas externas** (la forma más fuerte de anti-overfit, como s3):
   el diseño §4 lista "OWASP dep-check / npm audit / Semgrep/CodeQL / gitleaks / SBOM". Esas son **tech
   aspiracional**; casi todas son **NO-herméticas** (dep-check baja la NVD; `npm audit` pega al registry;
   Semgrep necesita reglas/red) → romperían `ci --rederive` (clon limpio, sin red). Reduzco a la forma
   **determinista y re-derivable** que s3 ya probó: un **oráculo pineado** (DATA) + un **scanner stdlib**.
   El check es UNO (`supply_chain_gate`); cubre los DOS ejes más crispos de "supply chain": **deps
   vulnerables** (vs un snapshot de advisories) + **secretos** (regex). Ambos ortogonales a s2/s3.
2. **Determinista + hermético, no "feed vivo"** (DES-13 con I-3/SAFE-3): el oráculo es un **snapshot pineado**
   de advisories reales (OSV/NVD, con CVE id, severidad, `fixed_in`), cero red. El **feed VIVO** que REFRESCA
   ese snapshot (OSV.dev / `npm audit` / Dependabot) queda **`declared-deferred`** — EXACTAMENTE el shape del
   MCP-recall diferido de s3 (el oráculo es genuino y determinista; su alimentación viva es contenido futuro,
   no diente). Igual el **SBOM transitivo** (resolver el grafo con `gradle dependencies`/`npm ls` = red/no
   determinista): el SBOM acá es de **deps DIRECTAS/declaradas** (honesto, re-derivable), derivado de los
   MISMOS pins que `build.gradle.kts`/`package.json` (single source = las constantes → no puede driftar).
3. **Advisories REALES sobre deps REALES** (honestidad SAFE-7, no fixtures inventados): `postgresql < 42.7.2`
   (**CVE-2024-1597**, SQLi) — el producto usa **42.7.4 (FIXED, safe)** → el gate limpio pasa, y el diente
   vivo baja la versión a `42.7.1` (un CVE REAL sobre una dep que el producto REALMENTE usa). Más advisories
   de cobertura (jackson-databind CVE-2022-42003, snakeyaml CVE-2022-1471, lodash CVE-2021-23337, axios
   CVE-2023-45857) sobre coords que el producto NO usa → disponibles para el probe, sin falsos positivos.
4. **El diente de dos lados es EMBEBIDO** (doctrina `eval_gate`/`infra_up`/s2/s3): el MISMO scanner sobre
   fixtures sucios (`probe/security/vuln-sbom.json` con `lodash@4.17.20` + `postgresql@42.7.1`;
   `probe/security/leak.txt` con la **key de ejemplo canónica de AWS** `AKIAIOSFODNN7EXAMPLE`) y **exige el
   hallazgo por grep** (`lodash` deps + `aws-access-key` secretos) — **fail-closed**. Los probes viven FUERA
   de `src/` → no se compilan ni se shippean. Dir PROPIO (`probe/security`) → decoupleado de s2/s3.
5. **Secretos: NO se saltan comentarios** (a diferencia del linter de currency): una key hardcodeada en un
   comentario sigue siendo una fuga. El scanner sólo apunta a `src/main/kotlin`+`frontend/src` (no a
   `config/`/`tools/` donde viven los patrones) → cero auto-match. Los patrones son ESPECÍFICOS (AKIA…, PEM,
   ghp_…, xox…) → no matchean el código limpio.
6. **Anti-overfit**: el mecanismo es `product_env` (ya existe, C3/E1) corriendo DATA; el sustrato NO nombra
   supply-chain/CVE/secreto. `git diff src/metafactory/ + seed/` = **0** — la composición §6 del ROADMAP.
7. **El producto SHIPPEA su gate**: el SBOM + el oráculo + el scanner viven en el árbol del producto
   (`sbom.json`, `config/`, `tools/`) → son parte de su mini-columna (s10), no andamiaje de la fábrica.

## 4. Plan por fases (cada cambio de código vive en este incremento; commit por fase, trailers I-10)
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Codegen** ✅ — `scaffold_product.py` emite `sbom.json` (CycloneDX-lite de deps directas), `config/supply-chain.lock` (advisories pineados + patrones de secretos, JSON), `tools/supply_chain_scan.py` (scanner determinista stdlib: modos `deps`/`secrets`), `probe/security/vuln-sbom.json` + `probe/security/leak.txt` (fixtures negativos). idempotente (30 archivos byte-idénticos). | ✅ |
| 2 | **s4 materializada + verde e2e** ✅ — s4 en `station_sequence` (`depends_on: [s3]`) con `supply_chain_gate` (product_env, diente embebido) + cap `seguridad_cadena_suministro`→built + REQ-NF-004; `validate`+`design-review` 0; M0–M8 verde; `product-run` PASS; **RTM COMPLETE 8/8**; pin 5/5. | ✅ |
| 3 | **Pin + dientes + cierre** ✅ — `ci --rederive` **5/5 == pineado**; **diente VIVO de dos lados** (`postgresql@42.7.1` en el SBOM→rojo · `AKIA…` en el Kotlin autorado→rojo; regen→verde) + probe vaciado→`DECORATIVE` (fail-closed); `meta check` 6/6; **anti-overfit `git diff src/+seed` = 0**; dummy intacta (5/5); STATE/ROADMAP; `meta increment close`. | ✅ |

## 5. Criterio de cierre (demostrable por BLOQUEO, no narrable)
1. `meta product-run --factory full-stack-kotlin` corre s0..s4 y queda **PASS**; pin escrito (5/5).
2. `meta ci --rederive --factory full-stack-kotlin` re-deriva en clon limpio **== pineado** (re-corre el
   scanner + el toolchain entero, incl. el contenedor PG de s1 y los linters de s2/s3), **sin red**.
3. **RTM** cubre **REQ-NF-004** (`supply_chain_gate`) con artifact real (`build/product/sbom.json`).
4. **diente VIVO de dos lados**: bajar `postgresql` a `42.7.1` en `sbom.json` → `supply_chain_gate` rojo
   (CVE-2024-1597); regen → verde. Inyectar `AKIAIOSFODNN7EXAMPLE` en el Kotlin autorado → rojo; regen →
   verde. Y el **probe negativo embebido** (no-decorativo) muerde en cada corrida verde (grep `lodash` +
   `aws-access-key`).
5. **`meta check` 6/6** verde; **anti-overfit**: `git diff src/metafactory/ + seed/` = **0** (cero nombres de
   supply-chain/CVE/secreto en el sustrato — son DATA de la fábrica). dummy/full-stack/iot/ASF **intactas**.

## 6. Riesgos / notas honestas (a resolver/registrar en el build)
- **Snapshot de advisories vs feed vivo** — el oráculo NO descubre CVEs nuevos por sí solo; es un snapshot
  pineado (DETERMINISTA, re-derivable, I-3). El refresco vivo (OSV/npm audit/Dependabot) es
  `declared-deferred` (mismo shape que el MCP-recall de s3). Honesto: el gate prueba que el producto no
  shippea lo que el oráculo CONOCE; mantener el oráculo fresco es contenido futuro, no diente.
- **SBOM de deps directas** — generar el SBOM transitivo necesita resolver el grafo (red/no determinista) →
  rompería `ci --rederive`. El SBOM acá lista las deps DIRECTAS declaradas, derivadas de los mismos pins que
  `build.gradle.kts`/`package.json` (single source = las constantes → no driftan). El SBOM transitivo es
  `declared-deferred`.
- **Falsos positivos de secretos** — patrones ESPECÍFICOS (AKIA…, PEM, ghp_…, xox…) sobre `src/` solamente;
  el lado positivo (autorado limpio → exit 0) es el diente que atrapa un patrón demasiado ancho.
- **Solapamiento con s2/s3** — eje DISTINTO: s2 (calidad/-Werror), s3 (frescura de API deprecada), s4
  (seguridad de la cadena: vulns de DEPS + secretos). Ningún linter de s2/s3 marca una dep con CVE conocido
  ni una key hardcodeada → cobertura genuina nueva.
- **`build/product` se regenera** — el slot `generate` (s0) sobre-escribe `build/product`; el diente vivo se
  demuestra corriendo el scanner directo contra el árbol corrompido (exit codes reales), no via
  `product-run` (que regeneraría y borraría la corrupción) — igual que s1/s2/s3.
- s4 es codegen DETERMINISTA (sin LLM). La lógica de dominio viva por LLM es s6 (DES-8, patrón MAT-2).

## 7. Evidencia de cierre (por bloqueo, 2026-06-19 — re-derivable, no narrada)
- **M0–M8 verde** (corridos en orden, gate_guard): m00 `validate`+`design-review` 0 · m02 materializó
  `stations/s4.yml` (supply_chain_gate) · m05 RTM · **m06 `clean_runner` == pineado** (re-deriva la línea +
  el scanner de supply-chain + detekt/ESLint + el contenedor PG en clon limpio) · m07 harness · m08 product_e2e.
- **product-run PASS** — s4: `supply_chain_gate` → `FSK_SUPPLYCHAIN_OK` (gate s4 OPEN).
- **RTM COMPLETE 8/8**: REQ-F-001/002/003/004 + REQ-NF-001/002/003 (s0/s1/s2/s3) + **REQ-NF-004** ←
  `seguridad_cadena_suministro` [s4, `build/product/sbom.json`✓].
- **`ci --rederive` full-stack-kotlin 5/5 == pineado** (re-corre el scanner de supply-chain + detekt + `-Werror`
  + ESLint + npm + gradle + el contenedor PG de s1 en árbol limpio, **sin red** — el oráculo y el SBOM son DATA).
- **diente VIVO de dos lados (exit codes reales)** — el árbol generado se corrompe directo (no via
  `product-run`, que regeneraría y borraría la corrupción; igual que s1/s2/s3):
  - clean `supply_chain_gate` → `FSK_SUPPLYCHAIN_OK` exit 0.
  - **deps** — `postgresql 42.7.4 → 42.7.1` en `sbom.json` → `VULN …[CVE-2024-1597] critical` → exit 1; regen → exit 0.
  - **secretos** — `AKIAIOSFODNN7EXAMPLE` en `App.kt` autorado → `SECRET …[aws-access-key]` → exit 1; regen → exit 0.
  - **fail-closed (probe embebido)** — vaciar `probe/security/leak.txt` → el autorado pasa pero el probe NO
    muerde → `FSK_SUPPLYCHAIN_DECORATIVE_SECRETS` → exit 1 (el diente embebido es no-decorativo); regen → exit 0.
- **El gate cubre lo que ningún linter marca**: una dep con CVE conocido (`postgresql<42.7.2`) y una key
  hardcodeada (`AKIA…`) NO las marca `detekt`/`-Werror` (s2), `tsc`/`eslint-strict`, ni el linter de currency
  (s3) — el eje seguridad-de-la-cadena (DES-13) es ortogonal a calidad (DES-10) y frescura (DES-11).
- **Anti-overfit**: `git diff src/metafactory/ + seed/` = **0**. El SBOM (`sbom.json`) + el oráculo
  (`config/supply-chain.lock`) + el scanner (`supply_chain_scan.py`) + los probes viven 100% en la fábrica
  (DATA); compuso sobre `product_env` (C3/E1) sin tocar el sustrato — la composición §6 del ROADMAP, como s0–s3/MAT-7.
- **Fábricas intactas**: sólo cambió `factories/full-stack-kotlin/`; dummy `ci --rederive` 5/5 == pineado
  (spot-check); full-stack/iot/ASF inalteradas por construcción (diff de sustrato = 0).
- **Diferido honesto**: el feed VIVO de advisories (OSV.dev/`npm audit`/Dependabot) que REFRESCA el oráculo y
  el **SBOM transitivo** (resolver el grafo con `gradle dependencies`/`npm ls` = red) quedan
  `declared-deferred` — mismo shape que el MCP-recall de s3: el oráculo y el SBOM-directo son genuinos y
  deterministas, su alimentación viva es contenido futuro (no diente). Los advisories de coords que el
  producto no usa (jackson/snakeyaml/axios) quedan como deny-rules disponibles, no ejercitadas (honesto).
