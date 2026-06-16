---
description: Corre el saludo del producto y verifica el marcador invariante.
run:
- python
- -c
- import sys; sys.path.insert(0, 'domain'); import greeting; assert greeting.greet()
  == 'DUMMY_OK'; print(greeting.greet())
---

# /greet — corré el producto de la fábrica dummy
Corré el saludo del producto y confirmá que devuelve el marcador invariante DUMMY_OK.
