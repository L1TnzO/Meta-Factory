---
name: verificar-fabrica
description: How to re-verify the factory by blocking (not by prose).
---

# verify — re-verify iot by blocking
Run `meta product-run --factory iot` and read the verdict bus (≤ max_lines), never the
test dump. The two verifiers: `meta ci --rederive --factory iot`.
