/**
 * Pantallas del frontend.
 *
 * La aplicación usa "rutas" con # en la URL (por ejemplo #/catalogo).
 * Cada ruta tiene una función que dibuja su pantalla dentro de <main id="app">.
 */
import "./style.css";
import { api, cerrarSesion, guardarSesion, obtenerSesion } from "./api.js";
import {
  NOMBRE_ESTADO, diasParaVencer, formatearFecha, formatearQuetzales,
  validarCarne, validarPassword,
} from "./validaciones.js";

const app = document.getElementById("app");

// ------------------------------------------------------------ utilidades
/** Escapa texto para mostrarlo en HTML sin riesgo de inyección. */
function esc(valor) {
  return String(valor ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function avisar(texto, tipo = "ok") {
  const aviso = document.getElementById("aviso");
  aviso.textContent = texto;
  aviso.className = `visible ${tipo}`;
  clearTimeout(avisar.t);
  avisar.t = setTimeout(() => (aviso.className = ""), 4000);
}

function esBibliotecario() {
  return obtenerSesion()?.usuario.rol === "BIBLIOTECARIO";
}

function sello(estado) {
  return `<span class="sello sello-${estado.toLowerCase()}">${NOMBRE_ESTADO[estado] || estado}</span>`;
}

/** Ejecuta una acción y muestra el resultado; luego redibuja la pantalla. */
async function ejecutar(accion, mensajeOk) {
  try {
    await accion();
    if (mensajeOk) avisar(mensajeOk);
    await refrescarUsuario();
    router();
  } catch (error) {
    avisar(error.message, "error");
  }
}

async function refrescarUsuario() {
  const sesion = obtenerSesion();
  if (!sesion) return;
  try {
    sesion.usuario = await api("GET", "/auth/yo");
    guardarSesion(sesion);
  } catch {
    cerrarSesion();
  }
}

function dibujarMenu() {
  const sesion = obtenerSesion();
  const menu = document.getElementById("menu");
  if (!sesion) {
    menu.innerHTML = `<a href="#/login">Iniciar sesión</a><a href="#/registro">Crear cuenta</a>`;
    return;
  }
  const u = sesion.usuario;
  const admin = u.rol === "BIBLIOTECARIO"
    ? `<a href="#/admin/prestamos">Préstamos</a><a href="#/admin/libros">Libros</a><a href="#/admin/usuarios">Usuarios</a>`
    : `<a href="#/mis-prestamos">Mis préstamos</a>`;
  menu.innerHTML = `<a href="#/catalogo">Catálogo</a>${admin}
    <span class="quien">${esc(u.nombre)}</span>
    <button class="enlace" id="salir">Salir</button>`;
  document.getElementById("salir").onclick = () => {
    cerrarSesion();
    location.hash = "#/login";
  };
}

// ------------------------------------------------------------ login / registro
function pantallaLogin() {
  app.innerHTML = `
    <section class="tarjeta angosta">
      <h1>Iniciar sesión</h1>
      <form id="form-login" novalidate>
        <label>Correo<input name="email" type="email" autocomplete="username" required></label>
        <label>Contraseña<input name="password" type="password" autocomplete="current-password" required></label>
        <button type="submit">Entrar</button>
      </form>
      <p class="nota">¿No tienes cuenta? <a href="#/registro">Crea una</a>.</p>
    </section>`;
  document.getElementById("form-login").onsubmit = async (ev) => {
    ev.preventDefault();
    const datos = Object.fromEntries(new FormData(ev.target));
    try {
      const sesion = await api("POST", "/auth/login", datos);
      guardarSesion(sesion);
      location.hash = sesion.usuario.rol === "BIBLIOTECARIO" ? "#/admin/prestamos" : "#/catalogo";
    } catch (error) {
      avisar(error.message, "error");
    }
  };
}

function pantallaRegistro() {
  app.innerHTML = `
    <section class="tarjeta angosta">
      <h1>Crear cuenta</h1>
      <form id="form-registro" novalidate>
        <label>Nombre completo<input name="nombre" required minlength="3" maxlength="100"></label>
        <label>Carné<input name="carne" placeholder="0901-22-12345" required></label>
        <label>Correo<input name="email" type="email" required></label>
        <label>Contraseña (8 a 64 caracteres)<input name="password" type="password" required></label>
        <label>Tipo de usuario
          <select name="tipo"><option value="ESTUDIANTE">Estudiante</option><option value="DOCENTE">Docente</option></select>
        </label>
        <button type="submit">Crear cuenta</button>
      </form>
    </section>`;
  document.getElementById("form-registro").onsubmit = async (ev) => {
    ev.preventDefault();
    const datos = Object.fromEntries(new FormData(ev.target));
    if (!validarCarne(datos.carne)) return avisar("El carné debe tener el formato 0000-00-00000.", "error");
    if (!validarPassword(datos.password)) return avisar("La contraseña debe tener entre 8 y 64 caracteres.", "error");
    try {
      await api("POST", "/auth/registro", datos);
      avisar("Cuenta creada. Ya puedes iniciar sesión.");
      location.hash = "#/login";
    } catch (error) {
      avisar(error.message, "error");
    }
  };
}

// ------------------------------------------------------------ catálogo
async function pantallaCatalogo() {
  const busqueda = new URLSearchParams(location.hash.split("?")[1] || "").get("q") || "";
  const libros = await api("GET", `/libros?q=${encodeURIComponent(busqueda)}`);
  const sesion = obtenerSesion();
  const puedePedir = sesion && sesion.usuario.rol === "USUARIO";

  app.innerHTML = `
    <section>
      <h1>Catálogo</h1>
      <form id="form-buscar" class="buscador">
        <input name="q" value="${esc(busqueda)}" placeholder="Busca por título, autor o ISBN" aria-label="Buscar">
        <button type="submit">Buscar</button>
      </form>
      ${libros.length === 0 ? `<p class="vacio">No hay libros que coincidan con “${esc(busqueda)}”.</p>` : ""}
      <ul class="fichas">
        ${libros.map((l) => `
          <li class="ficha">
            <h2>${esc(l.titulo)}</h2>
            <p class="autor">${esc(l.autor)}, ${l.anio}</p>
            <p class="isbn">ISBN ${esc(l.isbn)}</p>
            <p class="disponibles ${l.ejemplares_disponibles === 0 ? "agotado" : ""}">
              ${l.ejemplares_disponibles} de ${l.ejemplares_totales} disponibles</p>
            ${puedePedir ? `<button data-solicitar="${l.id}" ${l.ejemplares_disponibles === 0 ? "disabled" : ""}>Solicitar préstamo</button>` : ""}
          </li>`).join("")}
      </ul>
      ${!sesion ? `<p class="nota"><a href="#/login">Inicia sesión</a> para solicitar libros.</p>` : ""}
    </section>`;

  document.getElementById("form-buscar").onsubmit = (ev) => {
    ev.preventDefault();
    location.hash = `#/catalogo?q=${encodeURIComponent(ev.target.q.value)}`;
  };
  app.querySelectorAll("[data-solicitar]").forEach((boton) => {
    boton.onclick = () => ejecutar(
      () => api("POST", "/prestamos", { libro_id: Number(boton.dataset.solicitar) }),
      "Solicitud enviada. Recoge el libro en el mostrador.");
  });
}

// ------------------------------------------------------------ mis préstamos
async function pantallaMisPrestamos() {
  const { usuario } = obtenerSesion();
  const prestamos = await api("GET", "/prestamos/mios");

  const alerta = usuario.bloqueado
    ? `<p class="alerta">Tu cuenta está bloqueada por un atraso grave. Paga tu multa en el mostrador para desbloquearla.</p>`
    : usuario.multa_pendiente > 0
      ? `<p class="alerta">Tienes una multa pendiente de ${formatearQuetzales(usuario.multa_pendiente)}. No puedes solicitar ni renovar hasta pagarla.</p>`
      : "";

  app.innerHTML = `
    <section>
      <h1>Mis préstamos</h1>
      ${alerta}
      ${prestamos.length === 0 ? `<p class="vacio">Aún no tienes préstamos. <a href="#/catalogo">Busca un libro en el catálogo</a>.</p>` : ""}
      <ul class="fichas">
        ${prestamos.map((p) => {
          const dias = diasParaVencer(p.fecha_vencimiento);
          const plazo = ["ACTIVO", "RENOVADO"].includes(p.estado) && dias !== null
            ? `<p class="plazo">${dias === 0 ? "Vence hoy" : `Vence en ${dias} día(s)`}</p>` : "";
          return `
          <li class="ficha">
            ${sello(p.estado)}
            <h2>${esc(p.libro.titulo)}</h2>
            <dl>
              <dt>Entregado</dt><dd>${formatearFecha(p.fecha_entrega)}</dd>
              <dt>Vence</dt><dd>${formatearFecha(p.fecha_vencimiento)}</dd>
              <dt>Renovaciones</dt><dd>${p.renovaciones}</dd>
              ${p.estado === "DEVUELTO" ? `<dt>Multa</dt><dd>${formatearQuetzales(p.multa)}</dd>` : ""}
              ${p.motivo_rechazo ? `<dt>Motivo</dt><dd>${esc(p.motivo_rechazo)}</dd>` : ""}
            </dl>
            ${plazo}
            <div class="acciones">
              ${["ACTIVO", "RENOVADO"].includes(p.estado) ? `<button data-renovar="${p.id}">Renovar</button>` : ""}
              ${p.estado === "SOLICITADO" ? `<button class="secundario" data-cancelar="${p.id}">Cancelar solicitud</button>` : ""}
            </div>
          </li>`;
        }).join("")}
      </ul>
    </section>`;

  app.querySelectorAll("[data-renovar]").forEach((b) => {
    b.onclick = () => ejecutar(() => api("POST", `/prestamos/${b.dataset.renovar}/renovar`), "Préstamo renovado.");
  });
  app.querySelectorAll("[data-cancelar]").forEach((b) => {
    b.onclick = () => ejecutar(() => api("POST", `/prestamos/${b.dataset.cancelar}/cancelar`), "Solicitud cancelada.");
  });
}

// ------------------------------------------------------------ bibliotecario: préstamos
async function pantallaAdminPrestamos() {
  const filtro = new URLSearchParams(location.hash.split("?")[1] || "").get("estado") || "";
  const prestamos = await api("GET", `/prestamos${filtro ? `?estado=${filtro}` : ""}`);
  const opciones = ["", ...Object.keys(NOMBRE_ESTADO)];

  app.innerHTML = `
    <section>
      <h1>Préstamos</h1>
      <label class="filtro">Estado
        <select id="filtro">${opciones.map((e) => `<option value="${e}" ${e === filtro ? "selected" : ""}>${e ? NOMBRE_ESTADO[e] : "Todos"}</option>`).join("")}</select>
      </label>
      <label class="filtro">Fecha a registrar (opcional, para entregas o devoluciones pasadas)
        <input type="date" id="fecha-registro">
      </label>
      <div class="tabla-envoltura">
      <table>
        <thead><tr><th>#</th><th>Usuario</th><th>Libro</th><th>Estado</th><th>Vence</th><th>Multa</th><th>Acciones</th></tr></thead>
        <tbody>
        ${prestamos.map((p) => `
          <tr>
            <td>${p.id}</td>
            <td>${esc(p.usuario.nombre)}<br><small>${esc(p.usuario.carne)} · ${p.usuario.tipo === "DOCENTE" ? "Docente" : "Estudiante"}</small></td>
            <td>${esc(p.libro.titulo)}</td>
            <td>${sello(p.estado)}</td>
            <td>${formatearFecha(p.fecha_vencimiento)}</td>
            <td>${p.estado === "DEVUELTO" ? `${formatearQuetzales(p.multa)}<br><small>${p.dias_atraso} día(s) de atraso</small>` : "—"}</td>
            <td class="acciones">
              ${p.estado === "SOLICITADO" ? `<button data-entregar="${p.id}">Entregar</button><button class="secundario" data-rechazar="${p.id}">Rechazar</button>` : ""}
              ${["ACTIVO", "RENOVADO", "VENCIDO"].includes(p.estado) ? `<button data-devolver="${p.id}">Registrar devolución</button>` : ""}
            </td>
          </tr>`).join("")}
        </tbody>
      </table>
      </div>
      ${prestamos.length === 0 ? `<p class="vacio">No hay préstamos en este estado.</p>` : ""}
    </section>`;

  const fecha = () => {
    const valor = document.getElementById("fecha-registro").value;
    return valor ? { fecha: valor } : {};
  };
  document.getElementById("filtro").onchange = (ev) => {
    location.hash = ev.target.value ? `#/admin/prestamos?estado=${ev.target.value}` : "#/admin/prestamos";
  };
  app.querySelectorAll("[data-entregar]").forEach((b) => {
    b.onclick = () => ejecutar(() => api("POST", `/prestamos/${b.dataset.entregar}/entregar`, fecha()), "Libro entregado.");
  });
  app.querySelectorAll("[data-devolver]").forEach((b) => {
    b.onclick = () => ejecutar(() => api("POST", `/prestamos/${b.dataset.devolver}/devolver`, fecha()), "Devolución registrada.");
  });
  app.querySelectorAll("[data-rechazar]").forEach((b) => {
    b.onclick = () => {
      const motivo = prompt("Motivo del rechazo (mínimo 5 caracteres):");
      if (motivo === null) return;
      ejecutar(() => api("POST", `/prestamos/${b.dataset.rechazar}/rechazar`, { motivo }), "Solicitud rechazada.");
    };
  });
}

// ------------------------------------------------------------ bibliotecario: libros
async function pantallaAdminLibros() {
  const libros = await api("GET", "/libros");
  app.innerHTML = `
    <section>
      <h1>Libros</h1>
      <form id="form-libro" class="tarjeta" novalidate>
        <h2 id="titulo-form">Agregar libro</h2>
        <input type="hidden" name="id">
        <div class="rejilla">
          <label>ISBN-13<input name="isbn" required></label>
          <label>Título<input name="titulo" required></label>
          <label>Autor<input name="autor" required></label>
          <label>Año<input name="anio" type="number" required></label>
          <label>Ejemplares (1 a 20)<input name="ejemplares_totales" type="number" required></label>
        </div>
        <button type="submit">Guardar libro</button>
        <button type="reset" class="secundario">Limpiar</button>
      </form>
      <div class="tabla-envoltura">
      <table>
        <thead><tr><th>Título</th><th>Autor</th><th>ISBN</th><th>Año</th><th>Disponibles</th><th>Acciones</th></tr></thead>
        <tbody>
        ${libros.map((l) => `
          <tr>
            <td>${esc(l.titulo)}</td><td>${esc(l.autor)}</td><td>${esc(l.isbn)}</td><td>${l.anio}</td>
            <td>${l.ejemplares_disponibles} / ${l.ejemplares_totales}</td>
            <td class="acciones"><button class="secundario" data-editar="${l.id}">Editar</button><button class="peligro" data-eliminar="${l.id}">Eliminar</button></td>
          </tr>`).join("")}
        </tbody>
      </table>
      </div>
    </section>`;

  const form = document.getElementById("form-libro");
  form.onreset = () => (document.getElementById("titulo-form").textContent = "Agregar libro");
  form.onsubmit = (ev) => {
    ev.preventDefault();
    const d = Object.fromEntries(new FormData(form));
    const datos = { isbn: d.isbn, titulo: d.titulo, autor: d.autor,
      anio: Number(d.anio), ejemplares_totales: Number(d.ejemplares_totales) };
    ejecutar(() => (d.id ? api("PUT", `/libros/${d.id}`, datos) : api("POST", "/libros", datos)),
      d.id ? "Libro actualizado." : "Libro agregado.");
  };
  app.querySelectorAll("[data-editar]").forEach((b) => {
    b.onclick = () => {
      const l = libros.find((x) => x.id === Number(b.dataset.editar));
      for (const campo of ["id", "isbn", "titulo", "autor", "anio", "ejemplares_totales"]) form[campo].value = l[campo];
      document.getElementById("titulo-form").textContent = "Editar libro";
      form.scrollIntoView({ behavior: "smooth" });
    };
  });
  app.querySelectorAll("[data-eliminar]").forEach((b) => {
    b.onclick = () => {
      if (confirm("¿Eliminar este libro del catálogo?")) {
        ejecutar(() => api("DELETE", `/libros/${b.dataset.eliminar}`), "Libro eliminado.");
      }
    };
  });
}

// ------------------------------------------------------------ bibliotecario: usuarios
async function pantallaAdminUsuarios() {
  const usuarios = await api("GET", "/usuarios");
  app.innerHTML = `
    <section>
      <h1>Usuarios</h1>
      <div class="tabla-envoltura">
      <table>
        <thead><tr><th>Nombre</th><th>Carné</th><th>Tipo</th><th>Multa pendiente</th><th>Estado</th><th>Acciones</th></tr></thead>
        <tbody>
        ${usuarios.map((u) => `
          <tr>
            <td>${esc(u.nombre)}<br><small>${esc(u.email)}</small></td>
            <td>${esc(u.carne)}</td>
            <td>${u.rol === "BIBLIOTECARIO" ? "Bibliotecario" : u.tipo === "DOCENTE" ? "Docente" : "Estudiante"}</td>
            <td>${formatearQuetzales(u.multa_pendiente)}</td>
            <td>${u.bloqueado ? `<span class="sello sello-vencido">Bloqueado</span>` : "Activo"}</td>
            <td class="acciones">
              ${u.multa_pendiente > 0 ? `<button data-pagar="${u.id}" data-deuda="${u.multa_pendiente}">Registrar pago</button>` : ""}
              ${u.bloqueado ? `<button class="secundario" data-desbloquear="${u.id}">Desbloquear</button>` : ""}
            </td>
          </tr>`).join("")}
        </tbody>
      </table>
      </div>
    </section>`;

  app.querySelectorAll("[data-pagar]").forEach((b) => {
    b.onclick = () => {
      const texto = prompt(`Monto a pagar (deuda actual ${formatearQuetzales(b.dataset.deuda)}):`, b.dataset.deuda);
      if (texto === null) return;
      ejecutar(() => api("POST", `/usuarios/${b.dataset.pagar}/pagar-multa`, { monto: Number(texto) }), "Pago registrado.");
    };
  });
  app.querySelectorAll("[data-desbloquear]").forEach((b) => {
    b.onclick = () => ejecutar(() => api("POST", `/usuarios/${b.dataset.desbloquear}/desbloquear`), "Usuario desbloqueado.");
  });
}

// ------------------------------------------------------------ enrutador
const RUTAS = {
  "#/login": { pantalla: pantallaLogin },
  "#/registro": { pantalla: pantallaRegistro },
  "#/catalogo": { pantalla: pantallaCatalogo },
  "#/mis-prestamos": { pantalla: pantallaMisPrestamos, sesion: true },
  "#/admin/prestamos": { pantalla: pantallaAdminPrestamos, admin: true },
  "#/admin/libros": { pantalla: pantallaAdminLibros, admin: true },
  "#/admin/usuarios": { pantalla: pantallaAdminUsuarios, admin: true },
};

async function router() {
  const ruta = (location.hash || "#/catalogo").split("?")[0];
  const destino = RUTAS[ruta] || RUTAS["#/catalogo"];
  if ((destino.sesion || destino.admin) && !obtenerSesion()) {
    location.hash = "#/login";
    return;
  }
  if (destino.admin && !esBibliotecario()) {
    location.hash = "#/catalogo";
    return;
  }
  dibujarMenu();
  try {
    await destino.pantalla();
  } catch (error) {
    app.innerHTML = `<p class="alerta">No se pudo cargar la página: ${esc(error.message)}. Verifica tu conexión e intenta de nuevo.</p>`;
  }
}

window.addEventListener("hashchange", router);
refrescarUsuario().then(router);
