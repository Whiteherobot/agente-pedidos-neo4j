const $ = (id) => document.getElementById(id);
const dinero = (n) => `$${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const EJEMPLOS = [
  "¿Cuánto cuesta el iPhone 15?",
  "¿Quién vende laptops en Lima?",
  "¿Qué smartphone es más barato?",
  "¿Qué me recomiendas con una laptop?",
  "Quiero 2 cables HDMI",
];

// Columnas que se muestran según lo que traen las filas.
const COLUMNAS = [
  ["nombre", "Nombre"], ["categoria", "Categoría"], ["precio", "Precio"], ["stock", "Stock"],
  ["vendedor", "Vendedor"], ["ubicacion", "Ubicación"], ["ciudad", "Ciudad"], ["calificacion", "Calificación"],
  ["especialidad", "Especialidad"], ["cantidad", "Productos"], ["precio_minimo", "Desde"], ["precio_maximo", "Hasta"],
];

let carrito = [];

function el(tag, props = {}, hijos = []) {
  const e = document.createElement(tag);
  Object.assign(e, props);
  e.append(...[].concat(hijos));
  return e;
}

async function api(ruta, opciones) {
  const r = await fetch(ruta, opciones);
  const datos = await r.json().catch(() => ({}));
  if (!r.ok) {
    const detalle = Array.isArray(datos.detail) ? "Revise los datos del pedido." : datos.detail;
    throw new Error(detalle || `Error ${r.status}`);
  }
  return datos;
}

async function cargarEstado() {
  try {
    const e = await api("/api/estado");
    $("estado").replaceChildren(
      el("span", { className: "chip", textContent: `Catálogo: ${e.catalogo}` }),
      el("span", { className: "chip", textContent: `Enrutador: ${e.enrutador}` }),
      el("span", { className: "chip", textContent: `Redacción: ${e.redaccion}` }),
    );
  } catch {
    $("estado").replaceChildren(el("span", { className: "chip", textContent: "API sin conexión" }));
  }
}

function mostrarRecorrido(traza) {
  document.querySelectorAll(".graph-node, .graph-edge").forEach((n) => n.classList.remove("active"));
  const pasos = traza.map((t) => t.paso).concat("fin");
  pasos.forEach((paso, i) => {
    document.querySelector(`[data-nodo="${paso}"]`)?.classList.add("active");
    if (i > 0) document.querySelector(`[data-arista="${pasos[i - 1]}-${paso}"]`)?.classList.add("active");
  });
  $("traza").replaceChildren(...traza.map((t) => el("div", { className: "trace-item done" }, [
    el("strong", { textContent: `${t.paso} ` }), el("span", { textContent: `${t.detalle} (${t.ms} ms)` }),
  ])));
}

function tabla(filas, funcion) {
  if (!filas.length) return "";
  const columnas = COLUMNAS.filter(([clave]) => clave in filas[0]);
  const conBoton = "stock" in filas[0];
  const cabecera = el("tr", {}, columnas.map(([, titulo]) => el("th", { textContent: titulo })));
  if (conBoton) cabecera.append(el("th"));
  const cuerpo = filas.map((f) => {
    const fila = el("tr", {}, columnas.map(([clave]) => {
      const v = f[clave];
      return el("td", { textContent: clave.startsWith("precio") ? dinero(v) : v });
    }));
    if (conBoton) {
      const boton = el("button", { className: "btn-agregar", textContent: "Agregar", disabled: f.stock === 0 });
      boton.addEventListener("click", () => agregar({ producto_id: f.id, nombre: f.nombre, cantidad: 1, precio: f.precio }));
      fila.append(el("td", {}, boton));
    }
    return fila;
  });
  return el("table", { className: "tabla" }, [el("thead", {}, cabecera), el("tbody", {}, cuerpo)]);
}

async function consultar() {
  const consulta = $("consulta").value.trim();
  if (!consulta) return;
  $("enviar").disabled = true;
  $("estado-grafo").textContent = "PROCESANDO";
  $("estado-grafo").className = "status-pill active";
  $("aviso").textContent = "";
  try {
    const r = await api("/api/consulta", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ consulta }),
    });
    $("respuesta").textContent = r.respuesta;
    $("funcion").textContent = `Función: ${r.funcion ?? "ninguna"}`;
    $("similitud").textContent = `Similitud: ${r.similitud.toFixed(2)}`;
    $("origen").textContent = `Redacción: ${r.origen}`;
    $("resultados").replaceChildren(tabla(r.filas, r.funcion));
    mostrarRecorrido(r.traza);
    if (r.carrito) agregar(r.carrito);
    $("estado-grafo").textContent = "LISTO";
    $("estado-grafo").className = "status-pill done";
  } catch (error) {
    $("aviso").textContent = error.message;
    $("estado-grafo").textContent = "ERROR";
    $("estado-grafo").className = "status-pill";
  } finally {
    $("enviar").disabled = false;
  }
}

function agregar(linea) {
  const existente = carrito.find((l) => l.producto_id === linea.producto_id);
  if (existente) existente.cantidad += linea.cantidad;
  else carrito.push({ ...linea });
  pintarCarrito();
}

function pintarCarrito() {
  if (!carrito.length) {
    $("carrito").replaceChildren(el("p", { className: "carrito-vacio", textContent: "El carrito está vacío." }));
    $("carrito-resumen").hidden = true;
    return;
  }
  $("carrito").replaceChildren(...carrito.map((l, i) => {
    const quitar = el("button", { className: "btn-eliminar", textContent: "Quitar" });
    quitar.addEventListener("click", () => { carrito.splice(i, 1); pintarCarrito(); });
    return el("div", { className: "carrito-item" }, [
      el("div", { className: "carrito-item-info" }, [
        el("div", { className: "carrito-item-nombre", textContent: l.nombre }),
        el("div", { className: "carrito-item-detalles", textContent: `${l.cantidad} × ${dinero(l.precio)}` }),
      ]),
      el("div", { className: "carrito-item-subtotal", textContent: dinero(l.cantidad * l.precio) }),
      quitar,
    ]);
  }));
  $("total").textContent = dinero(carrito.reduce((s, l) => s + l.cantidad * l.precio, 0));
  $("carrito-resumen").hidden = false;
}

async function confirmar() {
  const cliente = $("cliente").value.trim();
  if (cliente.length < 2) {
    $("aviso").textContent = "Escriba el nombre del cliente para confirmar el pedido.";
    return;
  }
  $("confirmar").disabled = true;
  try {
    // Solo se mandan producto y cantidad: el precio lo pone el servidor.
    const pedido = await api("/api/pedidos", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cliente, items: carrito.map((l) => ({ producto_id: l.producto_id, cantidad: l.cantidad })) }),
    });
    $("aviso").textContent = `Pedido ${pedido.id} confirmado por ${dinero(pedido.total)}.`;
    carrito = [];
    pintarCarrito();
    cargarPedidos();
  } catch (error) {
    $("aviso").textContent = `No se pudo confirmar: ${error.message}`;
  } finally {
    $("confirmar").disabled = false;
  }
}

async function cargarPedidos() {
  const pedidos = await api("/api/pedidos").catch(() => []);
  if (!pedidos.length) {
    $("pedidos").replaceChildren(el("p", { className: "sin-pedidos", textContent: "Todavía no hay pedidos." }));
    return;
  }
  $("pedidos").replaceChildren(...pedidos.map((p) => el("div", { className: "pedido-card" }, [
    el("div", { className: "pedido-header" }, [
      el("span", { className: "pedido-id", textContent: `${p.id} · ${p.cliente}` }),
      el("span", { className: "pedido-fecha", textContent: new Date(p.fecha).toLocaleString("es-EC") }),
    ]),
    el("div", { className: "pedido-items-list", textContent: p.lineas.map((l) => `${l.cantidad} × ${l.producto}`).join(", ") }),
    el("div", { className: "pedido-total", textContent: `Total: ${dinero(p.total)}` }),
  ])));
}

$("ejemplos").replaceChildren(...EJEMPLOS.map((texto) => {
  const b = el("button", { type: "button", className: "chip chip-boton", textContent: texto });
  b.addEventListener("click", () => { $("consulta").value = texto; consultar(); });
  return b;
}));
$("enviar").addEventListener("click", consultar);
$("consulta").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); consultar(); }
});
$("confirmar").addEventListener("click", confirmar);

cargarEstado();
pintarCarrito();
cargarPedidos();

// Un enlace con ?consulta=... abre la página con esa consulta hecha.
const inicial = new URLSearchParams(location.search).get("consulta");
if (inicial) {
  $("consulta").value = inicial;
  consultar();
}
