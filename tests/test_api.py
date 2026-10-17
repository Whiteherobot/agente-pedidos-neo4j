import pytest
from fastapi.testclient import TestClient

from agente.agente import Agente
from agente.redaccion import Redactor
from api.main import crear_app


@pytest.fixture
def cliente(memoria):
    return TestClient(crear_app(memoria, "memoria", Agente(memoria, Redactor(clave=""))))


def test_pagina_y_estado(cliente):
    assert "text/html" in cliente.get("/").headers["content-type"]
    assert cliente.get("/static/app.js").status_code == 200
    assert cliente.get("/api/estado").json() == {
        "catalogo": "memoria", "enrutador": "tf-idf de caracteres", "redaccion": "plantillas", "productos": 27}


def test_consulta(cliente):
    r = cliente.post("/api/consulta", json={"consulta": "¿Quién vende routers?"})
    assert r.status_code == 200
    assert r.json()["filas"][0]["nombre"] == "Vendedor C"
    assert cliente.post("/api/consulta", json={"consulta": ""}).status_code == 422


def test_pedido_usa_el_precio_del_catalogo(cliente):
    r = cliente.post("/api/pedidos", json={"cliente": "Ana", "items": [{"producto_id": 4, "cantidad": 2, "precio": 0.01}]})
    assert r.status_code == 201
    assert r.json()["total"] == 159.98
    assert cliente.get("/api/pedidos").json()[0]["id"] == "PED-00001"
    assert next(p for p in cliente.get("/api/productos").json() if p["id"] == 4)["stock"] == 98


@pytest.mark.parametrize("cuerpo, codigo", [
    ({"cliente": "Ana", "items": [{"producto_id": 20, "cantidad": 9}]}, 409),
    ({"cliente": "Ana", "items": [{"producto_id": 999, "cantidad": 1}]}, 400),
    ({"cliente": "Ana", "items": [{"producto_id": 1, "cantidad": 0}]}, 422),
    ({"cliente": "Ana", "items": []}, 422),
    ({"cliente": "", "items": [{"producto_id": 1, "cantidad": 1}]}, 422),
])
def test_pedidos_rechazados(cliente, cuerpo, codigo):
    assert cliente.post("/api/pedidos", json=cuerpo).status_code == codigo
