import pytest

from agente.agente import Agente
from agente.redaccion import Redactor
from tests.consultas_etiquetadas import CONSULTAS


@pytest.fixture
def agente(memoria):
    return Agente(memoria, Redactor(clave=""))


def test_enruta_bien_preguntas_que_no_estan_en_los_ejemplos(agente):
    errores = []
    for consulta, esperada in CONSULTAS:
        e = agente.extractor.extraer(consulta)
        elegida = agente.enrutador.elegir(e.plantilla)
        if elegida.funcion != esperada or not elegida.segura:
            errores.append((consulta, elegida.funcion, esperada))
    assert len(errores) <= 2, errores


@pytest.mark.parametrize("consulta, terminos, categoria, ciudad, cantidad", [
    ("Quiero 2 iPhone 14 Pro", ["iphone", "14", "pro"], None, None, 2),
    ("¿Cuántos iPhone 14 hay disponibles?", ["iphone", "14"], None, None, None),
    ("¿Quién vende smartphones en Lima?", ["smartphone"], None, "Lima", None),
    ("Comprar tres cables HDMI", ["cable", "hdmi"], None, None, 3),
    ("¿Qué productos de Redes tienen?", [], "Redes", None, None),
    ("Busco un celular en Arequipa", ["smartphone"], None, "Arequipa", 1),
])
def test_extrae_entidades(agente, consulta, terminos, categoria, ciudad, cantidad):
    e = agente.extractor.extraer(consulta)
    assert (e.terminos, e.categoria, e.ciudad, e.cantidad) == (terminos, categoria, ciudad, cantidad)


def test_precio_de_un_producto(agente):
    r = agente.responder("¿Cuánto cuesta el iPhone 14?")
    assert r["funcion"] == "buscar_producto"
    assert r["filas"][0]["nombre"] == "iPhone 14 Pro"
    assert "$999.99" in r["respuesta"]
    assert [p["paso"] for p in r["traza"]] == ["interpretar", "enrutar", "ejecutar", "redactar"]


def test_stock(agente):
    r = agente.responder("¿Cuántas unidades quedan del Galaxy A54?")
    assert r["respuesta"].startswith("Quedan 60 unidades de Samsung Galaxy A54")


def test_compara_todos_los_que_coinciden(agente):
    r = agente.responder("¿Qué smartphone es más barato?")
    assert r["funcion"] == "comparar_precios"
    assert len(r["filas"]) == 9
    assert "Xiaomi Redmi Note 13 ($299.99)" in r["respuesta"]
    assert "$800.00 de diferencia" in r["respuesta"]


def test_vendedores_bien_calificados(agente):
    r = agente.responder("Vendedores con calificación alta")
    assert [v["id"] for v in r["filas"]] == ["C", "A"]


def test_el_pedido_por_chat_solo_propone_el_carrito(agente, memoria):
    r = agente.responder("Quiero 2 iPhone 14 Pro")
    assert r["funcion"] == "crear_pedido"
    assert r["carrito"] == {"producto_id": 2, "nombre": "iPhone 14 Pro", "cantidad": 2, "precio": 999.99}
    assert memoria.producto(2).stock == 50, "no compra sin confirmar"
    assert memoria.pedidos() == []


def test_no_propone_mas_de_lo_que_hay(agente):
    r = agente.responder("Quiero comprar 9 Laptop MSI Creator")
    assert r["carrito"] is None
    assert "Solo quedan 8" in r["respuesta"]


def test_pide_lo_que_falta(agente):
    assert agente.responder("¿Qué hay disponible?")["respuesta"].startswith("¿Sobre qué producto?")
    r = agente.responder("¿Qué venden en mi ciudad?")
    assert r["funcion"] == "buscar_por_ubicacion"
    assert "Arequipa, Cusco, Lima" in r["respuesta"]


def test_saludo_y_consulta_sin_sentido(agente):
    assert agente.responder("Buenos días")["funcion"] == "saludo"
    r = agente.responder("zxcv qwerty")
    assert r["funcion"] is None
    assert r["traza"][-1]["paso"] == "aclarar"


def test_recomendaciones(agente):
    r = agente.responder("¿Qué me recomiendas con el iPhone 15?")
    assert r["respuesta"].startswith("Con iPhone 15 le recomiendo")
    assert len(r["filas"]) == 3


def test_si_gemini_falla_queda_la_plantilla(memoria):
    class Roto:
        class models:
            @staticmethod
            def generate_content(**_):
                raise RuntimeError("sin red")

    redactor = Redactor(clave="")
    redactor._cliente = Roto()
    r = Agente(memoria, redactor).responder("¿Cuánto cuesta el iPhone 14?")
    assert r["origen"] == "plantilla (falló Gemini)"
    assert "$999.99" in r["respuesta"]
