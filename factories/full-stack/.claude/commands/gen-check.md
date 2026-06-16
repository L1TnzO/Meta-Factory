---
description: Corre el selftest del codegen del producto (parsea el blueprint, lista
  los archivos; no escribe).
run:
- python
- codegen/scaffold_product.py
- --selftest
---

# /gen-check — verificá el codegen de la fábrica full-stack
Corré el selftest del scaffolder: parsea el blueprint (domain.product) y lista los archivos del
producto que emitiría. Exit 0 = el generador es invocable y el blueprint está completo.
