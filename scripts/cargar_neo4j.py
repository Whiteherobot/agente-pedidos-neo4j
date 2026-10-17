"""Borra el grafo y lo vuelve a cargar desde data/ (lee NEO4J_* del entorno o de .env).

    python scripts/cargar_neo4j.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402

from agente.catalogo_neo4j import CatalogoNeo4j  # noqa: E402
from agente.datos import leer_productos, leer_vendedores  # noqa: E402

load_dotenv()
catalogo = CatalogoNeo4j(os.environ["NEO4J_URI"], os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", ""))
catalogo.cargar(leer_productos(), leer_vendedores())
print(f"{len(catalogo.productos())} productos, {len(catalogo.vendedores())} vendedores, "
      f"{len(catalogo.categorias())} categorías, {len(catalogo.ciudades())} ciudades")
catalogo.cerrar()
