# ReqCouncil — pin de provenance del producto adoptado

> tipo: reference (estable, per-producto) · adoptado: 2026-07-10 (ADR-025, incremento REQCOUNCIL-ADOPT)
> A diferencia de `docs/reference/ASF-PROVENANCE.md` (que PINEA identidad sin copiar bytes, porque ASF
> es una referencia archival de cosecha), acá el árbol se **COPIA físicamente**: `eval_floor` (la
> estación `s12`) necesita el código + `runs/pinned/` + `config/thresholds.yml` presentes en disco para
> re-verificar el piso; un pin sin bytes no alcanza para un producto que se re-corre (ADR-025 §4/§5).

## El pin

| Campo | Valor |
| --- | --- |
| commit | `89ad45b548c3e3f9464dc4feb081ea812cead5ac` |
| tree | `b6d15653623a8b6fd98c8c15e309fb2ced45a69b` |
| branch upstream | `master` |
| HEAD msg | `build(informe): pipeline markdown→PDF real (pandoc+typst, formato UFRO Anexo A)` |
| ubicación upstream | `~/University/Integración/APP/dataset_agent_re` (repo git HERMANO, FUERA del Meta-Factory) |
| sucio al pinear | sólo `docs/informe/*` (capítulos del informe UFRO + PDF regenerado) — post-pin, NO es material del núcleo evaluable (código/config/tests/runs/datasets), no afecta a `eval gates` |
| tamaño copiado | ~808M total: ~5M código+config+tests+runs/pinned+docs (TRACKEADO en Meta-Factory) + 803M `datasets/` (EN DISCO, gitignorado — ver abajo) |

## Verificar el pin (dos verificadores; aritmética, sin modelo)

```
git -C ~/University/Integración/APP/dataset_agent_re rev-parse 89ad45b            # → 89ad45b548c3e3f9464dc4feb081ea812cead5ac
git -C ~/University/Integración/APP/dataset_agent_re rev-parse '89ad45b^{tree}'   # → b6d15653623a8b6fd98c8c15e309fb2ced45a69b
```

## Qué se copió (y por qué)

Copiado ENTERO desde `git archive 89ad45b` (el commit pineado, NUNCA el working-tree vivo — que
estaba sucio en `docs/informe/*`): `reqcouncil/` (código) + `config/` + `tests/` + `runs/`
(sólo `runs/pinned/` está trackeado upstream — el resto de `runs/*` lo ignora su propio `.gitignore`)
+ `docs/` + `pyproject.toml` + `README.md` + `.env.example` + `.gitignore`. Excluidos (no
versionados upstream tampoco): `.venv/`, `__pycache__/`, `*.egg-info/`, `.pytest_cache/`, `.git/`.
El `.env` real (API keys) NO se copió — sólo `.env.example` (ya trackeado en el commit). NO se copió
`requirements.txt` (export de conveniencia del entorno de desarrollo; la fuente de verdad de
dependencias es `pyproject.toml`, y el camino de código de `eval gates` sólo requiere `pyyaml`).

**`datasets/` (803M) se copió AL DISCO completo — incluyendo `datasets/_originals/` (789M, corpora
crudos que el `.gitignore` upstream deja SIN trackear en git)** — no vía `git archive` (que sólo
trae lo trackeado, 19M) sino con una copia de árbol directa del working-tree del upstream, para que
ReqCouncil sea **autosuficiente en este disco** sin depender de que el directorio externo
`dataset_agent_re` siga existiendo. Está **gitignorado** en este repo (bulk pesado, decisión del
ingeniero 2026-07-10: "es pesado y sólo me interesa que esté en local") — sólo `datasets/MANIFEST.md`
queda trackeado (checksums sha256 + fuente + licencia/NOTICE por dataset, ADR-025 §5) para que la
procedencia sea re-verificable sin depender del bulk ni del directorio externo. `eval_floor` (el
check que gatea `s12`) **nunca lee `datasets/`** — sólo `runs/pinned/` + `config/thresholds.yml`
(H6 `eval gates` es zero-LLM); el manifest es integridad/procedencia, no un requisito del gate.

## Regla dura (la trampa latente que ratificó el diseño S1)

**`products/reqcouncil/` NUNCA debe llevar un `product.yml`** (el archivo que activa el modo R1 de
ASF — instancias multi-producto, ver `src/metafactory/cli.py::_list_products`). El árbol de
ReqCouncil deliberadamente no trae uno: la línea de ASF sigue corriendo en modo default (un solo
producto, `ctx.root == factory root`). Si un incremento FUTURO dejara caer un `product.yml` acá,
ASF flipearía a modo R1 y correría s0..s12 POR-INSTANCIA con `ctx.root == products/reqcouncil` — lo
que rompería `workdir: products/reqcouncil` de `s12` (doble anidado) Y s0..s11 (esperan
`build/product` en la raíz de fábrica) Y perturbaría el pin. Ver
`factories/agent-systems-factory/docs/work/REQCOUNCIL-ADOPT-INCREMENT.md` (diseño completo).
