import os

import pytest

from agente.catalogo import CatalogoMemoria
from agente.datos import leer_productos, leer_vendedores

NEO4J_URI = os.getenv("NEO4J_URI")


def _neo4j():
    from agente.catalogo_neo4j import CatalogoNeo4j
    c = CatalogoNeo4j(NEO4J_URI, os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", ""))
    c.cargar(leer_productos(), leer_vendedores())
    return c


@pytest.fixture(params=["memoria", "neo4j"])
def catalogo(request):
    """Las pruebas de contrato corren contra los dos catálogos (Neo4j si hay NEO4J_URI)."""
    if request.param == "memoria":
        yield CatalogoMemoria(leer_productos(), leer_vendedores())
        return
    if not NEO4J_URI:
        pytest.skip("sin NEO4J_URI")
    c = _neo4j()
    yield c
    c.cerrar()


@pytest.fixture
def memoria():
    return CatalogoMemoria(leer_productos(), leer_vendedores())
