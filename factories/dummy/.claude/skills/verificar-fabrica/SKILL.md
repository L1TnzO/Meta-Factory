---
name: verificar-fabrica
description: Cómo re-verificar la fábrica por bloqueo (no por prosa).
---

# verificar — re-verificá dummy por bloqueo
Corré `meta product-run --factory dummy` y leé el bus de veredictos (≤ max_lines), nunca el
dump de tests. Los dos verificadores: `meta ci --rederive --factory dummy`.
