"""API y página del agente.

    uvicorn api.main:crear_app --factory --reload

Con NEO4J_URI (y NEO4J_USER / NEO4J_PASSWORD) usa el grafo en Neo4j y lo carga
desde data/ si está vacío; sin NEO4J_URI trabaja con el catálogo en memoria.
"""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agente.agente import Agente
from agente.catalogo import MAX_UNIDADES, CatalogoMemoria
from agente.datos import leer_productos, leer_vendedores
from agente.modelo import ErrorPedido, SinStock

FRONT = Path(__file__).resolve().parents[1] / "front"
log = logging.getLogger("agente")


class Consulta(BaseModel):
    consulta: str = Field(min_length=1, max_length=300)


class ItemPedido(BaseModel):
    producto_id: int
    cantidad: int = Field(ge=1, le=MAX_UNIDADES)


class NuevoPedido(BaseModel):
    cliente: str = Field(min_length=2, max_length=80)
    items: list[ItemPedido] = Field(min_length=1)


def catalogo_por_entorno():
    uri = os.getenv("NEO4J_URI")
    if not uri:
        return CatalogoMemoria(leer_productos(), leer_vendedores()), "memoria"
    from agente.catalogo_neo4j import CatalogoNeo4j
    catalogo = CatalogoNeo4j(uri, os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", ""))
    if not catalogo.productos():
        log.info("grafo vacío: se carga desde data/")
        catalogo.cargar(leer_productos(), leer_vendedores())
    return catalogo, "neo4j"


def pedido_json(p):
    return {
        "id": p.id, "cliente": p.cliente, "fecha": p.fecha, "total": p.total,
        "lineas": [{**l.__dict__, "subtotal": l.subtotal} for l in p.lineas],
    }


def crear_app(catalogo=None, origen: str = "memoria", agente: Agente | None = None) -> FastAPI:
    if catalogo is None:
        load_dotenv()
        catalogo, origen = catalogo_por_entorno()
    agente = agente or Agente(catalogo)

    app = FastAPI(title="Agente de pedidos")

    @app.get("/api/estado")
    def estado():
        return {
            "catalogo": origen,
            "enrutador": agente.enrutador.metodo,
            "redaccion": "Gemini" if agente.redactor.usa_llm else "plantillas",
            "productos": len(catalogo.productos()),
        }

    @app.post("/api/consulta")
    def consultar(c: Consulta):
        return agente.responder(c.consulta)

    @app.get("/api/productos")
    def productos():
        return [p.__dict__ for p in catalogo.productos()]

    @app.get("/api/pedidos")
    def pedidos():
        return [pedido_json(p) for p in catalogo.pedidos()]

    @app.post("/api/pedidos", status_code=201)
    def crear_pedido(nuevo: NuevoPedido):
        # El precio sale del catálogo, nunca del navegador.
        try:
            pedido = catalogo.crear_pedido(nuevo.cliente.strip(), [(i.producto_id, i.cantidad) for i in nuevo.items])
        except SinStock as e:
            raise HTTPException(409, str(e)) from e
        except ErrorPedido as e:
            raise HTTPException(400, str(e)) from e
        return pedido_json(pedido)

    app.mount("/static", StaticFiles(directory=FRONT), name="static")

    @app.get("/", include_in_schema=False)
    def inicio():
        return FileResponse(FRONT / "index.html")

    return app

