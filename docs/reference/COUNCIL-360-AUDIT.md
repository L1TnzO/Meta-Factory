<!-- meta:doc sha=866f1b5664c5ae0bacbfb665bd856bb9d2a07dbf updated=2026-07-04T16:45Z -->
# COUNCIL-360-AUDIT — vista total: 15 sillas + topología de ejecución

> tipo: reference (estable) · creado: 2026-07-04T03:45Z · sesión S1 (Fable 5, pedido explícito del
> ingeniero: «pensar desde muchísimos ángulos, abogado del diablo y defensor»). Complementa
> `FOUNDATIONS-REAUDIT.md` (fundamentos vs conducta); esto es el barrido 360° + la auditoría de
> topología de ejecución. Los HECHOS citados se midieron en esta sesión (journal, filesystem, greps).

## §0 · Alcance declarado (resuelve la Silla 4)
**Proyecto PERSONAL** (no tesis, no comercial) — monetización/clientes FUERA de alcance (declaración
del ingeniero, 2026-07-04). Consecuencias: la Silla 15 se fortalece (el retorno ya cobrado es
aprendizaje + doctrina, sin deadline); la Silla 14 pierde su vehículo natural — la verificación
EXTERNA (ojos ajenos) no llega sola: si se quiere, será un acto deliberado (publicación/colega).

## §0.5 · Aclaración doctrinal: las TRES patas de la regeneración (2026-07-04, a raíz de la
## incomodidad del ingeniero — «la ingeniería real refactoriza de a poco, no regenera toneladas»)
La «regeneración» son tres patas de valor DISTINTO; la doctrina debe dejar de venderlas juntas:
- **(a) Re-derivación como VERIFICACIÓN** — TESIS DEMOSTRADA, valor diario: `ci --rederive == pin` en
  clon limpio ES el mecanismo de confianza («nadie leyó el código y aun así corresponde al spec»).
  Paga el aparato aunque jamás se regenere por evolución.
- **(b) N productos heredan mejoras de fábrica** — TESIS DEMOSTRADA, ejercitada decenas de veces
  (re-skin Vercel: 1 cambio de codegen → 3 productos re-derivados; un check nuevo en estación
  compartida → re-pin de todos). Es la regeneración que DE HECHO ocurre y paga.
- **(c) Regenerar como MANTENIMIENTO de un producto en producción** — **HIPÓTESIS ABIERTA, no
  tesis**: solo existe `V1__init.sql`; nunca sobrevivieron datos vivos a una regeneración. No
  afirmarla hasta que `SPEC-EVOLUTION` (§3.2) exista y mida. El refactoring incremental clásico SÍ
  existe acá, un nivel arriba: se refactoriza el CODEGEN (p. ej. MONOLITH-REFACTOR, byte-idéntico) y
  el SPEC; el código generado es artefacto de build (modelo compilador — nadie refactoriza `.class`).
  Anclaje SOTA: la industria migra artefactos de mascota a ganado (contenedores/IaC/lockfiles); apostar
  que el código de app sigue es defendible CON falsificador, no dogma. Régimen concedido: fábrica de
  UNA sola app que nunca mejora → el aparato es overkill; gana el vibe-coding.

## §1 · El consejo — 15 sillas (una línea por silla; el detalle vivió en la sesión)
1. **Historiador**: el cementerio CASE/MDA/«Software Factories» murió de 3 muertes; el LLM mata la #3
   (extender el generador ya es barato: helpdesk first-try, 0 incrementos) y ADR-011 la #2; la #1
   (spec-complexity creep) sigue VIVA y sin vigía. Falsificador: spec-LOC → código-LOC.
2. **Científico experimental**: TODAS las mediciones son autorreferenciales — **falta el grupo de
   control** (CC pelado + revisión humana, mismo spec, $ + horas + defectos). El benchmark ya puede
   arbitrarlo (~1 día, ~$20). El experimento más valioso sin correr.
3. **Arquitecto de datos**: HECHO — todo producto tiene SOLO `V1__init.sql`; no existe V2 en el
   sistema. «Regenerar > mantener» hoy vale solo SIN estado de producción. Falta `SPEC-EVOLUTION`
   (spec-diff → migración generada + gate «los datos sobreviven»).
4. **Economista**: 133 incrementos (71 meta + 62 fábrica) → ~8 productos → 0 usuarios; sin señal de
   demanda no hay gradiente de VALOR (todos los KPIs son de costo). Mitigado por §0.
5. **Estratega**: el moat (re-derivación demostrable) vale ORO en software regulado/auditable, no en
   CRUD-race-to-bottom. Con §0: la «venta» es la tesis/paper.
