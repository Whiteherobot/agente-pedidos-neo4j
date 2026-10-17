"""El catálogo como grafo en Neo4j.

(:Producto)-[:VENDIDO_POR]->(:Vendedor)-[:UBICADO_EN]->(:Ciudad)
(:Producto)-[:EN_CATEGORIA]->(:Categoria)
(:Producto)-[:ALMACENADO_EN]->(:Ciudad)
(:Pedido)-[:INCLUYE {cantidad, precio_unitario}]->(:Producto)
"""
from datetime import datetime

from neo4j import GraphDatabase

from .catalogo import COMPLEMENTOS, texto_buscable, validar_items
from .modelo import ErrorPedido, SinStock, LineaPedido, Pedido, Producto, ResumenCategoria, Vendedor

_PRODUCTO = """
p {.id, .nombre, .precio, .stock, .descripcion,
   categoria: [(p)-[:EN_CATEGORIA]->(c) | c.nombre][0],
   vendedor_id: [(p)-[:VENDIDO_POR]->(v) | v.id][0],
   ubicacion: [(p)-[:ALMACENADO_EN]->(u) | u.nombre][0]} AS p
"""


def _producto(d) -> Producto:
    return Producto(
        id=d["id"], nombre=d["nombre"], categoria=d["categoria"], precio=d["precio"], stock=d["stock"],
        vendedor_id=d["vendedor_id"], ubicacion=d["ubicacion"], descripcion=d["descripcion"],
    )


def _vendedor(d) -> Vendedor:
    return Vendedor(**d)


