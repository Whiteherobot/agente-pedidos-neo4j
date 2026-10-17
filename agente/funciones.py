"""Tabla de funciones del agente: qué hace cada una y ejemplos de cómo se pide.

El enrutador compara la consulta con estos ejemplos. Los nombres de producto,
ciudades y categorías se reemplazan por marcadores antes de comparar, así que
los ejemplos enseñan la forma de la pregunta y no los productos.
"""

FUNCIONES = [
    {
        "nombre": "buscar_producto",
        "descripcion": "Busca productos por nombre o características y devuelve precio, vendedor y ubicación.",
        "ejemplos": [
            "¿Cuánto cuesta el iPhone 14?",
            "¿Qué laptops tienen?",
            "Busco audífonos con cancelación de ruido",
            "¿Tienen mouse Logitech?",
            "Precio del MacBook Pro",
            "¿Cuánto vale el teclado mecánico?",
            "Quiero ver smartphones Samsung",
            "Información del monitor LG",
            "¿Qué celulares Android venden?",
        ],
    },
    {
        "nombre": "buscar_vendedor",
        "descripcion": "Encuentra vendedores por ciudad, especialidad, calificación o producto que venden.",
        "ejemplos": [
            "¿Quién vende smartphones en Lima?",
            "Vendedores con calificación alta",
            "¿Qué vendedor tiene el MacBook?",
            "Vendedores especializados en redes",
            "¿Hay vendedores en Arequipa?",
            "¿Cuál es el mejor vendedor?",
            "Datos de contacto de los vendedores",
            "¿Quién me vende audífonos?",
        ],
    },
    {
        "nombre": "verificar_stock",
        "descripcion": "Verifica disponibilidad y unidades en stock de un producto.",
        "ejemplos": [
            "¿Cuántos iPhone 14 hay disponibles?",
            "Stock del Samsung Galaxy S23",
            "¿Hay suficiente stock de cables HDMI?",
            "Disponibilidad del monitor LG",
            "¿Cuántas unidades quedan del MacBook?",
            "¿Todavía tienen la impresora en existencia?",
            "¿Se agotó el router?",
            "¿Queda alguna webcam?",
        ],
    },
    {
        "nombre": "comparar_precios",
        "descripcion": "Compara precios entre productos parecidos e indica el más barato y el más caro.",
        "ejemplos": [
            "¿Qué smartphone es más barato?",
            "Comparar precios de laptops",
            "¿iPhone o Samsung, cuál cuesta menos?",
            "Diferencia de precio entre los monitores",
            "¿Cuál es la laptop más cara?",
            "La opción más económica en audífonos",
            "Ordena los celulares de menor a mayor precio",
        ],
    },
    {
        "nombre": "crear_pedido",
        "descripcion": "Agrega un producto al carrito para hacer un pedido.",
        "ejemplos": [
            "Quiero comprar un iPhone 14",
            "Comprar 2 cables HDMI",
            "Agrega el MacBook Pro al carrito",
            "Hacer un pedido de audífonos Sony",
            "Me llevo 3 mouse Logitech",
            "Quiero 2 iPhone 15",
            "Pon una laptop Dell en mi carrito",
            "Deseo adquirir el monitor LG",
        ],
    },
    {
        "nombre": "consultar_categoria",
        "descripcion": "Lista las categorías o los productos de una categoría con su rango de precios.",
        "ejemplos": [
            "¿Qué productos de Audio tienen?",
            "Mostrar todos los accesorios",
            "Productos en la categoría Electrónica",
            "¿Qué hay en Almacenamiento?",
            "¿Qué categorías manejan?",
            "Lista de productos de Oficina",
            "Muéstrame la sección de redes",
        ],
    },
    {
        "nombre": "buscar_por_ubicacion",
        "descripcion": "Productos almacenados y vendedores ubicados en una ciudad.",
        "ejemplos": [
            "Productos disponibles en Lima",
            "¿Qué venden en Arequipa?",
            "¿Qué hay en Cusco?",
            "Stock en Lima",
            "¿Qué tienen en mi ciudad, Cusco?",
            "Entregas desde Arequipa",
        ],
    },
    {
        "nombre": "obtener_recomendaciones",
        "descripcion": "Sugiere productos complementarios o que otros compraron junto con uno.",
        "ejemplos": [
            "¿Qué me recomiendas con una laptop?",
            "Productos relacionados con el iPhone",
            "¿Qué accesorios van bien con el monitor?",
            "Sugerencias para acompañar la MacBook",
            "¿Qué más necesito si compro el iPad?",
            "¿Qué compran junto con el teclado mecánico?",
            "Recomiéndame algo para el Galaxy S24",
        ],
    },
    {
        "nombre": "saludo",
        "descripcion": "Saludos y conversación sin pedido concreto.",
        "ejemplos": [
            "Hola",
            "Buenos días",
            "Buenas tardes",
            "¿Cómo estás?",
            "Gracias",
            "Necesito ayuda",
            "¿Qué puedes hacer?",
        ],
    },
]
