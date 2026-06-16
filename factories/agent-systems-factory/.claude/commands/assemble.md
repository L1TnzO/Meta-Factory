---
description: Verifica que el generador del producto puede ensamblar la línea desde
  el blueprint (selftest, no escribe).
run:
- python
- codegen/scaffold_product.py
- --selftest
---

# /assemble — verificá que el producto de agent-systems-factory se puede ensamblar
Corré el scaffolder en modo selftest: parsea el blueprint del spec y confirma que la línea
LangGraph está lista para generarse. El producto e2e se construye con `meta product-run`.
