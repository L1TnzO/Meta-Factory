# datasets/MANIFEST.md — procedencia + integridad (ADR-025 §5)

> `datasets/` (803M, incluye `_originals/` 789M) vive EN DISCO y está **gitignorado** (ver
> `../.gitignore` — bulk pesado, decisión del ingeniero 2026-07-10: "es pesado y sólo me interesa que
> esté en local"). Este MANIFEST es el ÚNICO artefacto TRACKEADO del árbol `datasets/` — checksums
> sha256 por archivo top-level de cada corpus curado + fuente/licencia, para que la procedencia sea
> re-verificable sin depender del bulk ni de que el directorio externo `dataset_agent_re` siga
> existiendo. `eval_floor` (la estación `s12`) **nunca lee `datasets/`** — sólo `runs/pinned/` +
> `config/thresholds.yml` (H6 `eval gates` es zero-LLM); este manifest es integridad/procedencia, NO
> un requisito del gate. Fuente completa de las descripciones: `../datasets/README.md` (copiado del
> pin @89ad45b).

## 1. `inter2us/` — Text2Stories / Inter2US
- **Fuente**: Dente, F., Dalpiaz, F., Papotti, P. (2025). *Automated Alignment between Elicitation
  Interviews and Requirements*. arXiv:2510.08622 [cs.CL]. Paquete de reproducibilidad: Zenodo DOI
  `10.5281/zenodo.20596692` (`inter2us-635C.zip`).
- **Licencia**: MIT (`inter2us/LICENSE`, © 2025 Francesco Dente).
- **Checksums (archivos top-level; subdirs `data/`, `data_annotation/`, `eval/`, `train/` no se
  hashean acá — ver nota final):**
  ```
  82abcb29ea18cd52794f306714571023c9c79fe5e19da43af62f5f65d72369b0  inter2us/.gitignore
  9ebecf9177949dabc7ec422d99e0d080f2775599c25860587cefff9560076f1d  inter2us/LICENSE
  2a1565f676f2645bf71e3eacdeb05833581f101fe096b2acf09eea1f03558184  inter2us/pyproject.toml
  b1cfdd2745a9e985a69a2af5e039c39e68a1b92973a31ad102bb47bae4854d4a  inter2us/README.md
  ```

## 2. `reqelicitbench/` — ReqElicitGym
- **Fuente**: *ReqElicitGym: An Evaluation Environment for Interview Competence in Conversational
  Requirements Elicitation* (Jin, Fang, Li, Yang, He, Chen) — repo `jdm4pku/ReqElicitBench`.
- **Licencia**: no declarada por el upstream (README del corpus) — contactar a los autores si se
  publicara algo derivado (nota heredada de `datasets/README.md`).
- **Checksums (archivos top-level; subdirs `conversation_result/`, `metrics_result/`,
  `ReqElicitGym/` no se hashean acá):**
  ```
  fde5bb62718947670243b274e487ed7d24af7f72516a43b2a3b997391c4bc4ef  reqelicitbench/README.md
  72c858eba2f5e89907a9eddbfe08fe2c748b5d90c3e579049b021b1d2410ac9a  reqelicitbench/README_zh.md
  4f2bd2ccf2433adfb6e53a64b081c9684081cb4025d1c7bbe06835ceabbe951d  reqelicitbench/requirements.txt
  a0d16b44e6ac93ed9f43436846a597a9be36b180447494d9148ef9b8376ccfcf  reqelicitbench/run_reqelicitgym.py
  828fa364b7ff1d7b1e891393d9df214899bca6a3ff192d2c17f3e0d11d36c25f  reqelicitbench/run_reqelicitgym.sh
  ```

## 3. `wepgcomp_maislugar/` — WEPGCOMP y +Lugar (industria real, WER 2025)
- **Fuente**: material suplementario del estudio WER 2025 sobre generación de requisitos desde
  transcripciones reales. Zenodo DOI `10.5281/zenodo.15080374`. Idioma: portugués.
- **Licencia**: material suplementario de estudio académico — uso evaluación/investigación,
  citar la fuente (regla general de `datasets/README.md §Reglas de uso`).
- **Checksums (todo el corpus es plano, sin subdirs):**
  ```
  e720f847e6ae4f3a87c02df863c00b13d27cb94d5f74f669570b1b3097cff506  wepgcomp_maislugar/História de usuários - WEPGCOMP.pdf
  115273903e4aefd426fbfffebd530f2b5bbc6bf877cf979736efb28624328043  wepgcomp_maislugar/Histórias de Usuários +Lugar.pdf
  65787541fb9b65a483d5c9f3d546044ee3a4a58bd0339607f2b17b998ab398f8  wepgcomp_maislugar/Meeting Transcription - +Lugar.pdf
  e8ea59317740fd4d6f88460531b199c28c20285c5afbd0f3903d4c403604c11f  wepgcomp_maislugar/Meeting Transcription - WEPGCOMP.pdf
  e232b2d5eff3ea5cfb5b7184531c14aad3be15558276c240133efa598fe824ab  wepgcomp_maislugar/Prompt.pdf
  12a1190e0476e2d668b652147e835e9884f1e67da31ed660afaf308aa68ac24d  wepgcomp_maislugar/prompt_wepgcomp_study.txt
  2184d3d9f44c6ba5978d805d65e41cd2e838fbd41bfa2d58f7af0c1bd2d4c04a  wepgcomp_maislugar/Requisitos - +Lugar.xlsx
  e9d5b6159f9a1e6284bb710c4a73be85396ff0fb12f71cc324981c8b6e8dbfe1  wepgcomp_maislugar/Requisitos - WEPGCOMP.xlsx
  7b80fdda74b4252dca6391d58f0896cb5327037ef7bbe15393c65d8a1fb3fdfc  wepgcomp_maislugar/transcript_maislugar.txt
  839e335d02ffb22e872c1855d0494c2431ac5a89132bd2a2be0044d5cdc59ae2  wepgcomp_maislugar/transcript_wepgcomp.txt
  ```

## 4. `recover/` — RECOVER (consenso de expertos humanos)
- **Fuente**: Voria, G., Casillo, F., Gravino, C., Catolino, G., Palomba, F. (2024). *RECOVER: Toward
  Requirements Generation from Stakeholders' Conversations*. arXiv:2411.19552 [cs.SE] (Online
  Appendix público).
