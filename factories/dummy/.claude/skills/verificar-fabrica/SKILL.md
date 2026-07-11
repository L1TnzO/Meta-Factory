---
name: verificar-fabrica
description: How to re-verify the factory by blocking (not by prose).
---

# verify — re-verify dummy by blocking
Run `meta product-run --factory dummy` and read the verdict bus (≤ max_lines), never the
test dump. The two verifiers: `meta ci --rederive --factory dummy`.
