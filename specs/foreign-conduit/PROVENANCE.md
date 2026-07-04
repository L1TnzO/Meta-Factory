# Spec AJENA · RealWorld «Conduit» — proveniencia (E1+D-8, COUNCIL-360 §6.4.4)

**Por qué esta**: D-8 (endogeneidad del benchmark) exige UNA spec escrita por un TERCERO — no por este
proyecto ni en su gramática. RealWorld/Conduit es la spec pública canónica para comparar stacks
(«the mother of all demo apps»): un clon de Medium con Users/Auth · Profiles(follow) · Articles(CRUD+
favorite) · Comments · Tags — ~5-6 entidades, dentro de la banda sweet-spot (5–8).

**Origen (verbatim, sin editar)**:
- Repo: `github.com/gothinkster/realworld` (MIT)
- Commit upstream pineado: `98f29fb3f8bcb1dd614b91f2851371bf22c34775`
- Ruta upstream: `docs/src/content/docs/specifications/backend/{introduction,endpoints,api-response-format,error-handling}.md`
- Descargado: 2026-07-04 vía `curl` (raw.githubusercontent.com), 434 líneas totales.

**Regla del experimento**: estos archivos NO se editan (cualquier traducción a `product.yml` vive en
OTRO archivo y se compara contra estos). Re-verificable:
`curl -sL https://raw.githubusercontent.com/gothinkster/realworld/98f29fb3f8bcb1dd614b91f2851371bf22c34775/docs/src/content/docs/specifications/backend/endpoints.md | diff - specs/foreign-conduit/endpoints.md`
