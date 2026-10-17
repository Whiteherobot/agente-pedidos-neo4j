from dataclasses import dataclass, field


@dataclass(frozen=True)
class Vendedor:
    id: str
    nombre: str
    email: str
    ciudad: str
    calificacion: float
    productos_vendidos: int
    especialidad: str


@dataclass(frozen=True)
class Producto:
    id: int
    nombre: str
    categoria: str
    precio: float
    stock: int
    vendedor_id: str
    ubicacion: str
    descripcion: str


@dataclass(frozen=True)
class ResumenCategoria:
    categoria: str
    cantidad: int
    precio_minimo: float
    precio_maximo: float


@dataclass(frozen=True)
class LineaPedido:
    producto_id: int
    producto: str
    cantidad: int
    precio_unitario: float

    @property
    def subtotal(self) -> float:
        return round(self.cantidad * self.precio_unitario, 2)


@dataclass(frozen=True)
class Pedido:
    id: str
    cliente: str
    fecha: str
    lineas: list[LineaPedido] = field(default_factory=list)

    @property
    def total(self) -> float:
        return round(sum(linea.subtotal for linea in self.lineas), 2)


class ErrorPedido(ValueError):
    """Pedido inválido: sin productos, cantidad fuera de rango o producto inexistente."""


class SinStock(ErrorPedido):
    """No hay unidades suficientes de algún producto."""
