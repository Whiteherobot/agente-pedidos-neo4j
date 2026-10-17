"""Lectura de los CSV del catálogo."""
import csv
from pathlib import Path

from .modelo import Producto, Vendedor

CARPETA = Path(__file__).resolve().parents[1] / "data"


def leer_vendedores(carpeta: Path = CARPETA) -> list[Vendedor]:
    with open(carpeta / "dataset_vendedores.csv", encoding="utf-8") as f:
        return [
            Vendedor(
                id=fila["id"], nombre=fila["nombre"], email=fila["email"], ciudad=fila["ciudad"],
                calificacion=float(fila["calificacion"]), productos_vendidos=int(fila["productos_vendidos"]),
                especialidad=fila["especialidad"],
            )
            for fila in csv.DictReader(f)
        ]


def leer_productos(carpeta: Path = CARPETA) -> list[Producto]:
    # En el CSV el vendedor aparece como "Vendedor A"; se guarda su id ("A").
    with open(carpeta / "dataset_transaccional.csv", encoding="utf-8") as f:
        return [
            Producto(
                id=int(fila["id"]), nombre=fila["nombre"], categoria=fila["categoria"],
                precio=float(fila["precio"]), stock=int(fila["stock"]),
                vendedor_id=fila["vendedor"].removeprefix("Vendedor ").strip(),
                ubicacion=fila["ubicacion"], descripcion=fila["descripcion"],
            )
            for fila in csv.DictReader(f)
        ]
