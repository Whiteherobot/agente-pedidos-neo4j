"""Convierte el resultado de una herramienta en una respuesta en español.

Siempre hay una respuesta armada con plantillas a partir de los datos. Si hay
GEMINI_API_KEY, Gemini la reescribe en tono natural usando solo esos datos;
si falla o no hay clave, queda la de la plantilla.
"""
import json
import os

MODELO_GEMINI = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def _precio(valor: float) -> str:
    return f"${valor:,.2f}"


def _lista(filas, con_precio=True, con_stock=False, n=3):
    partes = []
    for f in filas[:n]:
        texto = f["nombre"]
        if con_precio:
            texto += f" a {_precio(f['precio'])}"
        if con_stock:
            texto += f" ({f['stock']} en stock)"
        partes.append(texto)
    return "; ".join(partes)


def plantilla(funcion: str, r: dict) -> str:
    filas = r.get("filas", [])
    falta = r.get("falta")
    if falta == "producto":
        return "¿Sobre qué producto? Por ejemplo: «¿Cuánto cuesta el iPhone 15?»."
    if falta == "ciudad":
        return f"¿En qué ciudad? Tenemos productos en {', '.join(r['ciudades'])}."
    if funcion == "comparar_precios" and falta:
        if filas:
            return f"Solo encontré {filas[0]['nombre']} a {_precio(filas[0]['precio'])}; nombre otro producto para comparar."
        return "No encontré productos para comparar."
    if not filas:
        return "No encontré nada que coincida en el catálogo."

    if funcion == "buscar_producto":
        partes = [f"{f['nombre']} a {_precio(f['precio'])} ({f['vendedor']}, {f['ubicacion']})" for f in filas[:3]]
        extra = f" y {len(filas) - 3} más" if len(filas) > 3 else ""
        return f"Encontré {'; '.join(partes)}{extra}."
    if funcion == "verificar_stock":
        p = filas[0]
        if p["stock"] == 0:
            return f"{p['nombre']} está agotado."
        return f"Quedan {p['stock']} unidades de {p['nombre']} ({_precio(p['precio'])}), en {p['ubicacion']}."
    if funcion == "comparar_precios":
        barato, caro = filas[0], filas[-1]
        return (f"El más barato es {barato['nombre']} ({_precio(barato['precio'])}) y el más caro "
                f"{caro['nombre']} ({_precio(caro['precio'])}): {_precio(r['diferencia'])} de diferencia.")
    if funcion == "buscar_vendedor":
        partes = [f"{v['nombre']} en {v['ciudad']} ({v['calificacion']}, {v['especialidad'].lower()})" for v in filas]
        return f"{'Vendedor' if len(filas) == 1 else 'Vendedores'}: {'; '.join(partes)}."
    if funcion == "crear_pedido":
        linea = r["linea"]
        if r.get("sin_stock"):
            return f"Solo quedan {filas[0]['stock']} unidades de {linea['nombre']}; no alcanza para {linea['cantidad']}."
        total = linea["cantidad"] * linea["precio"]
        return f"Agregué {linea['cantidad']} × {linea['nombre']} al carrito ({_precio(total)}). Confírmelo desde el carrito."
    if funcion == "consultar_categoria":
        if "categoria" in r:
            return f"En {r['categoria']} hay {len(filas)} productos: {_lista(filas, n=4)}."
        partes = [f"{c['categoria']} ({c['cantidad']}, de {_precio(c['precio_minimo'])} a {_precio(c['precio_maximo'])})" for c in filas]
        return f"Categorías: {'; '.join(partes)}."
    if funcion == "buscar_por_ubicacion":
        vendedores = f" Vendedores en la ciudad: {', '.join(r['vendedores'])}." if r["vendedores"] else ""
        return f"En {r['ciudad']} hay {len(filas)} productos, por ejemplo {_lista(filas)}.{vendedores}"
    if funcion == "obtener_recomendaciones":
        return f"Con {r['base']} le recomiendo: {_lista(filas)}."
    return f"Encontré {len(filas)} resultados."


class Redactor:
    def __init__(self, clave: str | None = None):
        clave = clave if clave is not None else os.getenv("GEMINI_API_KEY", "")
        self._cliente = None
        if clave:
            from google import genai
            self._cliente = genai.Client(api_key=clave)

    @property
    def usa_llm(self) -> bool:
        return self._cliente is not None

    def redactar(self, consulta: str, funcion: str, resultado: dict) -> tuple[str, str]:
        """Devuelve (respuesta, origen) donde origen es 'plantilla' o el modelo usado."""
        base = plantilla(funcion, resultado)
        if not self._cliente or not resultado.get("filas"):
            return base, "plantilla"
        prompt = (
            "Eres el asistente de una tienda de tecnología. Responde en español, en dos o tres "
            "oraciones, usando SOLO los datos de abajo; no inventes productos, precios ni stock.\n"
            f"Pregunta del cliente: {consulta}\n"
            f"Función ejecutada: {funcion}\n"
            f"Datos: {json.dumps(resultado, ensure_ascii=False)[:4000]}\n"
            f"Respuesta de referencia: {base}"
        )
        try:
            texto = self._cliente.models.generate_content(model=MODELO_GEMINI, contents=prompt).text
            return (texto.strip(), MODELO_GEMINI) if texto else (base, "plantilla")
        except Exception:
            return base, "plantilla (falló Gemini)"
