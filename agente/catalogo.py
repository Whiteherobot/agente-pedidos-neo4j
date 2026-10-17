"""Contrato del catálogo y su versión en memoria.

`CatalogoNeo4j` cumple el mismo contrato contra la base de grafos; las pruebas
de contrato corren contra las dos.
"""
import threading
from collections import Counter
from datetime import datetime
from typing import Protocol

from .modelo import ErrorPedido, SinStock, LineaPedido, Pedido, Producto, ResumenCategoria, Vendedor
from .texto import normalizar

# Qué categorías complementan a cada una, en orden de preferencia.
COMPLEMENTOS = {
    "Electronica": ["Accesorios", "Audio", "Almacenamiento", "Componentes"],
    "Accesorios": ["Electronica", "Audio"],
    "Audio": ["Electronica", "Accesorios"],
    "Almacenamiento": ["Componentes", "Electronica"],
    "Componentes": ["Almacenamiento", "Electronica"],
    "Oficina": ["Accesorios", "Electronica"],
    "Redes": ["Accesorios", "Electronica"],
}

MAX_UNIDADES = 20


class Catalogo(Protocol):
    def productos(self) -> list[Producto]: ...
    def producto(self, producto_id: int) -> Producto | None: ...
    def buscar_productos(self, terminos: list[str], categoria: str | None = None,
                         ciudad: str | None = None, limite: int = 10) -> list[Producto]: ...
    def vendedores(self, terminos: list[str] | None = None, categoria: str | None = None,
                   ciudad: str | None = None, calificacion_minima: float | None = None) -> list[Vendedor]: ...
    def vendedor(self, vendedor_id: str) -> Vendedor | None: ...
    def categorias(self) -> list[ResumenCategoria]: ...
    def ciudades(self) -> list[str]: ...
    def recomendaciones(self, producto_id: int, limite: int = 3) -> list[Producto]: ...
    def crear_pedido(self, cliente: str, items: list[tuple[int, int]]) -> Pedido: ...
    def pedidos(self) -> list[Pedido]: ...


def texto_buscable(p: Producto) -> str:
    return normalizar(f"{p.nombre} {p.descripcion} {p.categoria}")


def validar_items(items: list[tuple[int, int]]) -> dict[int, int]:
    """Junta los productos repetidos y valida las cantidades."""
    if not items:
        raise ErrorPedido("El pedido no tiene productos")
    juntos: dict[int, int] = {}
    for producto_id, cantidad in items:
        if not isinstance(cantidad, int) or cantidad < 1:
            raise ErrorPedido("Cada cantidad tiene que ser un entero positivo")
        juntos[producto_id] = juntos.get(producto_id, 0) + cantidad
    for cantidad in juntos.values():
        if cantidad > MAX_UNIDADES:
            raise ErrorPedido(f"Máximo {MAX_UNIDADES} unidades por producto")
    return juntos


class CatalogoMemoria:
    def __init__(self, productos: list[Producto], vendedores: list[Vendedor]):
        self._productos = {p.id: p for p in productos}
        self._vendedores = {v.id: v for v in vendedores}
        self._pedidos: list[Pedido] = []
        self._candado = threading.Lock()

    def productos(self):
        return sorted(self._productos.values(), key=lambda p: p.id)

    def producto(self, producto_id):
        return self._productos.get(producto_id)

    def buscar_productos(self, terminos, categoria=None, ciudad=None, limite=10):
        candidatos = [
            p for p in self._productos.values()
            if (categoria is None or p.categoria == categoria) and (ciudad is None or p.ubicacion == ciudad)
        ]
        puntuados = []
        for p in candidatos:
            texto = texto_buscable(p)
            puntaje = sum(1 for t in terminos if t in texto)
            if puntaje or not terminos:
                puntuados.append((puntaje, p))
        puntuados.sort(key=lambda x: (-x[0], x[1].precio, x[1].id))
        return [p for _, p in puntuados[:limite]]

    def vendedores(self, terminos=None, categoria=None, ciudad=None, calificacion_minima=None):
        elegidos = [
            v for v in self._vendedores.values()
            if (ciudad is None or v.ciudad == ciudad)
            and (calificacion_minima is None or v.calificacion >= calificacion_minima)
        ]
        if terminos or categoria:
            # Vende algún producto que coincide, o lo dice su especialidad.
            con_productos = {p.vendedor_id for p in self.buscar_productos(terminos or [], categoria, limite=1000)}
            elegidos = [
                v for v in elegidos
                if v.id in con_productos or any(t in normalizar(v.especialidad) for t in terminos or [])
            ]
        return sorted(elegidos, key=lambda v: (-v.calificacion, v.id))

    def vendedor(self, vendedor_id):
        return self._vendedores.get(vendedor_id)

    def categorias(self):
        grupos: dict[str, list[Producto]] = {}
        for p in self._productos.values():
            grupos.setdefault(p.categoria, []).append(p)
        resumen = [
            ResumenCategoria(c, len(ps), min(p.precio for p in ps), max(p.precio for p in ps))
            for c, ps in grupos.items()
        ]
        return sorted(resumen, key=lambda r: (-r.cantidad, r.categoria))

    def ciudades(self):
        return sorted({p.ubicacion for p in self._productos.values()} | {v.ciudad for v in self._vendedores.values()})

    def recomendaciones(self, producto_id, limite=3):
        base = self._productos.get(producto_id)
        if base is None:
            return []
        # 1) Lo que otros compraron junto con este producto.
        juntos = Counter()
        for pedido in self._pedidos:
            ids = {linea.producto_id for linea in pedido.lineas}
            if producto_id in ids:
                juntos.update(ids - {producto_id})
        elegidos = [
            self._productos[i] for i, _ in sorted(juntos.items(), key=lambda x: (-x[1], x[0]))
            if self._productos[i].stock > 0
        ]
        # 2) Productos de categorías complementarias, primero del mismo vendedor.
        orden = COMPLEMENTOS.get(base.categoria, [])
        complementarios = sorted(
            (p for p in self._productos.values() if p.categoria in orden and p.stock > 0),
            key=lambda p: (orden.index(p.categoria), p.vendedor_id != base.vendedor_id, p.precio, p.id),
        )
        for p in complementarios:
            if p not in elegidos and p.id != producto_id:
                elegidos.append(p)
        return elegidos[:limite]

    def crear_pedido(self, cliente, items):
        juntos = validar_items(items)
        with self._candado:
            for producto_id, cantidad in juntos.items():
                p = self._productos.get(producto_id)
                if p is None:
                    raise ErrorPedido(f"No existe el producto {producto_id}")
                if p.stock < cantidad:
                    raise SinStock(f"Solo quedan {p.stock} unidades de {p.nombre}")
            lineas = []
            for producto_id, cantidad in juntos.items():
                p = self._productos[producto_id]
                self._productos[producto_id] = Producto(**{**p.__dict__, "stock": p.stock - cantidad})
                lineas.append(LineaPedido(p.id, p.nombre, cantidad, p.precio))
            pedido = Pedido(
                id=f"PED-{len(self._pedidos) + 1:05d}", cliente=cliente,
                fecha=datetime.now().isoformat(timespec="seconds"), lineas=lineas,
            )
            self._pedidos.append(pedido)
            return pedido

    def pedidos(self):
        return list(reversed(self._pedidos))
