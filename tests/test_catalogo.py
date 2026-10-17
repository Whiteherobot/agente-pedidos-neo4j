import threading

import pytest

from agente.modelo import ErrorPedido, SinStock


def nombres(productos):
    return [p.nombre for p in productos]


def test_carga_todo_el_catalogo(catalogo):
    productos = catalogo.productos()
    assert len(productos) == 27
    assert productos[1].nombre == "iPhone 14 Pro"
    assert productos[1].vendedor_id == "B"
    assert catalogo.ciudades() == ["Arequipa", "Cusco", "Lima"]


def test_busca_por_terminos_ordenando_por_coincidencias_y_precio(catalogo):
    assert nombres(catalogo.buscar_productos(["iphone", "14"], limite=3)) == ["iPhone 14 Pro", "iPhone 13", "iPhone 15"]
    assert nombres(catalogo.buscar_productos(["hdmi"])) == ["Cable HDMI 2.1"]
    assert catalogo.buscar_productos(["inexistente"]) == []


def test_filtra_por_categoria_y_ciudad(catalogo):
    en_cusco = catalogo.buscar_productos([], ciudad="Cusco", limite=50)
    assert {p.ubicacion for p in en_cusco} == {"Cusco"}
    assert len(en_cusco) == 5
    assert nombres(catalogo.buscar_productos([], categoria="Audio")) == ["Audifonos Sony WH-1000XM5"]
    assert nombres(catalogo.buscar_productos(["smartphone"], categoria="Electronica", ciudad="Arequipa")) == [
        "iPhone 13", "Samsung Galaxy S23", "Samsung Galaxy S24"]


def test_vendedores_por_ciudad_calificacion_y_lo_que_venden(catalogo):
    assert [v.id for v in catalogo.vendedores()] == ["C", "A", "B"]
    assert [v.id for v in catalogo.vendedores(ciudad="Lima")] == ["A", "B"]
    assert [v.id for v in catalogo.vendedores(calificacion_minima=4.7)] == ["C", "A"]
    assert [v.id for v in catalogo.vendedores(["router"])] == ["C"]
    assert [v.id for v in catalogo.vendedores(categoria="Audio")] == ["B"]
    assert [v.id for v in catalogo.vendedores(["redes"])] == ["C"], "por especialidad"


def test_resumen_de_categorias(catalogo):
    resumen = catalogo.categorias()
    assert resumen[0].categoria == "Electronica"
    assert resumen[0].cantidad == 18
    assert (resumen[0].precio_minimo, resumen[0].precio_maximo) == (299.99, 1999.99)
    assert sum(r.cantidad for r in resumen) == 27


def test_pedido_con_precio_del_catalogo_y_descuento_de_stock(catalogo):
    pedido = catalogo.crear_pedido("Ana", [(2, 2), (14, 3), (2, 1)])
    assert pedido.id == "PED-00001"
    assert [(l.producto, l.cantidad, l.precio_unitario) for l in pedido.lineas] == [
        ("iPhone 14 Pro", 3, 999.99), ("Cable HDMI 2.1", 3, 19.99)]
    assert pedido.total == 3059.94
    assert catalogo.producto(2).stock == 47
    assert catalogo.crear_pedido("Luis", [(4, 1)]).id == "PED-00002"
    assert [p.id for p in catalogo.pedidos()] == ["PED-00002", "PED-00001"]


def test_pedido_sin_stock_no_descuenta_nada(catalogo):
    with pytest.raises(SinStock, match="Solo quedan 8"):
        catalogo.crear_pedido("Ana", [(1, 1), (20, 9)])
    assert catalogo.producto(1).stock == 25
    assert catalogo.pedidos() == []


@pytest.mark.parametrize("items", [[], [(1, 0)], [(1, 21)], [(999, 1)]])
def test_pedidos_invalidos(catalogo, items):
    with pytest.raises(ErrorPedido):
        catalogo.crear_pedido("Ana", items)


def test_pedidos_simultaneos_no_venden_de_mas(catalogo):
    # MSI Creator 15 tiene 8 unidades; 12 clientes piden 1 a la vez.
    resultados = []

    def comprar(i):
        try:
            catalogo.crear_pedido(f"cliente {i}", [(20, 1)])
            resultados.append("ok")
        except SinStock:
            resultados.append("sin stock")

    hilos = [threading.Thread(target=comprar, args=(i,)) for i in range(12)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert resultados.count("ok") == 8
    assert catalogo.producto(20).stock == 0


def test_recomienda_complementos_y_luego_lo_comprado_junto(catalogo):
    # Sin pedidos: categorías complementarias, primero del mismo vendedor (A).
    assert nombres(catalogo.recomendaciones(1)) == ["Mouse Logitech MX", "Teclado Mecanico", "Cable HDMI 2.1"]
    catalogo.crear_pedido("Ana", [(1, 1), (7, 1)])
    catalogo.crear_pedido("Luis", [(1, 1), (7, 1), (10, 1)])
    assert nombres(catalogo.recomendaciones(1)) == ["Audifonos Sony WH-1000XM5", "SSD Samsung 1TB", "Mouse Logitech MX"]
    assert catalogo.recomendaciones(999) == []
