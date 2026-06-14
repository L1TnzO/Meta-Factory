"""GENERADO por la fábrica {{slug}} — NO editar (se regenera en cada scaffold, frontera I-5).

El chasis es dueño de este archivo: el runner importa el módulo de DOMINIO ({{product_module}}, que
vive en domain/ y SOBREVIVE un re-scaffold) y expone run(). Una edición a mano acá se PIERDE al
re-renderizar — ese es justamente el contrato que boundary_survives verifica por bloqueo."""
from {{product_module}} import {{greet_fn}}


def run() -> str:
    return {{greet_fn}}()
