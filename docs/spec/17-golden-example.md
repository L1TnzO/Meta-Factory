<!-- meta:doc sha=1415fbb47dd296a755ff6c61e2a0902e5c7b6575 updated=2026-07-28T03:56Z -->
# 17 — Golden example: the `dummy` factory, end to end

`dummy` is the smallest factory the system builds (bootstrap seed B5). It is small enough to hold in
one page and real enough to exercise five of the harder check kinds (`product_env`, `infra_up`,
`mcp_tools` among them) — everything below is transcribed from committed files, cited by `path:line`,
and closed by a machine-checked block (§5) that the gate `tools/spec_doc_check.py --mode golden`
recomputes and compares against the COMMITTED `factories/dummy/pinned_verdict.json`.

## 1. The spec (`factories/dummy/factory.spec.yml`)

Top-level shape (§03-engine.md §2 gives the general grammar; this is dummy's INSTANCE of it):

| Key | Dummy's value |
| --- | --- |
| `factory.{name,slug,maturity}` | `Dummy Factory` / `dummy` / `bootstrap` — `factory.spec.yml:6-9` |
| `domain.produces` | `"un módulo de saludo trivial con un marcador invariante"` — `:12` |
| `domain.capabilities` | 5 entries, one per station, each with `id · invariant · artifact · proof · status: built` — `:16-40` |
| `domain.station_sequence` | 5 stations `s00..s04`, each `activation: always`, each `depends_on`/chained to its predecessor — `:42-134` |
| `domain.product` | `{product_module: greeting, greet_fn: greet, marker: DUMMY_OK}` + the I-5 domain/generated boundary (`boundary_domain_dest: domain/greeting.py`, `boundary_generated_dest: generated/runner.py`) — `:135-163` |
| `machinery.harness` | 3 agents (`writer`/`reviewer`/`triage`), 1 command (`/greet`), 1 skill (`verificar-fabrica`) — `:166-224` |
| `machinery.infra` | 1 service (`sandbox-svc`, `kind: socket-service`, `endpoint: infra.sock`, `marker: INFRA_OK`), stdlib `AF_UNIX` server+client emitted inline — `:229-260` |
| `machinery.mcp` | 2 tools (`greet`, `echo`), a stdlib JSON-RPC/stdio server+prover emitted inline — `:264-322` |
| `factory_substrate` | the standard block (`anti_rubber_stamp_column: true`, `verdict_bus.max_lines: 10`, …) — `:325-333` |
| `requirements.functional` | 5 requirements `REQ-F-001..005`, each `satisfied_by:[s0N]` + `capability:` pointing at the matching capability id — `:336-361` |

Every requirement maps 1:1 to a capability and a station: `REQ-F-001→invariant_marker→s00`,
`REQ-F-002→release_manifest→s01`, `REQ-F-003→product_toolchain_proof→s02`,
`REQ-F-004→infra_sandbox→s03`, `REQ-F-005→mcp_tools_exposed→s04`.

## 2. The five stations

Materialized 1:1 from `station_sequence` into `factories/dummy/stations/s0N.yml` by meta station `m02`
(§3). What each builds and checks:

| Station | Builds | Checks (`kind`) | Depends on | Proves |
| --- | --- | --- | --- | --- |
| `s00` "build greeting" | renders `domain/greeting.py`→`build/greeting.py`, `generated/runner.py`→`build/runner.py`, `generated/test_greeting.py`→`build/test_greeting.py` — `stations/s00.yml:5-11` | `compile` (`py_compile`, both files) · `runs` (`import_runs`: imports `runner`, asserts `runner.run() == 'DUMMY_OK'`) · `invariant` (`artifact_contains`: `build/greeting.py` contains `DUMMY_OK`) — `:12-22` | — (first) | REQ-F-001 / `invariant_marker` |
| `s01` "release manifest" | `generate` action: a `via` Python one-liner concatenates a brief (`RELEASE_OK manifest for dummy`) with `build/greeting.py`'s content into `build/manifest.txt` — `stations/s01.yml:5-13` | `release_tag` (`artifact_contains`: `manifest.txt` has `RELEASE_OK`) · `chain_marker` (`artifact_contains`: `manifest.txt` has `DUMMY_OK`, proving the embed is a REAL chain, not two independent stations) — `:14-19` | `s00` | REQ-F-002 / `release_manifest` |
| `s02` "proof in the product's own toolchain" | none (`builds: []`) — `stations/s02.yml:5` | `product_unittest` (`product_env`: `workdir: build`, `bootstrap` = `python -m venv --without-pip .venv`, `cmd` = `.venv/bin/python -m unittest discover -s . -p test_*.py`) — `:6-14` | `s01` | REQ-F-003 / `product_toolchain_proof` (DES-8: the venv is scrubbed from the factory's own PYTHONPATH) |
| `s03` "infra/sandbox" | `emit_infra` action (writes `build/infra/server.py`+`client.py` from `machinery.infra.emit`, spec `:243-260`) — `stations/s03.yml:5-6` | `infra_proof` (`infra_up`: `workdir: build/infra`, `up`=`python server.py infra.sock`, `proof`=`python client.py infra.sock`, `down`=`[]`, `timeout: 8`) — `:7-15` | `s02` | REQ-F-004 / `infra_sandbox` (DES-9: the service must actually LEVANTAR, be reached, and be torn down) |
| `s04` "MCP" | `emit_mcp` action (writes `build/mcp/server.py`+`prove.py` from `machinery.mcp.emit`, spec `:271-322`) — `stations/s04.yml:5-6` | `mcp_proof` (`mcp_tools`: `workdir: build/mcp`, `prove`=`python prove.py`, `tools: [greet, echo]`) — `:7-12` | `s03` | REQ-F-005 / `mcp_tools_exposed` (DES-6: the prover speaks real JSON-RPC/stdio, lists tools, calls each) |

The chain is real, not cosmetic: `s01`'s manifest embeds `s00`'s literal build output (§2 table,
`chain_marker`), so corrupting `s00`'s artifact after the fact would break `s01`'s check too — the
capstone lesson this factory was built to prove (bootstrap B5).

## 3. The walkthrough: spec → line → proofs → pin → re-derivation

The same 9-stage pipeline every factory goes through (`03-engine.md §1`), concretely for `dummy`:

1. **Register.** `meta new factories/dummy/factory.spec.yml` → `cmd_new()`, `cli.py:227-240` — validates
   the spec (`spec.validator.validate`) and copies it to `factories/dummy/factory.spec.yml` +
   `.metafactory.json`.
2. **Run the meta line `m00→m08`.** `cmd_station()`/`run_station()`, `cli.py:261`, `engine/runner.py:69`,
   over `src/metafactory/stations/*.yml`. For `dummy` the meta-line proofs currently committed at
   `factories/dummy/.proof/` are `m00.json` (spec contract, `stations/m00.yml:1-5`), `m01.json` (seed +
   column install, `stations/m01.yml:1-6`), and `m07.json` (harness emit, `stations/m07.yml:1-11`) — the
   three meta stations whose proofs are retained in this tree today; `m02..m06,m08` are re-derivable but
   not currently pinned in `.proof/` (only the PRODUCT line's `s00..s04` pin is committed, §4).
3. **Materialize the product line.** Meta station `m02` (`stations/m02.yml:1-13`) runs
   `action: materialize_line` → `_materialize_line()`, `codegen/renderer.py:129` — writes one
   `factories/dummy/stations/s0N.yml` per `domain.station_sequence` entry (§2), and its own check
   `stations_match_spec` asserts the materialized line's ids equal the spec's declared sequence, ordered
   by the SAME natural key the engine uses (`_natural_key`, `engine/sequence.py:16-22`) — so `s9`
   ordering bugs can't hide behind a lexicographic accident.
4. **Emit the harness.** Meta station `m07` (`stations/m07.yml:1-11`) runs `action: emit_harness` →
   `_emit_harness()`, `codegen/renderer.py:238-264` — writes `factories/dummy/.claude/{agents,commands,skills}`
   from `machinery.harness` (§1 table); its checks `agent_shadow`/`command_runs` prove every agent's
   `shadows[]` entry is real and wired, and every generated command actually runs.
5. **Build the product end-to-end.** `meta product-run --factory dummy` → `cmd_product_run()`,
   `cli.py:323-333` → `_run_product_line()`, `cli.py:275` → `load_sequence(fdir/"stations")` (the 5 files
   from step 3) → `run_station()` per station: `apply_builds` → `write_active` → resolve+run `checks` →
   `ctx.verifier.verify_station()` (the SEED, not the engine — Lock #1) → `open_gate()` → journal append
   (`engine/runner.py:69-106`, `03-engine.md §4`). This is also what meta station `m08`
   (`stations/m08.yml:1-8`, "Auto-test anti-fachada") runs when birthing the factory itself — a render-green
   product with a broken invariant MUST be able to fail here (the capstone negative test).
6. **Proofs land under `.proof/`.** One `s0N.json` per station, written by `seed/verifier.py:verify_station()`
   — `{"station", "passed", "checks":[{"name","cmd","exit"}], "computed_at", "proof_sha", "writer"}`
   (`03-engine.md §7`). `passed = len(checks) > 0 and all(exit == 0)`. Dummy's 5 real proof files live at
   `factories/dummy/.proof/s00.json` .. `s04.json` (read directly for §5, never hand-copied).
7. **Pin.** `meta pin` → `_pin_from_proofs()`, `cli.py:498-511` — for every ACTIVE station, requires a
   `passed: true` proof and writes `pinned_verdict.json = {station_id: proof_sha}`. Dummy's committed pin
   is `factories/dummy/pinned_verdict.json` — exactly the 5 keys `s00..s04` (§4).
8. **Re-derive (CI).** `meta ci --rederive --factory dummy` → `rederive_pinned()`, `cli.py:435-453` —
   deletes `.proof/` + `build/`, re-runs the full product line from source, recomputes each `proof_sha`,
   and demands equality against the pin **in both directions** via `_compare_to_pinned()`, `cli.py:421-432`
   (a station present in one side and absent from the other is a mismatch, not a tolerance — same rule as
   `pin_matches()` in the kernel, `14-kernel-reference.md §2`). The underlying primitive,
   `verify/verdict.py:rederive_verdict()` (`:29-60`), does this in a throwaway `tempfile.mkdtemp` clone —
   custody of the in-tree `.proof/` is never the root of trust; replicability is.

A re-implementer who only has this page can therefore reconstruct the exact command sequence
(`meta new` → `meta station m00..m08 --factory dummy` → `meta product-run --factory dummy` → `meta pin
--factory dummy` → `meta ci --rederive --factory dummy`) and knows, station by station, what artifact
and what checks must exist for each to go green.

## 4. Proof → pin, the arithmetic

The kernel (`14-kernel-reference.md §2`, `compute_proof_sha`) hashes `{station: id, checks: sorted[(name,
exit)]}` as canonical JSON, sha256, hex — excluding timestamps, stdout, command lines, machine identity,
and check ORDER. For `s00`, whose real proof (`factories/dummy/.proof/s00.json`) carries checks
`compile=0, runs=0, invariant=0`:

```python
compute_proof_sha("s00", [{"name": "compile", "exit": 0},
                           {"name": "runs", "exit": 0},
                           {"name": "invariant", "exit": 0}])
# -> "c84e1f26d64fdeb31c3d2727a6e682c532c1fec1dc3b381bcc79b2cc313cb477"
```

which is exactly `pinned_verdict.json["s00"]`. Change ANY exit code, add/remove a check, or rename one,
and the digest changes — that is the entire trust argument, applied once by hand here so §5's block is
not the first time a reader sees it work.

## 5. The machine-checked block

Recomputed by `tools/spec_doc_check.py --mode golden` (`check_golden()`,
`tools/spec_doc_check.py:91-136`) via the kernel extracted from `14-kernel-reference.md §2`, and compared
station-by-station against the COMMITTED `factories/dummy/pinned_verdict.json` — CONF-G2 (the declared
checks reproduce the declared `proof_sha`), CONF-G3 (that sha equals the committed pin), CONF-G4 (a
pinned station recomputes as `passed`), CONF-G5 (no pinned station is omitted here). Every `(name, exit)`
pair below is transcribed verbatim from `factories/dummy/.proof/s0N.json`, never invented.

<!-- golden: dummy -->
```json
{"factory": "dummy",
 "stations": [
   {"id": "s00", "checks": [["compile", 0], ["runs", 0], ["invariant", 0]],
    "proof_sha": "c84e1f26d64fdeb31c3d2727a6e682c532c1fec1dc3b381bcc79b2cc313cb477"},
   {"id": "s01", "checks": [["release_tag", 0], ["chain_marker", 0]],
    "proof_sha": "47361a92dcd14c6e3a704cca75ab279c1eb936537e70c0b32f6f4e7806f0b85a"},
   {"id": "s02", "checks": [["product_unittest", 0]],
    "proof_sha": "69df50461b853a231576111569904e131ece7e7de7a089eb470e7192bdb43643"},
   {"id": "s03", "checks": [["infra_proof", 0]],
    "proof_sha": "db577b19df14eeedf383d4161cb21047ac1627ea0e54142e8696852c1dacb345"},
   {"id": "s04", "checks": [["mcp_proof", 0]],
    "proof_sha": "6bd27228813f97fa516ffedf5692d944bff558ad9e349974c3c5c413d3399843"}
 ]}
```

## 6. What would break this page

- Editing any station's `builds`/`checks` in `factory.spec.yml` without re-running `m02` — `stations_match_spec`
  (`stations/m02.yml:12-13`) catches the drift before a proof is even attempted.
- Hand-editing a `.proof/s0N.json` exit code or `proof_sha` — `gate_recompute_ok()`
  (`14-kernel-reference.md §2`) rejects it; a station's own re-derivation would also change.
- Corrupting `build/greeting.py`'s `DUMMY_OK` marker after `s00` ran once — `s00`'s own `invariant` check
  would fail on the NEXT run, and `s01`'s `chain_marker` check would fail too (the manifest embedded the
  old, now-mismatched content) — this is the exact capstone scenario bootstrap B5 was built to prove: a
  corrupted marker blocks the COLUMN, not a human reviewer.
- Any of the above makes `meta ci --rederive --factory dummy` (§3 step 8) diverge from the committed
  `pinned_verdict.json`, which is precisely what `--mode golden` (§5) would also catch — the same law,
  checked twice, by two different processes, on purpose.