class CatalogoNeo4j:
    def __init__(self, uri: str, usuario: str, clave: str):
        self._driver = GraphDatabase.driver(uri, auth=(usuario, clave))
        self._driver.verify_connectivity()

    def cerrar(self):
        self._driver.close()

    def _leer(self, cypher, **params):
        registros, _, _ = self._driver.execute_query(cypher, params, routing_="r")
        return registros

    def cargar(self, productos: list[Producto], vendedores: list[Vendedor]):
        """Borra todo y vuelve a crear el grafo desde los datos."""
        with self._driver.session() as s:
            s.run("MATCH (n) DETACH DELETE n").consume()
            for consulta in (
                "CREATE CONSTRAINT producto_id IF NOT EXISTS FOR (p:Producto) REQUIRE p.id IS UNIQUE",
                "CREATE CONSTRAINT vendedor_id IF NOT EXISTS FOR (v:Vendedor) REQUIRE v.id IS UNIQUE",
                "CREATE CONSTRAINT pedido_id IF NOT EXISTS FOR (p:Pedido) REQUIRE p.id IS UNIQUE",
            ):
                s.run(consulta).consume()
            s.run("CREATE (:Contador {nombre: 'pedido', valor: 0})").consume()
            s.run("""
                UNWIND $filas AS f
                MERGE (c:Ciudad {nombre: f.ciudad})
                CREATE (v:Vendedor {id: f.id, nombre: f.nombre, email: f.email, ciudad: f.ciudad,
                        calificacion: f.calificacion, productos_vendidos: f.productos_vendidos,
                        especialidad: f.especialidad})-[:UBICADO_EN]->(c)
            """, filas=[v.__dict__ for v in vendedores]).consume()
            s.run("""
                UNWIND $filas AS f
                MATCH (v:Vendedor {id: f.vendedor_id})
                MERGE (c:Categoria {nombre: f.categoria})
                MERGE (u:Ciudad {nombre: f.ubicacion})
                CREATE (p:Producto {id: f.id, nombre: f.nombre, precio: f.precio, stock: f.stock,
                        descripcion: f.descripcion, texto: f.texto})
                CREATE (p)-[:VENDIDO_POR]->(v), (p)-[:EN_CATEGORIA]->(c), (p)-[:ALMACENADO_EN]->(u)
            """, filas=[{**p.__dict__, "texto": texto_buscable(p)} for p in productos]).consume()

    def productos(self):
        return [_producto(r["p"]) for r in self._leer(f"MATCH (p:Producto) RETURN {_PRODUCTO} ORDER BY p.id")]

    def producto(self, producto_id):
        r = self._leer(f"MATCH (p:Producto {{id: $id}}) RETURN {_PRODUCTO}", id=producto_id)
        return _producto(r[0]["p"]) if r else None

    def buscar_productos(self, terminos, categoria=None, ciudad=None, limite=10):
        # Mismo puntaje que en memoria: cuántos términos aparecen en el texto del producto.
        registros = self._leer(f"""
            MATCH (p:Producto)-[:EN_CATEGORIA]->(c), (p)-[:ALMACENADO_EN]->(u)
            WHERE ($categoria IS NULL OR c.nombre = $categoria) AND ($ciudad IS NULL OR u.nombre = $ciudad)
            WITH p, size([t IN $terminos WHERE p.texto CONTAINS t]) AS puntaje
            WHERE puntaje > 0 OR size($terminos) = 0
            RETURN {_PRODUCTO} ORDER BY puntaje DESC, p.precio, p.id LIMIT $limite
        """, terminos=terminos, categoria=categoria, ciudad=ciudad, limite=limite)
        return [_producto(r["p"]) for r in registros]

    def vendedores(self, terminos=None, categoria=None, ciudad=None, calificacion_minima=None):
        terminos = terminos or []
        filtra = bool(terminos or categoria)
        registros = self._leer("""
            MATCH (v:Vendedor)
            WHERE ($ciudad IS NULL OR v.ciudad = $ciudad)
              AND ($minima IS NULL OR v.calificacion >= $minima)
              AND (NOT $filtra
                   OR any(t IN $terminos WHERE toLower(v.especialidad) CONTAINS t)
                   OR EXISTS {
                     MATCH (p:Producto)-[:VENDIDO_POR]->(v), (p)-[:EN_CATEGORIA]->(c)
                     WHERE ($categoria IS NULL OR c.nombre = $categoria)
                       AND (size($terminos) = 0 OR any(t IN $terminos WHERE p.texto CONTAINS t))
                   })
            RETURN v {.id, .nombre, .email, .ciudad, .calificacion, .productos_vendidos, .especialidad} AS v
            ORDER BY v.calificacion DESC, v.id
        """, terminos=terminos, categoria=categoria, ciudad=ciudad, minima=calificacion_minima, filtra=filtra)
        return [_vendedor(r["v"]) for r in registros]

    def vendedor(self, vendedor_id):
        r = self._leer("""
            MATCH (v:Vendedor {id: $id})
            RETURN v {.id, .nombre, .email, .ciudad, .calificacion, .productos_vendidos, .especialidad} AS v
        """, id=vendedor_id)
        return _vendedor(r[0]["v"]) if r else None

    def categorias(self):
        registros = self._leer("""
            MATCH (c:Categoria)<-[:EN_CATEGORIA]-(p)
            RETURN c.nombre AS categoria, count(p) AS cantidad, min(p.precio) AS minimo, max(p.precio) AS maximo
            ORDER BY cantidad DESC, categoria
        """)
        return [ResumenCategoria(r["categoria"], r["cantidad"], r["minimo"], r["maximo"]) for r in registros]

    def ciudades(self):
        return [r["n"] for r in self._leer("MATCH (c:Ciudad) RETURN c.nombre AS n ORDER BY n")]

    def recomendaciones(self, producto_id, limite=3):
        base = self.producto(producto_id)
        if base is None:
            return []
        juntos = self._leer(f"""
            MATCH (b:Producto {{id: $id}})<-[:INCLUYE]-(:Pedido)-[:INCLUYE]->(p:Producto)
            WHERE p <> b AND p.stock > 0
            WITH p, count(*) AS veces
            RETURN {_PRODUCTO} ORDER BY veces DESC, p.id
        """, id=producto_id)
        orden = COMPLEMENTOS.get(base.categoria, [])
        complementarios = self._leer(f"""
            MATCH (p:Producto)-[:EN_CATEGORIA]->(c), (p)-[:VENDIDO_POR]->(v)
            WHERE c.nombre IN $orden AND p.stock > 0 AND p.id <> $id
            WITH p, [i IN range(0, size($orden) - 1) WHERE $orden[i] = c.nombre][0] AS prioridad,
                 v.id <> $vendedor AS otro_vendedor
            RETURN {_PRODUCTO} ORDER BY prioridad, otro_vendedor, p.precio, p.id
        """, orden=orden, id=producto_id, vendedor=base.vendedor_id)
        elegidos: list[Producto] = []
        for r in [*juntos, *complementarios]:
            p = _producto(r["p"])
            if p not in elegidos:
                elegidos.append(p)
        return elegidos[:limite]

    def crear_pedido(self, cliente, items):
        juntos = validar_items(items)

        def transaccion(tx):
            filas = [{"id": i, "cantidad": c} for i, c in juntos.items()]
            existentes = tx.run("""
                UNWIND $filas AS f
                OPTIONAL MATCH (p:Producto {id: f.id})
                RETURN f.id AS id, f.cantidad AS cantidad, p.nombre AS nombre, p.stock AS stock, p.precio AS precio
            """, filas=filas).data()
            for e in existentes:
                if e["nombre"] is None:
                    raise ErrorPedido(f"No existe el producto {e['id']}")
                if e["stock"] < e["cantidad"]:
                    raise SinStock(f"Solo quedan {e['stock']} unidades de {e['nombre']}")
            # Primero se bloquea el contador (escribiendo en él) y después se lee;
            # leer antes del bloqueo deja que dos pedidos saquen el mismo número.
            numero = tx.run("""
                MATCH (c:Contador {nombre: 'pedido'})
                SET c.bloqueo = true
                WITH c
                SET c.valor = c.valor + 1
                RETURN c.valor AS valor
            """).single()["valor"]
            pedido_id = f"PED-{numero:05d}"
            fecha = datetime.now().isoformat(timespec="seconds")
            # El descuento es condicional: si otro pedido se llevó el stock entre
            # la lectura y la escritura, no actualiza y se cancela todo.
            actualizados = tx.run("""
                CREATE (ped:Pedido {id: $pedido, cliente: $cliente, fecha: $fecha})
                WITH ped
                UNWIND $filas AS f
                MATCH (p:Producto {id: f.id}) WHERE p.stock >= f.cantidad
                SET p.stock = p.stock - f.cantidad
                CREATE (ped)-[:INCLUYE {cantidad: f.cantidad, precio_unitario: p.precio}]->(p)
                RETURN count(*) AS n
            """, pedido=pedido_id, cliente=cliente, fecha=fecha, filas=filas).single()["n"]
            if actualizados != len(filas):
                raise SinStock("El stock cambió mientras se procesaba el pedido")
            lineas = [LineaPedido(e["id"], e["nombre"], e["cantidad"], e["precio"]) for e in existentes]
            return Pedido(pedido_id, cliente, fecha, lineas)

        with self._driver.session() as s:
            return s.execute_write(transaccion)

    def pedidos(self):
        registros = self._leer("""
            MATCH (ped:Pedido)-[i:INCLUYE]->(p:Producto)
            WITH ped, i, p ORDER BY p.id
            RETURN ped.id AS id, ped.cliente AS cliente, ped.fecha AS fecha,
                   collect({id: p.id, nombre: p.nombre, cantidad: i.cantidad, precio: i.precio_unitario}) AS lineas
            ORDER BY ped.id DESC
        """)
        return [
            Pedido(r["id"], r["cliente"], r["fecha"],
                   [LineaPedido(l["id"], l["nombre"], l["cantidad"], l["precio"]) for l in r["lineas"]])
            for r in registros
        ]