6. **Ing. de seguridad**: circularidad del trust-chain — el modelo revisa la columna que el modelo
   escribió; el humano-raíz aprueba lo que declara no entender del todo. SAFE-8 se invierte de facto.
   Mitigación barata: red-team con instancia fresca sin memoria; auditoría externa (la defensa de tesis).
7. **Epistemólogo**: el vocabulario («medido», «verificado») lava n=1 como certeza; «app verificada» =
   pasó gates declarados, tasa de escape de defectos DESCONOCIDA. Disciplina: «medido(n=1)» vs
   «medido(re-derivable)».
8. **Ergónomo**: el cuello de botella emergente es el MODELO MENTAL del principal (evidencia: esta
   sesión — pasos entre líneas, INDEX invisible, operatoria opaca). Falta one-pager de operador
   REGENERABLE; cada «¿cómo funciona X?» del ingeniero = señal de defecto, como una compactación.
9. **Biólogo**: linaje único, selección auto-administrada = riesgo de máximo local; nunca corrió un
   diseño competidor. El clon-limpio + benchmark hacen barato el torneo de variantes.
10. **SRE**: acople total a plataforma (ya mordió: rename Task→Agent rompió la métrica en silencio) y
    a la LISTA DE PRECIOS (ADR-021). Falta canario de plataforma (check que afirme primitivas vigentes).
11. **Contador de atención**: el ledger precia tokens, no horas-humano (262 session_starts/3 semanas);
    wall-clock por sesión al `meta outcome` es gratis (timestamps ya existen).
12. **Minimalista**: journal — 5478 station_run · 262 session_start · **15 delegation · 3 compact ·
    1 recall · 0 graph_query**. El grafo («keystone») y el harness de delegación tienen ROI realizado
    ≈ 0; la corrida S2 pendiente es su juicio. La ley de la casa (medir o borrar) aplica a las joyas.
13. **Defensor**: (a) funciona de punta a punta re-derivable en clon limpio — casi nadie puede;
    (b) gates de dos lados = contribución metodológica genuina (mata la trampa PWF); (c) el sistema NO
    se miente a sí mismo (N/A-por-medición, HONEST-STATE, F1 matizado) — la propiedad más rara;
    (d) economía de cache SOTA; (e) validación convergente (opusplan, Spec-Kit).
14. **Arqueólogo 2036**: el código no sobrevive; la DOCTRINA puede — destilarla standalone
    (paper/informe) sería además la PRIMERA verificación EXTERNA del sistema (el gate faltante de más
    alto nivel: ojos ajenos).
15. **Pedagogo**: valor ya entregado independiente de mercado — el artefacto operacionaliza más SWE
    real que la mayoría de los codebases industriales; como proyecto de Integración, sobre-entrega
    exactamente lo que las rúbricas premian: evidencia.

**Veredicto:** el sistema es un espejo perfecto de sus propios criterios — corrige con disciplina
rarísima todo lo que sus instrumentos ven; acumula en silencio lo que queda fuera (usuarios, ojos
externos, comprensión del principal, datos de producción). No es «botar y simplificar»: es **girar los
instrumentos hacia afuera**.

## §2 · Topología de ejecución (auditoría con hechos, 2026-07-04)
- **Modo operativo real = WORKSPACE desde la raíz meta** (modelo Nx/Bazel/Rails-engine — SOTA-
  consistente, pero NO declarado en ningún doc). Todo corre con cwd=raíz: columna máxima activa,
  hooks de cierre-de-turno cwd-relativos, verbos `meta`.
- **CLAUDE.md de fábrica = medio-vivo**: la plataforma adjunta CLAUDE.md anidados al LEER archivos del
  subárbol (verificar con `/context` en sesión que toque FSK — canario de 30s); la prosa cabalga a
  demanda. **El harness de fábrica (.claude/ agents·hooks·skills·settings + seed propio) está DORMIDO**:
  solo se activa lanzando `claude` DENTRO de la fábrica (hooks con rutas RELATIVAS lo delatan), cosa que
  hoy nadie hace ni funciona con los gotchas de cwd. Misma clase que el grafo: construido-pero-dormido.
- **Deriva de doctrina entre niveles (hallazgo serio)**: FSK/CLAUDE.md aún dice «el cerebro es el
  orchestrator (Opus)» — pre-ADR-021; el runbook de costos nunca se propagó a las 5 fábricas. La
  doctrina fluye solo al EMITIR y después rota; la remediación conocida (re-emit total) PISA docs de
  fábrica (gotcha). Falta: emit acotado de harness o check de paridad de doctrina.
