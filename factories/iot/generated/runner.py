"""GENERADO por la fábrica iot — NO editar (se regenera en cada scaffold, frontera I-5).

El chasis es dueño de este archivo: el runner importa el módulo de DOMINIO (iotgw, que
vive en domain/ y SOBREVIVE un re-scaffold) y expone run(). Una edición a mano acá se PIERDE al
re-renderizar — ese es justamente el contrato que boundary_survives verifica por bloqueo."""
from iotgw import marker


def run() -> str:
    return marker()
