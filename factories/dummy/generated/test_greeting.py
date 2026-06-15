"""GENERADO por la fábrica dummy — el test del PRODUCTO, corre en SU PROPIO toolchain (C3, DES-8).

Lo ejecuta la estación s02 (`product_env`) dentro del venv del producto, AISLADO del de la fábrica
(PYTHONPATH scrubbed): por eso sólo importa el módulo de DOMINIO (greeting), nunca `metafactory`. Si el
marcador invariante se corrompe, este unittest sale ≠0 y la columna bloquea por exit code (no por prosa).
El chasis es dueño de este archivo (frontera I-5): se re-renderiza en cada scaffold."""
import unittest

from greeting import greet


class TestGreetingMarker(unittest.TestCase):
    def test_marker(self):
        self.assertEqual(greet(), "DUMMY_OK")


if __name__ == "__main__":
    unittest.main()