- **Exportar una fábrica → HOY se exporta el monorepo, por diseño declarado** (el `external_ci.yml` de
  FSK: «el checkout es el repo del Meta-Factory»). Acoples: FSK importa `metafactory` en 4 módulos
  (las otras 4 fábricas: 0 imports — pero todas necesitan el engine como RUNNER de la línea). La
  historia de confianza para un colega ya es de primer nivel: `git clone` + `meta ci --rederive
  --factory X` = re-deriva el pin en SU máquina (provenance estilo SLSA/in-toto casero). Opciones si
  aparece el colega real: (1) compartir monorepo (hoy, suficiente); (2) `meta export <fábrica>` —
  bundle standalone con engine vendoreado+pineado, gate = el bundle re-deriva == pin (reusa `ci`);
  (3) engine como pip package (sobredimensionado para §0). YAGNI hasta que exista el colega.
- **«Meta raíz = lugar más seguro» → SIGUE VERDADERO, con base formal**: columna máxima (fábrica ⊊
  meta, ADR-018 `least_priv`) + cierre-de-turno solo funciona ahí + settings portables
  (`$CLAUDE_PROJECT_DIR`, sin rutas absolutas). Matices: más-enforzado ≠ más-aislado (una sesión raíz
  toca TODO; la jaula por-fábrica sería el bundle exportado); consultas triviales pagan el alquiler del
  CLAUDE.md meta → día-a-día = shell directo/Sonnet (runbook).
- **Menores**: doble residencia posible (meta + FSK CLAUDE.md adjunto) — nadie mide la SUMA (el gate
  `agent_shadow` mide solo el de fábrica); concurrencia de 2 sesiones choca en `.proof/active.json`
  (conocido); Playwright cache es máquina-local (documentado).

## §2.5 · Por qué la fábrica no corre sola (aclaración, 2026-07-04)
**Meta = la máquina-herramienta; una fábrica = la MATRIZ montada en ella; el producto = la pieza.**
Nada está «siempre activo» (no hay daemon): toda sesión se para sobre el banco de meta porque ahí viven
el MOTOR (`src/metafactory/` + CLI — quien ejecuta estaciones/gates/re-derivación/RTM) y la columna. La
fábrica es data+codegen: no corre, ES corrida. UNA máquina y no 5 copias porque: (1) un fix del motor
mejora las 5 fábricas al instante (pata b, medida); (2) el trust-chain se audita UNA vez con ojos — 5
copias = 5 superficies de auditoría del punto más caro; (3) es el modelo estándar (Gradle/Bazel/Rails-
engine) — lo único no estándar es «mismo repo» en vez de «versión declarada», elegido para evitar
releases/matriz de versiones y verificar el TODO en un clon. Export = `meta export` (bundle con motor
vendoreado+pineado, gate: el bundle re-deriva == pin) — no-construido, YAGNI hasta colega real.

## §2.6 · Auditoría valor/complejidad (pedida por el ingeniero, 2026-07-04)
Principio: cada pieza sirve a (i) SEGURIDAD de generación · (ii) ECONOMÍA medida · (iii) OPCIONALIDAD
futura. La zona (iii) es donde se acumula peso muerto → regla: **congelar-o-medir, jamás extender sin uso**.
- **Músculo (no tocar)**: seed/columna · pin clon-limpio · gramática+M0 · RTM · gates de dos lados ·
  ledger/ruteo (−82% medido) · benchmark · disciplina docs núcleo · `roles`/`least_priv`.
- **Grasa probable (veredicto c/u)**: capa de NAVEGACIÓN del grafo (0 usos; el módulo SÍ alimenta
  `quality`+`pbt`+`cost_report` → instrumentar; 30 días en 0 → archivar solo la superficie de
  navegación) · harness de delegación + plan-as-data (15 usos, ROI≈0 → EN JUICIO: la corrida S2 es su
  prueba; si S2 rinde igual sin ceremonia, quedan los gates y muere la ceremonia) · harness por-fábrica
  emitido (dormido → congelar y declarar «esqueleto de export, no operativo») · fábrica full-stack TS
  (paridad ya cubierta por Kotlin+Go+Python → candidata a regression-frozen, no borrar) · dial (medido
  pero solo builds pesados → mantener sin crecer) · observers marginales (costo ~0 → dejar).
- **Lectura global**: nada de la zona (i) sobra — la tesis «generar seguro» está bien dimensionada. El
  patrón de error histórico no fue sobre-asegurar sino construir OPCIONES antes de medir su demanda; el
  corrector (N/A-por-medición) ya existe — apuntarlo a estas cuatro.

## §3 · Cola consolidada de experimentos/acciones (ordenada por valor/costo)
1. **E1 — grupo de control**: CC pelado vs fábrica, mismo spec helpdesk, arbitrado por el benchmark
   (~1 día). Decide la historia de VALOR del sistema entero.
