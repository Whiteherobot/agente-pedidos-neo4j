"""Lo que ejecuta cada función de la tabla contra el catálogo.

Cada herramienta devuelve un dict con `filas` (lo que se muestra) y los datos
que necesita la respuesta. Si falta algo para responder, lo dice en `falta`.
"""
from .catalogo import Catalogo
from .entidades import Entidades
from .modelo import Producto

CALIFICACION_ALTA = 4.7


def fila_producto(catalogo: Catalogo, p: Producto) -> dict:
    vendedor = catalogo.vendedor(p.vendedor_id)
    return {
        "id": p.id, "nombre": p.nombre, "categoria": p.categoria, "precio": p.precio,
        "stock": p.stock, "vendedor": vendedor.nombre if vendedor else p.vendedor_id, "ubicacion": p.ubicacion,
    }


def _buscar(catalogo, e: Entidades, limite=5):
    return catalogo.buscar_productos(e.terminos, e.categoria, e.ciudad, limite)


def buscar_producto(catalogo, e):
    if not (e.terminos or e.categoria or e.ciudad):
        return {"filas": [], "falta": "producto"}
    return {"filas": [fila_producto(catalogo, p) for p in _buscar(catalogo, e)]}


def verificar_stock(catalogo, e):
    if not e.terminos:
        return {"filas": [], "falta": "producto"}
    return {"filas": [fila_producto(catalogo, p) for p in _buscar(catalogo, e, 3)]}


def comparar_precios(catalogo, e):
    productos = sorted(_buscar(catalogo, e, 100), key=lambda p: (p.precio, p.id))
    if len(productos) < 2:
        return {"filas": [fila_producto(catalogo, p) for p in productos], "falta": "dos productos para comparar"}
    return {
        "filas": [fila_producto(catalogo, p) for p in productos],
        "diferencia": round(productos[-1].precio - productos[0].precio, 2),
    }


def buscar_vendedor(catalogo, e):
    minima = CALIFICACION_ALTA if e.calificacion_alta else None
    vendedores = catalogo.vendedores(e.terminos, e.categoria, e.ciudad, minima)
    return {"filas": [v.__dict__ for v in vendedores]}


def crear_pedido(catalogo, e):
    """No compra: propone la línea para el carrito; el pedido se confirma aparte."""
    if not e.terminos:
        return {"filas": [], "falta": "producto"}
    productos = _buscar(catalogo, e, 1)
    if not productos:
        return {"filas": []}
    p = productos[0]
    cantidad = e.cantidad or 1
    linea = {"producto_id": p.id, "nombre": p.nombre, "cantidad": cantidad, "precio": p.precio}
    if p.stock < cantidad:
        return {"filas": [fila_producto(catalogo, p)], "sin_stock": True, "linea": linea}
    return {"filas": [fila_producto(catalogo, p)], "linea": linea}


def consultar_categoria(catalogo, e):
    if e.categoria:
        productos = catalogo.buscar_productos([], e.categoria, e.ciudad, 50)
        return {"filas": [fila_producto(catalogo, p) for p in productos], "categoria": e.categoria}
    return {"filas": [r.__dict__ for r in catalogo.categorias()]}


def buscar_por_ubicacion(catalogo, e):
    if not e.ciudad:
        return {"filas": [], "falta": "ciudad", "ciudades": catalogo.ciudades()}
    productos = catalogo.buscar_productos(e.terminos, e.categoria, e.ciudad, 50)
    vendedores = catalogo.vendedores(ciudad=e.ciudad)
    return {
        "filas": [fila_producto(catalogo, p) for p in productos],
        "ciudad": e.ciudad, "vendedores": [v.nombre for v in vendedores],
    }


def obtener_recomendaciones(catalogo, e):
    if not e.terminos:
        return {"filas": [], "falta": "producto"}
    base = _buscar(catalogo, e, 1)
    if not base:
        return {"filas": []}
    sugeridos = catalogo.recomendaciones(base[0].id, 3)
    return {"filas": [fila_producto(catalogo, p) for p in sugeridos], "base": base[0].nombre}


HERRAMIENTAS = {
    "buscar_producto": buscar_producto,
    "buscar_vendedor": buscar_vendedor,
    "verificar_stock": verificar_stock,
    "comparar_precios": comparar_precios,
    "crear_pedido": crear_pedido,
    "consultar_categoria": consultar_categoria,
    "buscar_por_ubicacion": buscar_por_ubicacion,
    "obtener_recomendaciones": obtener_recomendaciones,
}
