#!/usr/bin/env python3
"""scaffold_product.py — el codegen de PRODUCTO de la fábrica iot (MAT-7).

DETERMINISTA: lee el blueprint (`domain.product`) de `factory.spec.yml` y EMITE un gateway IoT en Go
en `build/product/` (contrato de mensaje tipado + topología pub/sub + validador BFS + gate OTA +
procedencia + telemetría store-and-forward + broker socket-Unix). Es el `via` del slot `generate`
(ADR-013): el sustrato del Meta-Factory NO genera producto ni nombra ninguna tech Go (ADR-012) — esta
lógica vive en la FÁBRICA (su plan eligió Go). El determinismo hace re-derivable la línea (`ci --rederive`
re-pinea idéntico — el `proof_sha` es exit-code-based, así que el output de `go test` no lo afecta).

El producto se verifica en SU PROPIO toolchain (DES-8): `go vet ./...` (compila TODO el módulo: un drift
del esquema rompe acá) y `go test` por paquete. HERMÉTICO: Go stdlib, `GOPROXY=off`, sin red ni `go get`.

Generado DESDE el blueprint (no hardcodeado): el struct del mensaje + sus campos requeridos (DES-6), las
aristas de la topología + la raíz (DES-2), y el join-key de procedencia (DES-5). El resto (algoritmo BFS,
guard OTA, store-and-forward, broker) son plantillas con el nombre del mensaje sustituido.

Uso:
  python codegen/scaffold_product.py            # emite el árbol Go en build/product/ (METAFACTORY_ROOT)
  python codegen/scaffold_product.py --selftest # parsea el blueprint y lista los archivos; no escribe
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# tipo del blueprint -> tipo Go + un valor de muestra para los tests generados (determinista).
_GO_TYPE = {"string": "string", "float": "float64", "float64": "float64",
            "int": "int64", "int64": "int64", "bool": "bool"}
_GO_SAMPLE = {"string": '"sample"', "float64": "1.5", "int64": "1", "bool": "false"}


def _load_blueprint(root: Path) -> dict:
    import yaml
    data = yaml.safe_load((root / "factory.spec.yml").read_text(encoding="utf-8")) or {}
    bp = ((data.get("domain") or {}).get("product") or {})
    for req in ("package_name", "module_path"):
        if req not in bp:
            raise SystemExit(f"scaffold: blueprint domain.product sin {req!r} (spec incompleto)")
    msg = bp.get("message") or {}
    if not msg.get("name") or not msg.get("fields"):
        raise SystemExit("scaffold: blueprint domain.product.message sin 'name'/'fields' (spec incompleto)")
    for f in msg["fields"]:
        if f.get("type") not in _GO_TYPE:
            raise SystemExit(f"scaffold: campo {f.get('name')!r} con tipo no soportado {f.get('type')!r}")
    topo = bp.get("topology") or {}
    if not topo.get("root") or not topo.get("topics"):
        raise SystemExit("scaffold: blueprint domain.product.topology sin 'root'/'topics' (spec incompleto)")
    if not (bp.get("provenance") or {}).get("join_key"):
        raise SystemExit("scaffold: blueprint domain.product.provenance sin 'join_key' (spec incompleto)")
    return bp


def _go_type(bp_type: str) -> str:
    return _GO_TYPE[bp_type]


def _field_type_map(msg: dict) -> dict:
    return {f["name"]: _go_type(f["type"]) for f in msg["fields"]}


# ── contract/ (DES-6) ────────────────────────────────────────────────────────
def _contract_go(msg: dict) -> str:
    name = msg["name"]
    required = msg.get("required") or []
    for r in required:
        if _field_type_map(msg).get(r) != "string":
            raise SystemExit(f"scaffold: campo requerido {r!r} no es string (la validación del borde "
                             f"genera un chequeo `== \"\"`; sólo soporta requeridos string)")
    members = "\n".join(f"\t{f['name']} {_go_type(f['type'])}" for f in msg["fields"])
    cond = " || ".join(f'r.{r} == ""' for r in required)
    return (
        "// Package contract defines the typed device→gateway message contract (DES-6). A drift of any\n"
        "// field type breaks the build of every consumer — the `go vet ./...` gate of s0.\n"
        "package contract\n\n"
        "import \"errors\"\n\n"
        f"// {name} is the typed telemetry message that crosses the device→gateway boundary.\n"
        f"type {name} struct {{\n{members}\n}}\n\n"
        "// ErrMalformed is returned when a message violates the edge contract (a required field is empty).\n"
        "var ErrMalformed = errors.New(\"malformed reading rejected at the edge\")\n\n"
        "// Validate enforces the edge contract: the required fields must be non-empty. A malformed\n"
        "// message is REJECTED here, never ingested (DES-6).\n"
        f"func (r {name}) Validate() error {{\n"
        f"\tif {cond} {{\n"
        "\t\treturn ErrMalformed\n"
        "\t}\n"
        "\treturn nil\n"
        "}\n"
    )


def _sample_lit(msg: dict, *, omit: str | None = None) -> str:
    """A composite literal for the message with sample values; `omit` drops one field (for the
    malformed-edge test — a required field left at its zero value)."""
    parts = []
    for f in msg["fields"]:
        if f["name"] == omit:
            continue
        parts.append(f"{f['name']}: {_GO_SAMPLE[_go_type(f['type'])]}")
    return ", ".join(parts)


def _contract_test_go(msg: dict) -> str:
    name = msg["name"]
    required = msg.get("required") or []
    omit = required[0]
    return (
        "package contract\n\n"
        "import \"testing\"\n\n"
        "func TestValidateAcceptsWellFormed(t *testing.T) {\n"
        f"\tr := {name}{{{_sample_lit(msg)}}}\n"
        "\tif err := r.Validate(); err != nil {\n"
        "\t\tt.Fatalf(\"well-formed reading rejected at the edge: %v\", err)\n"
        "\t}\n"
        "}\n\n"
        "func TestValidateRejectsMalformed(t *testing.T) {\n"
        f"\t// Missing required {omit} → must be rejected at the edge, not ingested.\n"
        f"\tr := {name}{{{_sample_lit(msg, omit=omit)}}}\n"
        "\tif err := r.Validate(); err == nil {\n"
        f"\t\tt.Fatal(\"malformed reading (empty {omit}) was NOT rejected at the edge\")\n"
        "\t}\n"
        "}\n"
    )


# ── topology/ (DES-2) ────────────────────────────────────────────────────────
_TOPOLOGY_GO_HEAD = (
    "// Package topology models the pub/sub topic graph and validates it structurally (DES-2): the Go\n"
    "// analogue of ASF's s11 compiled-graph validator — every node reachable from the root, no orphans,\n"
    "// without running the broker.\n"
    "package topology\n\n"
    "import \"fmt\"\n\n"
    "// Edge is one declared topic: a publisher node writes it, a subscriber node consumes it.\n"
    "type Edge struct {\n"
    "\tTopic      string\n"
    "\tPublisher  string\n"
    "\tSubscriber string\n"
    "}\n\n"
    "// Graph is the declared pub/sub topology rooted at the ingestion node.\n"
    "type Graph struct {\n"
    "\tRoot  string\n"
    "\tEdges []Edge\n"
    "}\n\n"
    "// Validate is a structural BFS check (DES-2): no orphan topic (every edge has a publisher AND a\n"
    "// subscriber), and every node is reachable from Root over the (undirected) pub/sub links — no\n"
    "// disconnected device. Pure structure: it does NOT start the broker.\n"
    "func (g Graph) Validate() error {\n"
    "\tfor _, e := range g.Edges {\n"
    "\t\tif e.Topic == \"\" || e.Publisher == \"\" || e.Subscriber == \"\" {\n"
    "\t\t\treturn fmt.Errorf(\"orphan topic (missing endpoint): %+v\", e)\n"
    "\t\t}\n"
    "\t}\n"
    "\tadj := map[string]map[string]bool{}\n"
    "\tall := map[string]bool{}\n"
    "\tlink := func(a, b string) {\n"
    "\t\tif adj[a] == nil {\n"
    "\t\t\tadj[a] = map[string]bool{}\n"
    "\t\t}\n"
    "\t\tadj[a][b] = true\n"
    "\t}\n"
    "\tfor _, e := range g.Edges {\n"
    "\t\tlink(e.Publisher, e.Subscriber)\n"
    "\t\tlink(e.Subscriber, e.Publisher)\n"
    "\t\tall[e.Publisher] = true\n"
    "\t\tall[e.Subscriber] = true\n"
    "\t}\n"
    "\tif !all[g.Root] {\n"
    "\t\treturn fmt.Errorf(\"root %q is not present in the topology\", g.Root)\n"
    "\t}\n"
    "\tseen := map[string]bool{g.Root: true}\n"
    "\tqueue := []string{g.Root}\n"
    "\tfor len(queue) > 0 {\n"
    "\t\tn := queue[0]\n"
    "\t\tqueue = queue[1:]\n"
    "\t\tfor m := range adj[n] {\n"
    "\t\t\tif !seen[m] {\n"
    "\t\t\t\tseen[m] = true\n"
    "\t\t\t\tqueue = append(queue, m)\n"
    "\t\t\t}\n"
    "\t\t}\n"
    "\t}\n"
    "\tfor n := range all {\n"
    "\t\tif !seen[n] {\n"
    "\t\t\treturn fmt.Errorf(\"node %q is unreachable from root %q (orphaned subgraph)\", n, g.Root)\n"
    "\t\t}\n"
    "\t}\n"
    "\treturn nil\n"
    "}\n\n"
)


def _topology_go(topo: dict) -> str:
    edges = "\n".join(
        f'\t\t\t{{Topic: "{t["name"]}", Publisher: "{t["publisher"]}", Subscriber: "{t["subscriber"]}"}},'
        for t in topo["topics"]
    )
    return (
        _TOPOLOGY_GO_HEAD +
        "// Declared returns the blueprint's pub/sub topology (codegen'd from domain.product.topology).\n"
        "func Declared() Graph {\n"
        "\treturn Graph{\n"
        f'\t\tRoot: "{topo["root"]}",\n'
        "\t\tEdges: []Edge{\n"
        f"{edges}\n"
        "\t\t},\n"
        "\t}\n"
        "}\n"
    )


_TOPOLOGY_TEST_GO = (
    "package topology\n\n"
    "import \"testing\"\n\n"
    "func TestDeclaredTopologyIsValid(t *testing.T) {\n"
    "\tif err := Declared().Validate(); err != nil {\n"
    "\t\tt.Fatalf(\"declared topology rejected by the BFS validator: %v\", err)\n"
    "\t}\n"
    "}\n\n"
    "func TestOrphanedSubgraphRejected(t *testing.T) {\n"
    "\tg := Declared()\n"
    "\tg.Edges = append(g.Edges, Edge{Topic: \"ghost\", Publisher: \"lonely\", Subscriber: \"void\"})\n"
    "\tif err := g.Validate(); err == nil {\n"
    "\t\tt.Fatal(\"an orphaned subgraph (unreachable from root) was accepted by the BFS validator\")\n"
    "\t}\n"
    "}\n"
)


# ── ota/ (DES-3) ─────────────────────────────────────────────────────────────
_OTA_GO = (
    "// Package ota enforces a non-skippable firmware-update signature gate (DES-3): there is no code\n"
    "// path that flashes an unsigned firmware — Apply ALWAYS verifies first.\n"
    "package ota\n\n"
    "import \"errors\"\n\n"
    "// ErrUnsigned is returned when an OTA update fails signature verification.\n"
    "var ErrUnsigned = errors.New(\"OTA update refused: signature verification failed (non-skippable gate)\")\n\n"
    "// Firmware is an update payload with its claimed signature.\n"
    "type Firmware struct {\n"
    "\tVersion   string\n"
    "\tPayload   []byte\n"
    "\tSignature string\n"
    "}\n\n"
    "// verifySignature is the gate. The structural invariant (DES-3) is that Apply cannot flash without\n"
    "// passing it; the signature scheme itself is a stand-in (real crypto would be DATA of the fleet).\n"
    "func verifySignature(fw Firmware) bool {\n"
    "\treturn fw.Signature == \"VALID-\"+fw.Version\n"
    "}\n\n"
    "// OTAGuard tracks the flashed version. Apply is the ONLY path to flash and it goes through\n"
    "// verifySignature first — the gate is the roof, not a step that can be skipped.\n"
    "type OTAGuard struct {\n"
    "\tFlashed string\n"
    "}\n\n"
    "// Apply flashes fw iff its signature verifies; otherwise it refuses BEFORE touching flash state.\n"
    "func (g *OTAGuard) Apply(fw Firmware) error {\n"
    "\tif !verifySignature(fw) {\n"
    "\t\treturn ErrUnsigned\n"
    "\t}\n"
    "\tg.Flashed = fw.Version\n"
    "\treturn nil\n"
    "}\n"
)

_OTA_TEST_GO = (
    "package ota\n\n"
    "import \"testing\"\n\n"
    "func TestApplyFlashesSigned(t *testing.T) {\n"
    "\tg := &OTAGuard{}\n"
    "\tfw := Firmware{Version: \"2.0.0\", Payload: []byte(\"fw\"), Signature: \"VALID-2.0.0\"}\n"
    "\tif err := g.Apply(fw); err != nil {\n"
    "\t\tt.Fatalf(\"signed firmware refused: %v\", err)\n"
    "\t}\n"
    "\tif g.Flashed != \"2.0.0\" {\n"
    "\t\tt.Fatalf(\"signed firmware not flashed: %q\", g.Flashed)\n"
    "\t}\n"
    "}\n\n"
    "func TestApplyRefusesUnsigned(t *testing.T) {\n"
    "\tg := &OTAGuard{}\n"
    "\tfw := Firmware{Version: \"2.0.0\", Payload: []byte(\"fw\"), Signature: \"FORGED\"}\n"
    "\tif err := g.Apply(fw); err == nil {\n"
    "\t\tt.Fatal(\"unsigned firmware was flashed — the OTA gate was skipped\")\n"
    "\t}\n"
    "\tif g.Flashed != \"\" {\n"
    "\t\tt.Fatalf(\"unsigned firmware modified flash state %q — the OTA gate was skipped\", g.Flashed)\n"
    "\t}\n"
    "}\n"
)


# ── provenance/ (DES-5) ──────────────────────────────────────────────────────
def _provenance_go(bp: dict, msg: dict, module: str) -> str:
    name = msg["name"]
    ftypes = _field_type_map(msg)
    join = bp["provenance"]["join_key"]
    key_members = "\n".join(f"\t{k} {ftypes[k]}" for k in join)
    key_of = ", ".join(f"{k}: r.{k}" for k in join)
    return (
        "// Package provenance keeps an append-only audit trail linking aggregated metrics back to the\n"
        "// raw readings that formed them, by join-key — DES-5.\n"
        "package provenance\n\n"
        "import (\n"
        "\t\"fmt\"\n\n"
        f"\t\"{module}/contract\"\n"
        ")\n\n"
        "// key is the provenance join-key (domain.product.provenance.join_key).\n"
        f"type key struct {{\n{key_members}\n}}\n\n"
        f"func keyOf(r contract.{name}) key {{\n"
        f"\treturn key{{{key_of}}}\n"
        "}\n\n"
        "// Trail records raw readings under their join-key so aggregates can be traced backward.\n"
        "type Trail struct {\n"
        f"\traw map[key]contract.{name}\n"
        "}\n\n"
        f"func NewTrail() *Trail {{ return &Trail{{raw: map[key]contract.{name}{{}}}} }}\n\n"
        "// Record ingests a raw reading into the trail under its join-key.\n"
        f"func (t *Trail) Record(r contract.{name}) {{ t.raw[keyOf(r)] = r }}\n\n"
        "// Aggregate is a derived metric plus the join-keys of the readings that formed it.\n"
        "type Aggregate struct {\n"
        "\tMetric string\n"
        "\tValue  float64\n"
        "\tfrom   []key\n"
        "}\n\n"
        "// Mean aggregates readings into a metric, remembering their join-keys for provenance.\n"
        f"func (t *Trail) Mean(metric string, rs []contract.{name}) Aggregate {{\n"
        "\tvar sum float64\n"
        "\tfrom := make([]key, 0, len(rs))\n"
        "\tfor _, r := range rs {\n"
        "\t\tsum += r.Value\n"
        "\t\tfrom = append(from, keyOf(r))\n"
        "\t}\n"
        "\tvar v float64\n"
        "\tif len(rs) > 0 {\n"
        "\t\tv = sum / float64(len(rs))\n"
        "\t}\n"
        "\treturn Aggregate{Metric: metric, Value: v, from: from}\n"
        "}\n\n"
        "// Trace walks an aggregate BACKWARD to the raw readings that formed it (DES-5). An aggregate\n"
        "// that references a key with no recorded raw reading is a provenance break: error.\n"
        f"func (t *Trail) Trace(a Aggregate) ([]contract.{name}, error) {{\n"
        f"\tout := make([]contract.{name}, 0, len(a.from))\n"
        "\tfor _, k := range a.from {\n"
        "\t\tr, ok := t.raw[k]\n"
        "\t\tif !ok {\n"
        "\t\t\treturn nil, fmt.Errorf(\"provenance break: aggregate %q references unknown reading %+v\", a.Metric, k)\n"
        "\t\t}\n"
        "\t\tout = append(out, r)\n"
        "\t}\n"
        "\treturn out, nil\n"
        "}\n"
    )


def _provenance_test_go(msg: dict, module: str) -> str:
    name = msg["name"]
    # two readings sharing metric, distinct join-keys
    r1 = f'{{DeviceID: "dev-1", Metric: "temp", Value: 20, TS: 1, FWVersion: "1.0.0"}}'
    r2 = f'{{DeviceID: "dev-2", Metric: "temp", Value: 22, TS: 2, FWVersion: "1.0.0"}}'
    orphan = f'{{DeviceID: "ghost", Metric: "temp", Value: 1, TS: 9, FWVersion: "9.9.9"}}'
    return (
        "package provenance\n\n"
        "import (\n"
        "\t\"testing\"\n\n"
        f"\t\"{module}/contract\"\n"
        ")\n\n"
        "func TestTraceBacktracksToRawReadings(t *testing.T) {\n"
        "\ttr := NewTrail()\n"
        f"\trs := []contract.{name}{{\n"
        f"\t\t{r1},\n"
        f"\t\t{r2},\n"
        "\t}\n"
        "\tfor _, r := range rs {\n"
        "\t\ttr.Record(r)\n"
        "\t}\n"
        "\tagg := tr.Mean(\"temp.mean\", rs)\n"
        "\tif agg.Value != 21 {\n"
        "\t\tt.Fatalf(\"aggregate value = %v, want 21\", agg.Value)\n"
        "\t}\n"
        "\tgot, err := tr.Trace(agg)\n"
        "\tif err != nil {\n"
        "\t\tt.Fatalf(\"trace failed: %v\", err)\n"
        "\t}\n"
        "\tif len(got) != 2 {\n"
        "\t\tt.Fatalf(\"trace returned %d raw readings, want 2\", len(got))\n"
        "\t}\n"
        "}\n\n"
        "func TestTraceDetectsProvenanceBreak(t *testing.T) {\n"
        "\ttr := NewTrail()\n"
        "\t// Aggregate references a reading that was never recorded → provenance break.\n"
        f"\torphan := []contract.{name}{{{orphan}}}\n"
        "\tagg := tr.Mean(\"temp.mean\", orphan)\n"
        "\tif _, err := tr.Trace(agg); err == nil {\n"
        "\t\tt.Fatal(\"a provenance break (aggregate over unrecorded readings) was not detected\")\n"
        "\t}\n"
        "}\n"
    )


# ── dedup/ (DES-4: ingestión idempotente) ────────────────────────────────────
def _dedup_go(bp: dict, msg: dict, module: str) -> str:
    name = msg["name"]
    ftypes = _field_type_map(msg)
    join = bp["provenance"]["join_key"]
    key_members = "\n".join(f"\t{k} {ftypes[k]}" for k in join)
    key_of = ", ".join(f"{k}: r.{k}" for k in join)
    return (
        "// Package dedup enforces idempotent ingestion (DES-4): at-least-once delivery must not corrupt\n"
        "// durable state — a reading already accepted (same provenance join-key) is NOT counted twice.\n"
        "// The dual of store-and-forward (telemetry): nothing lost, AND nothing double-counted.\n"
        "package dedup\n\n"
        f"import \"{module}/contract\"\n\n"
        "// key is the idempotency join-key (domain.product.provenance.join_key — the same identity that\n"
        "// provenance traces by, so a re-delivered reading is recognised as the same reading).\n"
        f"type key struct {{\n{key_members}\n}}\n\n"
        f"func keyOf(r contract.{name}) key {{\n"
        f"\treturn key{{{key_of}}}\n"
        "}\n\n"
        "// Set tracks the join-keys already accepted.\n"
        "type Set struct {\n"
        "\tseen map[key]bool\n"
        "}\n\n"
        "func NewSet() *Set { return &Set{seen: map[key]bool{}} }\n\n"
        "// Accept reports whether r is NEW (first time its join-key is seen). A duplicate returns false\n"
        "// and leaves state unchanged beyond the first acceptance — idempotent ingestion (DES-4).\n"
        f"func (s *Set) Accept(r contract.{name}) bool {{\n"
        "\tk := keyOf(r)\n"
        "\tif s.seen[k] {\n"
        "\t\treturn false\n"
        "\t}\n"
        "\ts.seen[k] = true\n"
        "\treturn true\n"
        "}\n\n"
        "// Count is how many distinct readings have been accepted.\n"
        "func (s *Set) Count() int { return len(s.seen) }\n"
    )


def _dedup_test_go(msg: dict, module: str) -> str:
    name = msg["name"]
    r = '{DeviceID: "dev-1", Metric: "temp", Value: 20, TS: 1, FWVersion: "1.0.0"}'
    r2 = '{DeviceID: "dev-2", Metric: "temp", Value: 22, TS: 2, FWVersion: "1.0.0"}'
    return (
        "package dedup\n\n"
        "import (\n"
        "\t\"testing\"\n\n"
        f"\t\"{module}/contract\"\n"
        ")\n\n"
        "func TestAcceptsNewRejectsDuplicate(t *testing.T) {\n"
        "\ts := NewSet()\n"
        f"\tr := contract.{name}{r}\n"
        "\tif !s.Accept(r) {\n"
        "\t\tt.Fatal(\"first reading was not accepted as new\")\n"
        "\t}\n"
        "\tif s.Accept(r) {\n"
        "\t\tt.Fatal(\"a duplicate reading (same join-key) was accepted twice — ingestion is not idempotent\")\n"
        "\t}\n"
        f"\tr2 := contract.{name}{r2}\n"
        "\tif !s.Accept(r2) {\n"
        "\t\tt.Fatal(\"a distinct reading was wrongly treated as a duplicate\")\n"
        "\t}\n"
        "\tif s.Count() != 2 {\n"
        "\t\tt.Fatalf(\"accepted-count = %d, want 2 distinct readings\", s.Count())\n"
        "\t}\n"
        "}\n"
    )


# ── telemetry/ (DES-4) + cmd/broker (DES-9) ──────────────────────────────────
def _forward_go(msg: dict, module: str) -> str:
    name = msg["name"]
    return (
        "// Package telemetry implements store-and-forward telemetry against a live broker (DES-4/DES-9):\n"
        "// a Forwarder buffers readings locally and flushes them to the broker over a unix socket;\n"
        "// readings recorded while the broker is unreachable stay buffered and survive the \"cut\".\n"
        "package telemetry\n\n"
        "import (\n"
        "\t\"encoding/json\"\n"
        "\t\"fmt\"\n"
        "\t\"net\"\n\n"
        f"\t\"{module}/contract\"\n"
        ")\n\n"
        "type flushReq struct {\n"
        "\tOp       string             `json:\"op\"`\n"
        f"\tReadings []contract.{name} `json:\"readings\"`\n"
        "}\n\n"
        "type flushResp struct {\n"
        "\tOK    bool `json:\"ok\"`\n"
        "\tCount int  `json:\"count\"`\n"
        "}\n\n"
        "// Forwarder buffers readings (store-and-forward) and delivers them to the broker on Flush.\n"
        "type Forwarder struct {\n"
        "\tsock   string\n"
        f"\tbuffer []contract.{name}\n"
        "}\n\n"
        "func NewForwarder(sock string) *Forwarder { return &Forwarder{sock: sock} }\n\n"
        "// Record buffers a reading locally (no network — survives a broker outage).\n"
        f"func (f *Forwarder) Record(r contract.{name}) {{ f.buffer = append(f.buffer, r) }}\n\n"
        "// Pending is how many readings are buffered (not yet acknowledged by the broker).\n"
        "func (f *Forwarder) Pending() int { return len(f.buffer) }\n\n"
        "// Flush delivers the buffered readings to the live broker. On success it clears the buffer; on\n"
        "// failure (broker down) the buffer is RETAINED — nothing confirmed is lost (DES-4).\n"
        "func (f *Forwarder) Flush() error {\n"
        "\tconn, err := net.Dial(\"unix\", f.sock)\n"
        "\tif err != nil {\n"
        "\t\treturn err // broker down → buffer retained\n"
        "\t}\n"
        "\tdefer conn.Close()\n"
        "\tif err := json.NewEncoder(conn).Encode(flushReq{Op: \"flush\", Readings: f.buffer}); err != nil {\n"
        "\t\treturn err\n"
        "\t}\n"
        "\tvar resp flushResp\n"
        "\tif err := json.NewDecoder(conn).Decode(&resp); err != nil {\n"
        "\t\treturn err\n"
        "\t}\n"
        "\tif !resp.OK {\n"
        "\t\treturn fmt.Errorf(\"broker rejected the flush\")\n"
        "\t}\n"
        "\tf.buffer = nil\n"
        "\treturn nil\n"
        "}\n"
    )


def _live_test_go(msg: dict, module: str) -> str:
    name = msg["name"]
    s1 = '{DeviceID: "dev-1", Metric: "temp", Value: 21.5, TS: 1, FWVersion: "1.0.0"}'
    s2 = '{DeviceID: "dev-2", Metric: "temp", Value: 22.0, TS: 2, FWVersion: "1.0.0"}'
    return (
        "package telemetry\n\n"
        "import (\n"
        "\t\"os\"\n"
        "\t\"testing\"\n\n"
        f"\t\"{module}/contract\"\n"
        ")\n\n"
        "// brokerSock is the live broker's unix socket, shared with the broker via IOTGW_SOCK (set by the\n"
        "// infra_up `up`/`proof` wrappers, same cwd). Without it the round-trip is not meaningful → skip.\n"
        "func brokerSock(t *testing.T) string {\n"
        "\ts := os.Getenv(\"IOTGW_SOCK\")\n"
        "\tif s == \"\" {\n"
        "\t\tt.Skip(\"IOTGW_SOCK not set (this round-trip only runs under infra_up, against the live broker)\")\n"
        "\t}\n"
        "\treturn s\n"
        "}\n\n"
        "func TestStoreAndForwardAgainstLiveBroker(t *testing.T) {\n"
        "\tf := NewForwarder(brokerSock(t))\n"
        f"\tf.Record(contract.{name}{s1})\n"
        f"\tf.Record(contract.{name}{s2})\n"
        "\tif f.Pending() != 2 {\n"
        "\t\tt.Fatalf(\"store-and-forward: expected 2 buffered, got %d\", f.Pending())\n"
        "\t}\n"
        "\tif err := f.Flush(); err != nil {\n"
        "\t\tt.Fatalf(\"flush to the LIVE broker failed (broker down?): %v\", err)\n"
        "\t}\n"
        "\tif f.Pending() != 0 {\n"
        "\t\tt.Fatalf(\"buffer not cleared after a successful flush: %d still pending\", f.Pending())\n"
        "\t}\n"
        "}\n"
    )


def _broker_go(msg: dict, module: str) -> str:
    name = msg["name"]
    return (
        "// Command broker is the IoT telemetry broker (DES-9): a stdlib unix-socket server that ingests\n"
        "// store-and-forward batches, rejecting malformed readings at the edge (DES-6). No ports, no\n"
        "// external dependency — the Go analogue of full-stack's node:sqlite-over-socket and dummy's socket.\n"
        "package main\n\n"
        "import (\n"
        "\t\"encoding/json\"\n"
        "\t\"net\"\n"
        "\t\"os\"\n\n"
        f"\t\"{module}/contract\"\n"
        ")\n\n"
        "type flushReq struct {\n"
        "\tOp       string             `json:\"op\"`\n"
        f"\tReadings []contract.{name} `json:\"readings\"`\n"
        "}\n\n"
        "func main() {\n"
        "\tsock := os.Getenv(\"IOTGW_SOCK\")\n"
        "\tif sock == \"\" {\n"
        "\t\tsock = \"telemetry.sock\"\n"
        "\t}\n"
        "\tos.Remove(sock) // clear a stale socket (re-derivable, like full-stack's rmSync)\n"
        "\tln, err := net.Listen(\"unix\", sock)\n"
        "\tif err != nil {\n"
        "\t\tpanic(err)\n"
        "\t}\n"
        "\tdefer func() { ln.Close(); os.Remove(sock) }()\n"
        "\tos.Stdout.WriteString(\"BROKER_UP\\n\") // readiness marker (infra_up retries until reachable)\n\n"
        f"\tvar store []contract.{name}\n"
        "\tfor {\n"
        "\t\tconn, err := ln.Accept()\n"
        "\t\tif err != nil {\n"
        "\t\t\treturn\n"
        "\t\t}\n"
        "\t\thandle(conn, &store)\n"
        "\t}\n"
        "}\n\n"
        f"func handle(conn net.Conn, store *[]contract.{name}) {{\n"
        "\tdefer conn.Close()\n"
        "\tvar req flushReq\n"
        "\tif err := json.NewDecoder(conn).Decode(&req); err != nil {\n"
        "\t\treturn\n"
        "\t}\n"
        "\tif req.Op == \"flush\" {\n"
        "\t\tfor _, r := range req.Readings {\n"
        "\t\t\tif r.Validate() != nil {\n"
        "\t\t\t\tcontinue // reject malformed at the edge (DES-6)\n"
        "\t\t\t}\n"
        "\t\t\t*store = append(*store, r)\n"
        "\t\t}\n"
        "\t}\n"
        "\t_ = json.NewEncoder(conn).Encode(map[string]any{\"ok\": true, \"count\": len(*store)})\n"
        "}\n"
    )


def _go_mod(module: str) -> str:
    return f"module {module}\n\ngo 1.26\n"


def build_files(bp: dict) -> dict[str, str]:
    msg = bp["message"]
    module = bp["module_path"]
    return {
        "go.mod": _go_mod(module),
        "contract/message.go": _contract_go(msg),
        "contract/message_test.go": _contract_test_go(msg),
        "topology/topology.go": _topology_go(bp["topology"]),
        "topology/topology_test.go": _TOPOLOGY_TEST_GO,
        "ota/guard.go": _OTA_GO,
        "ota/guard_test.go": _OTA_TEST_GO,
        "provenance/trail.go": _provenance_go(bp, msg, module),
        "provenance/trail_test.go": _provenance_test_go(msg, module),
        "dedup/dedup.go": _dedup_go(bp, msg, module),
        "dedup/dedup_test.go": _dedup_test_go(msg, module),
        "telemetry/forward.go": _forward_go(msg, module),
        "telemetry/live_test.go": _live_test_go(msg, module),
        "cmd/broker/main.go": _broker_go(msg, module),
    }


def main(argv: list[str]) -> int:
    root = Path(os.environ.get("METAFACTORY_ROOT", ".")).resolve()
    bp = _load_blueprint(root)
    files = build_files(bp)
    if "--selftest" in argv:
        print(f"scaffold selftest OK: blueprint paquete={bp['package_name']} mensaje={bp['message']['name']} "
              f"campos={len(bp['message']['fields'])} tópicos={len(bp['topology']['topics'])} "
              f"→ {len(files)} archivos Go")
        return 0
    out = root / "build" / "product"
    for rel, content in files.items():
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
    # MANIFEST AL FINAL: es el keystone del slot generate (dest); su existencia == el scaffolder completó.
    (out / "MANIFEST.txt").write_text(
        "# gateway IoT en Go generado por scaffold_product.py (MAT-7)\n" + "\n".join(sorted(files)) + "\n",
        encoding="utf-8")
    print(f"scaffold: {len(files)} archivos Go emitidos en {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
