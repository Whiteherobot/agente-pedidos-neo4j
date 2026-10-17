"""Extrae de la consulta lo que el catálogo entiende: términos de producto,
categoría, ciudad, cantidad y si pide buena calificación."""
from dataclasses import dataclass, field

from .texto import NUMEROS, PALABRAS_VACIAS, formas, normalizar, palabras, singular

SINONIMOS = {
    "celular": "smartphone", "telefono": "smartphone", "movil": "smartphone",
    "portatil": "laptop", "computadora": "laptop", "notebook": "laptop",
    "audifono": "audifono", "auricular": "audifono", "parlante": "audio",
    "camara": "camara", "disco": "disco", "raton": "mouse",
}

# Sustantivos de producto que no siempre están en los nombres.
GENERICOS = {
    "laptop", "smartphone", "audifono", "mouse", "teclado", "monitor", "cable", "impresora",
    "router", "tablet", "webcam", "camara", "disco", "memoria", "ssd", "ram", "apple", "android",
}


@dataclass
class Entidades:
    terminos: list[str] = field(default_factory=list)
    categoria: str | None = None
    ciudad: str | None = None
    cantidad: int | None = None
    calificacion_alta: bool = False
    plantilla: str = ""


class Extractor:
    def __init__(self, nombres_productos: list[str], categorias: list[str], ciudades: list[str]):
        self.vocabulario = set(GENERICOS)
        for nombre in nombres_productos:
            for p in palabras(nombre):
                self.vocabulario.add(singular(p))
        self.vocabulario -= PALABRAS_VACIAS
        self.categorias = {normalizar(c): c for c in categorias}
        self.ciudades = {normalizar(c): c for c in ciudades}

    def _producto(self, palabra: str) -> str | None:
        """La forma de la palabra que está en el vocabulario (con sinónimos), o None."""
        for forma in formas(palabra):
            forma = SINONIMOS.get(forma, forma)
            if forma in self.vocabulario:
                return forma
        return None

    def _categoria(self, palabra: str) -> str | None:
        for clave, original in self.categorias.items():
            if palabra == clave or (len(palabra) >= 4 and clave.startswith(singular(palabra))):
                return original
        return None

    def extraer(self, consulta: str) -> Entidades:
        e = Entidades()
        ps = palabras(consulta)
        marcadores = []
        for i, p in enumerate(ps):
            producto = self._producto(p)
            siguiente = ps[i + 1] if i + 1 < len(ps) else ""
            es_numero = p.isdigit() or p in NUMEROS
            # Un número antes de un producto es la cantidad ("2 iphone 14"); después, es el modelo.
            if es_numero and e.cantidad is None and not siguiente.isdigit() and self._producto(siguiente):
                e.cantidad = int(p) if p.isdigit() else NUMEROS[p]
                marcadores.append("NUM")
            elif p in self.ciudades:
                e.ciudad = self.ciudades[p]
                marcadores.append("CIUDAD")
            elif self._categoria(p) and not producto:
                e.categoria = self._categoria(p)
                marcadores.append("CATEGORIA")
            elif producto:
                e.terminos.append(producto)
                if not marcadores or marcadores[-1] != "PRODUCTO":
                    marcadores.append("PRODUCTO")
            else:
                marcadores.append(p)
        texto = normalizar(consulta)
        e.calificacion_alta = "calificacion" in texto and any(w in texto for w in ("alta", "mejor", "buena"))
        e.terminos = list(dict.fromkeys(e.terminos))
        e.plantilla = " ".join(marcadores)
        return e
