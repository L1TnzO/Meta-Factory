---
description: Verifies the product generator can assemble the line from the blueprint
  (selftest, writes nothing).
run:
- python
- codegen/scaffold_product.py
- --selftest
---

# /assemble — verify the agent-systems-factory product can be assembled
Run the scaffolder in selftest mode: it parses the spec's blueprint and confirms the LangGraph
line is ready to generate. The e2e product is built with `meta product-run`.
