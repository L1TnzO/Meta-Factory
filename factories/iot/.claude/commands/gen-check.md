---
description: Runs the product codegen selftest (parses the blueprint, lists the files;
  writes nothing).
run:
- python
- codegen/scaffold_product.py
- --selftest
---

# /gen-check — verify the iot factory's codegen
Run the scaffolder selftest: it parses the blueprint (domain.product) and lists the Go product
files it would emit. Exit 0 = the generator is invocable and the blueprint is complete.