- **Licencia**: no declarada explícitamente por el upstream — mismo régimen que los demás corpora
  de terceros (evaluación/investigación, citar fuente).
- **Checksums (archivos top-level; subdir `requirements_lists/` no se hashea acá):**
  ```
  da449949655b205a52ba25c94154d029a973a129825a57f71dc154761c82b7d4  recover/example_conversation.txt
  df916f5846a2892eb6354206d679f2d9ea101d4fe7d8747dd67af90ddc992bf6  recover/PURE_annotated_dataset.csv
  da84da33ec3df34e2eca6395236186e6c962901d2b6189ffb56704ef8b6c8f97  recover/Step1-2_predicted_requirements.txt
  ```

## 5. `_originals/` — corpora crudos (789M, gitignorado también upstream)
Conservados tal cual se descargaron, previos a la curación de arriba (§1-4). No trackeados NUNCA en
git (ni upstream ni acá) por tamaño; presentes en disco sólo para trazabilidad de la extracción.
Ningún gate los lee (ni siquiera `eval_floor` — que sólo toca `runs/pinned` + `config/thresholds.yml`).

| Subdir | Tamaño | Corresponde a |
| --- | --- | --- |
| `RECOVEROnlineAppendix/` | 787M | `recover/` (§4) |
| `ReqElicitBench/` | 1.9M | `reqelicitbench/` (§2) |
| `Text2Stories(Inter2US)/` | 236K | `inter2us/` (§1) |
| `WEPGCOMP_y_+Lugar/` | 740K | `wepgcomp_maislugar/` (§3) |

## Re-hidratación
Si `datasets/` se limpia del disco local (gitignorado, no sobrevive un `git clean -fdx`), este
MANIFEST alcanza para re-verificar identidad de lo re-descargado (mismos sha256 top-level) pero NO
para re-obtener los bytes — la fuente de los bytes son los DOIs/repos citados arriba (§1-4), no
`dataset_agent_re` (que es sólo dónde se curaron por primera vez, ver `../PROVENANCE.md`).
