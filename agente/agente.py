"""El agente como grafo de LangGraph:

    interpretar -> enrutar -> ejecutar -> redactar
                         \\-> conversar (saludos)
                         \\-> aclarar   (similitud bajo el umbral)

Cada nodo deja un paso en la traza, que la página muestra.
"""
import time
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from .catalogo import Catalogo
from .entidades import Extractor
from .enrutador import UMBRAL, Enrutador
from .herramientas import HERRAMIENTAS
from .redaccion import Redactor

SALUDO = ("Hola. Puedo buscar productos y precios, ver el stock, comparar, recomendar, "
          "encontrar vendedores y armar su pedido. ¿Qué necesita?")


class Estado(TypedDict, total=False):
    consulta: str
    entidades: Any
    eleccion: Any
    resultado: dict
    respuesta: str
    origen: str
    traza: list


def _paso(estado: Estado, nombre: str, detalle: str, inicio: float) -> list:
    return [*estado.get("traza", []), {"paso": nombre, "detalle": detalle, "ms": round((time.perf_counter() - inicio) * 1000, 1)}]


class Agente:
    def __init__(self, catalogo: Catalogo, redactor: Redactor | None = None, usar_embeddings: bool | None = None):
        self.catalogo = catalogo
        self.extractor = Extractor(
            [p.nombre for p in catalogo.productos()],
            [c.categoria for c in catalogo.categorias()],
            catalogo.ciudades(),
        )
        self.enrutador = Enrutador(self.extractor, usar_embeddings)
        self.redactor = redactor or Redactor()
        self._grafo = self._construir()

    def _construir(self):
        g = StateGraph(Estado)
        g.add_node("interpretar", self._interpretar)
        g.add_node("enrutar", self._enrutar)
        g.add_node("ejecutar", self._ejecutar)
        g.add_node("redactar", self._redactar)
        g.add_node("conversar", self._conversar)
        g.add_node("aclarar", self._aclarar)
        g.set_entry_point("interpretar")
        g.add_edge("interpretar", "enrutar")
        g.add_conditional_edges("enrutar", self._siguiente, ["ejecutar", "conversar", "aclarar"])
        g.add_edge("ejecutar", "redactar")
        for final in ("redactar", "conversar", "aclarar"):
            g.add_edge(final, END)
        return g.compile()

    def _interpretar(self, estado: Estado):
        t = time.perf_counter()
        e = self.extractor.extraer(estado["consulta"])
        detalle = f"plantilla «{e.plantilla}»; términos {e.terminos or '-'}"
        if e.categoria:
            detalle += f"; categoría {e.categoria}"
        if e.ciudad:
            detalle += f"; ciudad {e.ciudad}"
        if e.cantidad:
            detalle += f"; cantidad {e.cantidad}"
        return {"entidades": e, "traza": _paso(estado, "interpretar", detalle, t)}

    def _enrutar(self, estado: Estado):
        t = time.perf_counter()
        el = self.enrutador.elegir(estado["entidades"].plantilla)
        top = ", ".join(f"{f} {s:.2f}" for f, s in list(el.puntajes.items())[:3])
        return {"eleccion": el, "traza": _paso(estado, "enrutar", f"{el.metodo}: {top}", t)}

    def _siguiente(self, estado: Estado) -> str:
        el = estado["eleccion"]
        if not el.segura:
            return "aclarar"
        return "conversar" if el.funcion == "saludo" else "ejecutar"

    def _ejecutar(self, estado: Estado):
        t = time.perf_counter()
        funcion = estado["eleccion"].funcion
        resultado = HERRAMIENTAS[funcion](self.catalogo, estado["entidades"])
        return {"resultado": resultado, "traza": _paso(estado, "ejecutar", f"{funcion}: {len(resultado['filas'])} fila(s)", t)}

    def _redactar(self, estado: Estado):
        t = time.perf_counter()
        texto, origen = self.redactor.redactar(estado["consulta"], estado["eleccion"].funcion, estado["resultado"])
        return {"respuesta": texto, "origen": origen, "traza": _paso(estado, "redactar", origen, t)}

    def _conversar(self, estado: Estado):
        return {"respuesta": SALUDO, "origen": "plantilla", "resultado": {"filas": []},
                "traza": _paso(estado, "conversar", "saludo", time.perf_counter())}

    def _aclarar(self, estado: Estado):
        el = estado["eleccion"]
        return {
            "respuesta": "No entendí bien la consulta. Pruebe con algo como «¿Cuánto cuesta el iPhone 15?» "
                         "o «¿Quién vende laptops en Lima?».",
            "origen": "plantilla", "resultado": {"filas": []},
            "traza": _paso(estado, "aclarar", f"similitud {el.similitud:.2f} < {UMBRAL}", time.perf_counter()),
        }

    def responder(self, consulta: str) -> dict:
        final = self._grafo.invoke({"consulta": consulta, "traza": []})
        el = final["eleccion"]
        resultado = final.get("resultado", {"filas": []})
        return {
            "consulta": consulta,
            "funcion": el.funcion if el.segura else None,
            "similitud": el.similitud,
            "respuesta": final["respuesta"],
            "origen": final["origen"],
            "filas": resultado.get("filas", []),
            "carrito": resultado.get("linea") if not resultado.get("sin_stock") else None,
            "traza": final["traza"],
        }
