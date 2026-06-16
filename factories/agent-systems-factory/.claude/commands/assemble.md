---
description: Corre el producto (ensamble) y verifica el marcador invariante.
run:
- python
- -c
- import sys; sys.path.insert(0, 'domain'); import agent_system; assert agent_system.assemble()
  == 'AGENT_SYSTEM_OK'; print(agent_system.assemble())
---

# /assemble — corré el producto de la fábrica agent-systems-factory
Corré el ensamble del producto y confirmá que devuelve el marcador invariante AGENT_SYSTEM_OK.
