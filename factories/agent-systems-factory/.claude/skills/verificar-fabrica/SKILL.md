---
name: verificar-fabrica
description: How to re-verify the factory by blocking (not by prose).
---

# verify — re-verify agent-systems-factory by blocking
Run `meta product-run --factory agent-systems-factory` and read the verdict bus, never the test dump.
The two verifiers: `meta ci --rederive --factory agent-systems-factory`.