2. **E2 — `SPEC-EVOLUTION`**: spec v2 → migración generada + gate «los datos sobreviven». Decide
   «regenerar > mantener» para sistemas CON estado.
3. **Corrida S2 pendiente** (KPI opus-share) — además es el juicio del harness de delegación (Silla 12).
4. **One-pager de operador regenerable** (Silla 8) + `SESSION-CLASS-AS-DATA` (ya diseñado, DIFERIDO).
5. **Paridad de doctrina meta↔fábricas** (deriva ADR-021) vía emit acotado o check — NO re-emit total.
6. **Observers gratis**: horas-humano al ledger · fact `graph_query` al journal · suma de residencia
   de CLAUDE.md anidados · ratio spec-LOC/generado-LOC (muerte #1 de MDA).
7. **E3 — red-team de columna con instancia fresca** (Silla 6) · canario de plataforma (Silla 10).
8. **Declarar el modo workspace** en un doc de referencia (una sección, no maquinaria).
   ✅ 2026-07-04: `ARCHITECTURE-MAP.md §2`.
9. **La destilación standalone de la doctrina** (paper/informe de tesis) — la primera verificación
   externa (Sillas 14/15).

## §4 · Barrido de segunda pasada (Fable 5, 2026-07-04): hallazgos NUEVOS + anclas SOTA

> Segunda vuelta con ojos frescos sobre filesystem/git/journal/código (no re-audita lo que §1–§2.6 ya
> vio). Las anclas SOTA de §4.2 son conocimiento del modelo (sin web en esta sesión) — **no
> verificadas online hoy**; tratarlas como hipótesis fuertes, no como «medido».

### §4.1 · Hallazgos (H-1..H-8, orden por severidad/costo)

- **H-1 (grave, fix ≈ minutos): el «segundo verificador» NUNCA corrió como segundo actor.** HECHOS:
  no existe `.github/workflows/` (el `seed/external_ci.yml` es transporte jamás instalado); `origin`
  (github.com/L1TnzO/Meta-Factory) existe pero su último push es **2026-06-26** — 8 días y decenas de
  commits atrás. I-11 («otra máquina, otro actor, la ÚNICA capa intocable») opera de facto como
  clean-clone LOCAL del MISMO actor (`meta ci`). Doble consecuencia: (a) el eslabón más alto de la
  cadena de confianza es aspiracional — exactamente la clase de gap que I-13 obliga a declarar;
  (b) riesgo de pérdida de datos: 3 semanas de trabajo denso con backup viejo. **Fix:** `mkdir -p
  .github/workflows && cp seed/external_ci.yml .github/workflows/ && git push` — además le da a la
  Silla 6 su actor independiente gratis en cada push.
- **H-2 (matiz doctrinal): el pin ancla VEREDICTOS, no BYTES.** `proof_sha = sha256(station +
  sorted[(check, exit)])` (`seed/verifier.py`): dos árboles generados DISTINTOS que pasen los mismos
  checks producen el MISMO pin. Coherente con la filosofía (los gates SON el spec de correctitud),
  pero la prosa de `external_ci.yml` («un Meta-Factory comprometido produce un proof_sha que el runner
  no reproduce») sobre-afirma: solo si el compromiso cambia algún exit. Upgrade barato si algún día se
  quiere provenance real: agregar al proof el digest del subárbol emitido por estaciones deterministas
  (los productos ya están commiteados; s6-LLM rederiva sin red desde estado commiteado).
- **H-3 (el instrumento que le falta a la Silla 7): mutation testing = medir la tasa de escape.**
  «App verificada» = pasó gates declarados; la tasa de escape es DESCONOCIDA. El SOTA tiene el
  instrumento exacto: sembrar defectos y medir qué % matan los gates. Dos blancos: (a) el producto
  helpdesk (mutantes en dominio/handlers Kotlin → ¿los contract-tests + gates s0–s11 los matan?);
  (b) el propio motor (mutantes en `verify/checks/` → ¿`tests/` los mata?) — este segundo mide la
  fuerza del guardián mismo. Convierte el claim central en un NÚMERO y complementa E1.
- **H-4: `security_scan` = 5 regexes sobre el sustrato.** Sin entropía, sin escaneo de dependencias a
  nivel meta, sin defensa contra paquete-alucinado — el riesgo específico de deps generadas por LLM
  (FSK emite `build.gradle.kts` + `package.json`). Fix alineado a la casa (data, no maquinaria):
  ampliar `_PATTERNS` con el corpus estándar + un check en s4 «toda dep declarada existe en el
  registry y tiene edad > N» (una vez, cacheable, sin red en rederive).
- **H-5 (defecto del pipeline de docs): doble sello `sha=PENDING` en 19 docs** — incluidas decisions
  INMUTABLES (011/012/015/018). `doc_stamp` PREPENDE el sello fresco sin remover el `sha=PENDING` que
  el autor dejó → el cuerpo hasheado arrastra un pseudo-sello con fecha falsa (ruido para el triaje
  INDEX). Fix: endurecer `doc_stamp`/`split_seal` para strip de sellos residuales en cuerpo (columna →
  ojos propios); limpiar los docs NO-inmutables; decisions/ se deja o se decide explícitamente
  (des-churn vs pureza). Esta pasada limpió los que tocó (este doc).
- **H-6: `cli.py` = 1141 LOC y 24 verbos, creciendo.** El mayor archivo del motor; la regla
  multi-archivo (~800) es para archivos nuevos, pero cada verbo lo agrava. Split por-verbo cuando
  haya vehículo barato. Nota: para la **corrida S2 pendiente** el mejor vehículo sigue siendo uno de
  CONTENIDO con gate existente (p. ej. `FSK-FRONTEND-DELETE`, handoff ya escrito) — un split
  byte-idéntico es transformación determinista, no slot (lección MONOLITH-REFACTOR).
- **H-7 (límite a DECLARAR, no a construir): el grafo indexa SOLO Python.** El LOC dominante del
  sistema (Kotlin/TS generado + templates de codegen) es invisible para `quality`/`repomap`. Dado que
  §2.6 ya puso la navegación del grafo EN JUICIO (0 usos), la acción correcta es declarar el límite
  (hecho: `ARCHITECTURE-MAP.md §3`) y NO extender antes de que aparezca demanda medida.
- **H-9 (gap de instrumento, descubierto al MEDIR): el KPI opus-share no tiene medidor de primera
  clase.** `meta outcome --transcript` no imprime split por modelo; la medición S3 del vehículo iot
  (2026-07-04, ver `factories/iot/docs/LOG.md`) se hizo ad-hoc (dedup `message.id` + `graph/pricing.py`):
  $5.65/incr (−92%, VERDE) · opus-share 49.7% (ROJO vs ≤35%, de 100%→50%). Fix: ~20 líneas en
  `verify/outcome.py` reutilizando `pricing.py` — el KPI del norte VIGENTE debe ser un número del CLI,
  no un script de sesión. **Con esto, el ítem 3 de la cola §3 queda MEDIDO** (resta la variante «S2
  pura» en sesión separada).
- **H-8 (diseño para E2 ya existe afuera): `SPEC-EVOLUTION` no es investigación, es adopción.** El
  patrón estándar: esquema declarativo → diff → migración generada (clase Atlas/Prisma Migrate) +
  expand-contract para cambios breaking; el gate «los datos sobreviven» = PG efímero (infra s7 ya
  existe) + datos sembrados + migrate + asserts. Baja E2 de hipótesis abierta a incremento diseñable.

### §4.2 · Tabla de anclas SOTA por área (estado honesto)

| Área | SOTA (conocimiento del modelo) | Estado acá | Acción |
| --- | --- | --- | --- |
| Spec-driven dev | Spec-Kit · Kiro · Tessl | convergente; el diente es la diferencia | ninguna |
| Multi-agente / costo | «workflows > agents»; overhead multi-agente medido ~15× | ya alineado POR MEDICIÓN (ADR-020/021) | corrida S2 |
| Provenance / supply-chain | SLSA (builder independiente) · in-toto (subject digests) · sigstore | pin fuerte en re-derivación, sin actor independiente ni subject | **H-1** ya; H-2 si paper/colega |
| Fuerza de verificación | mutation testing (JVM: clase pitest; Python: clase mutmut) | tasa de escape desconocida | **H-3** (nuevo experimento E4) |
| Secret/dep scanning | corpus ~170 patrones + entropía · OSV · anti-slopsquatting | 5 regexes, sustrato-only | H-4 (data, barato) |
| Evolución de esquema | schema-diff→migración generada · expand-contract | solo `V1__init.sql` | **H-8 alimenta E2** |
| Indexación de código | tree-sitter · SCIP/LSIF multi-lang | grafo Python-only, navegación en juicio | declarar límite (hecho), no construir |
| Hermeticidad | Nix · devcontainers · Bazel | `tools/toolchain.sh` casero | suficiente a esta escala (YAGNI) |
| Memoria de agente | prune-first vs RAG-stacks | ya alineado (ADR-019, medido) | vigilar umbral §6 |

### §4.3 · Efecto sobre la cola §3 (ver también §5.9)

**H-1 entra PRIMERO** (arriba de E1: minutos de costo, cierra backup + segundo-actor + Silla 6 a la
vez). **H-3 entra como E4** después de E1/E2 (mismo espíritu: girar los instrumentos hacia el defecto
no visto). H-4/H-5 son mantenimiento barato de columna/pipeline; H-8 se anexa al diseño de E2. El
ítem 8 de §3 quedó ✅ (`ARCHITECTURE-MAP.md`).

## §5 · Fallas de DISEÑO (iteración 2 del loop, Fable 5, 2026-07-04)

> Pedido del ingeniero: «sentarnos honestamente frente al sistema y ver si tiene sentido». Esto NO
> re-audita ejecución (§4) ni fundamentos (FOUNDATIONS-REAUDIT): son tensiones del DISEÑO mismo —
> cosas que podrían estar mal dibujadas aunque todo lo medido esté verde. Cada una con falsificador.

- **D-1 · La recursión meta es una apuesta de AMPLITUD con N=2 dominios reales.** Todo el nivel meta
  (M0–M8, gramática factory.spec, template, layering ADR-016/018) existe para «muchas fábricas»; hoy
  hay FSK (real) + iot (real-delgada) + 3 congeladas/juguete. El costo fijo del nivel se justifica por
  (a) columna única auditada UNA vez y (b) fábricas futuras baratas — (a) está cobrado, (b) es fe.
  Falsificador: la 3ª fábrica REAL nacida end-to-end, midiendo $ y días. Si en N meses no nace, la
  pregunta honesta no es «borrar» sino si meta+FSK deberían plegarse en una capa (menos superficie).
- **D-2 · I-2 confunde «secuencia como dato» (bueno) con «contenido como strings YAML» (malo).**
  `factories/full-stack-kotlin/stations/s6.yml` embebe archivos Kotlin/Gradle ENTEROS como literales
  escapados: sin highlighting, sin lint, diffs ilegibles — los mismos costos que la regla multi-archivo
  combate en código. Diseño correcto: el YAML orquesta (secuencia+checks) y los `builds` REFERENCIAN
  archivos (`stations/templates/…`); migración mecánica byte-idéntica posible (lección
  MONOLITH-REFACTOR). Barato y quirúrgico por estación.
- **D-3 · El vocabulario de checks está INVERTIDO (medido hoy):** el kind genérico `product_env` hace
  72 de ~130 usos (+`infra_up` 26); la mayoría de los ~32 kinds aparece UNA vez (línea meta/dummy) o
  solo en `meta check`. No es podar (los one-shot sostienen la línea meta): es CONGELAR el vocabulario
  con la misma regla que roles (ADR-020): kind nuevo = acto deliberado, y la vara es «¿no alcanza
  `product_env` + un script?».
- **D-4 · El loop de auto-mejora vía slots cerró UNA vez (n=1).** La promesa central «gap de spec →
  slot escribe la extensión del codegen → gates verifican» ocurrió en IOT-S1 (2 spawns, verde, $5.65);
  su contraejemplo previo son los 17 ADOPTs a mano de Snipe-IT. Si los próximos ejes NO siguen el
  patrón iot, el harness de delegación es ceremonia (Silla 12); si lo siguen, es LA tesis operando.
  Regla propuesta (barata, prosa): todo eje nuevo de fábrica nace como slot S2 salvo justificación
  escrita en su work-doc.
- **D-5 · El gobierno no tiene falsificador de su propio creep.** CLAUDE.md meta = 99 líneas (bajo
  presupuesto) pero la DENSIDAD normativa por línea crece (el runbook entero vive inline) y las reglas
  solo se acumulan — nunca se retiró una. Es la muerte #1 de MDA (spec-complexity) aplicada al
  gobierno. Observer gratis: conteo de bullets normativos de CLAUDE.md por commit (git ya lo tiene).
- **D-6 · ¿Los dólares del ledger son REALES? — RESPONDIDA (ingeniero, 2026-07-04): SUSCRIPCIÓN, no
  API.** Consecuencias en §6.0: todos los KPIs-$ pasan a shadow-prices (proxy de cupo/consumo, no
  ahorro contante); el ledger se conserva re-etiquetado; horas-humano y cupo se vuelven la
  restricción vinculante.
- **D-7 · El lenguaje de seguridad sobre-afirma el threat model.** «Intocable», trusting-trust,
  SLSA-casero — pero pin, checks y estaciones son EDITABLES por el modelo dentro de un incremento (así
  se trabaja, por diseño). La defensa real: columna anti-autoengaño + git-diff + ojos del ingeniero.
  El threat model honesto es DERIVA/AUTOENGAÑO, no adversario activo. Falta una sección THREAT-MODEL
  (qué se defiende, qué explícitamente NO) que desinfle el vocabulario prestado (Silla 7 aplicada al
  diseño).
- **D-8 · Endogeneidad del benchmark.** El target sweet-spot está escrito en la MISMA gramática que el
  sistema genera: mide cobertura de la gramática propia, no capacidad. Falsificador barato: UNA spec
  escrita por un tercero (o pública) traducida a `product.yml` en sesión S2 — si el costo explota, el
  claim de generalidad se recorta otra vez (como pasó con Snipe-IT). Se puede fusionar con E1.

### §5.9 · Qué se decide con esto (mínimo accionable)
1. **D-6 se responde HOY** (1 línea del ingeniero: ¿API o suscripción?) — re-etiqueta todos los KPIs $.
2. **D-4 se adopta como regla de prosa** en el próximo eje de fábrica (nace como slot o justifica).
3. **D-2 es el incremento mecánico candidato** cuando haya vehículo S2 (byte-idéntico, riesgo ~0).
4. D-1/D-8 no piden trabajo: piden FECHA/vara (3ª fábrica; spec ajena) para que la apuesta tenga juez.

## §6 · Síntesis final (iteración 3, Fable 5, 2026-07-04): los caminos simulados y la arquitectura recomendada

### §6.0 · D-6 respondida: SUSCRIPCIÓN → re-etiquetado de toda la economía
1. **Los KPIs-$ son SHADOW-PRICES**: «$5.65» y «−92%» miden consumo relativo, no ahorro contante. El
   ledger NO se tira — la tabla de precios API es el peso correcto del CUPO relativo (Opus consume
   cupo ~5× Sonnet por token): mismo contador, otra unidad. Disciplina de rotulado: «medido($shadow)».
2. **La restricción vinculante real = CUPO (ventanas de uso) + HORAS-HUMANO.** La Silla 11 queda
   PROMOVIDA: wall-clock por sesión en `meta outcome` pasa de «gratis, algún día» a observer #1
   pendiente (los timestamps ya existen; es una resta).
3. **Lo que NO cambia**: el ruteo S1/S2/S3, kill-don't-idle y el dial optimizan cupo exactamente igual
   que $; la línea 0-modelo sigue siendo la palanca #1 (cupo 0). La doctrina de cache pierde urgencia
   de dólar y conserva la de cupo/latencia.

### §6.1 · El vigía de la muerte #1 de MDA — instalado CON DATOS (medido 2026-07-04)
spec-LOC → generado-LOC: **helpdesk 82 → 37.8k (1:461) · assets 57 → 53.2k (1:932) · snipeit 411 →
41.5k (1:100)**. Lectura honesta: hoy NO hay spec-complexity creep (el colapso MDA histórico es
ratio→~1:1); el ratio degrada con la complejidad del producto pero Snipe-IT —el techo— sigue en 1:100.
Juicio de la gramática `product.yml`: BUENA — declarativa, vocabulario cerrado, comentable, la
activación de estaciones es data; no es el eslabón débil. Umbral de alarma propuesto: un producto
futuro bajo ~1:50 = la muerte #1 tocando la puerta. Re-derivable con `wc` (observer formal: opcional).

### §6.2 · Los tres caminos, simulados contra la evidencia §1–§5
| Camino | Qué es | A favor | En contra | Veredicto |
| --- | --- | --- | --- | --- |
| **A · statu quo + cirugía** | mantener todo activo; ejecutar H/D | costo mínimo, opcionalidad | no responde D-1; la superficie sigue cobrando alquiler cognitivo (Silla 8 = el cuello MEDIDO) | insuficiente solo |
| **B · consolidación** | declarar el sistema vivo = meta+FSK+iot; congelar dummy (fixture del pin) + full-stack-TS + ASF como regression-frozen; vocabularios CERRADOS (D-3 como roles); navegación-grafo bajo la regla 30-días-en-0 (§2.6) | ataca el cuello real (modelo mental); nada de lo congelado se borra (el pin lo mantiene verificable gratis); coherente con §0 (retorno = aprendizaje+doctrina, ya cobrado) | renuncia narrativa a «N fábricas» hasta que C tenga fecha | **BASE recomendada** |
| **C · expansión** | 3ª fábrica REAL end-to-end bajo patrón iot (S1 diseña, S2 ejecuta), midiendo cupo y días | es EL juez de D-1; vindicaría el nivel meta | semanas de trabajo; sin dominio con uso propio real es teatro | **opción CON FECHA**, solo si aparece dominio real |

### §6.3 · Veredicto: la arquitectura óptima
**La topología actual ES la óptima conocida para el régimen declarado** (§0 personal · $/feature
verificada sin humano leyendo el código): ninguna alternativa simulada la domina — plegar niveles (B
extremo) destruiría la columna-única y el pin multi-fábrica que SÍ están cobrados; expandir sin
demanda (C sin fecha) repite el patrón de error histórico (§2.6: construir opciones antes de medir
demanda). El óptimo no es otra topología; es **la misma con la mitad de la superficie activa y jueces
instalados**: (a) camino B; (b) contenido-como-archivos (D-2); (c) los TRES jueces — E1 control-group
fusionado con D-8 (spec ajena), E4 mutation/escape-rate (H-3), horas-humano (§6.0.2); (d) patrón iot
como única vía de extensión (D-4); (e) H-1 ya (el eslabón aspiracional más barato de volver real).

**Sobre observabilidad (la pregunta directa): NO falta más telemetría para diseñar** — el diseño ya
se decidió por medición varias veces (INC-5/6 N/A, índice semántico descartado, dial medido). Lo que
falta son instrumentos de JUICIO EXTERNO, tres y baratos: tasa de escape (E4), grupo de control
(E1+D-8) y horas-humano. La comunidad ya pagó las ideas necesarias (mutation testing, schema-diff→
migración, actor-independiente de CI, plan-execute por sesión) — mapeadas con su estado en §4.2;
ninguna requiere investigación, solo adopción con dientes.

### §6.4 · Orden de ejecución recomendado (fusiona §3 + §4.3 + §5.9)
1. **H-1** (minutos): instalar workflow + push — segundo actor + backup.
2. **Horas-humano al outcome + rotulado shadow-price** (gratis, §6.0).
3. **D-2** contenido-como-archivos (mecánico, byte-idéntico, vehículo S2).
4. **E1+D-8 fusionados** (~1 día): spec AJENA, CC-pelado vs fábrica, arbitrado por benchmark.
5. **E4** mutation sobre helpdesk + `verify/checks/` (H-3) — el número de la Silla 7.
6. **C solo con dominio real y fecha**; mientras tanto, B es la casa.

### §6.5 · El repo resultante (proyección: qué queda al terminar §6.4, pedida por el ingeniero)
Principio rector: acá NO se borra — se **congela con pin** (la re-derivación mantiene verificable lo
congelado a costo ~0); borrar es solo para RUIDO. Por eso ~90% del repo queda byte-idéntico; lo que
cambia es su ESTADO y su forma:

| Zona | Estado resultante |
| --- | --- |
| `seed/` · `.claude/` · `template/` · `tests/` | **VIVOS sin cambios** (la columna; H-5 endurece `doc_stamp`) |
| `src/metafactory/` | **VIVO**, 3 deltas: `verify/outcome.py` +horas-humano/split-modelo (§6.0/H-9) · vocabulario de checks CONGELADO (D-3, regla tipo-roles) · superficie de navegación del grafo bajo regla 30-días-en-0 → archivable (internals quedan: alimentan quality/pbt/billing) |
| `.github/workflows/` | **NUEVO** (H-1): el transporte del seed por fin instalado; Actions re-deriva en cada push |
| `stations/` (meta y fábricas) | **cambia de FORMA** (D-2): YAML = orquestación (secuencia+checks); el contenido embebido migra a archivos reales `stations/templates/*.kt/.kts/.ts` — salida byte-idéntica |
| `factories/full-stack-kotlin/` · `factories/iot/` | **VIVAS** — el sistema operativo real; extensión SOLO por patrón iot (D-4) |
| `factories/dummy/` | **VIVA como FIXTURE** — es el cuerpo de prueba de la línea meta (el pin que el CI re-deriva); no es deuda |
| `factories/agent-systems-factory/` · `factories/full-stack/` | **REGRESSION-FROZEN declarado** (STATE de cada una lo dice): pin verde gratis en `ci --rederive`, cero incrementos nuevos; descongelar = acto deliberado |
| `benchmarks/` · `scenarios/` · `specs/` | **VIVOS** + crece: la spec AJENA de E1+D-8 y su veredicto |
| `docs/decisions/` (001–021) · `LOG` · `work/` cerrados | **INMUTABLES, quedan todos** — son la evidencia; jamás se podan |
| `docs/reference/` | **VIVO y consolidado**: COUNCIL+MAP = casa de auditoría; los históricos (REGEN-AUDIT, MAT-6, F1) quedan como evidencia fechada; +THREAT-MODEL honesto (D-7, una sección) |
| Evidencia nueva | tasa de escape (E4) + veredicto control-group (E1+D-8) + horas-humano en outcome — los tres JUECES por fin en el árbol |

Día-a-día resultante: el ingeniero toca meta+FSK+iot; los productos salen por la línea 0-modelo; los
ejes nuevos nacen como slots S2; la auditoría vive en UN doc; y todo lo demás sigue verificable sin
costo de atención — que era el cuello real (Silla 8).
