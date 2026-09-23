/**
 * Comunicación con el backend (API REST).
 * Todas las peticiones pasan por la función "api", que agrega el token
 * de sesión y convierte los errores en mensajes legibles.
 */
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function obtenerSesion() {
  const texto = sessionStorage.getItem("sesion");
  return texto ? JSON.parse(texto) : null;
}

export function guardarSesion(sesion) {
  sessionStorage.setItem("sesion", JSON.stringify(sesion));
}

export function cerrarSesion() {
  sessionStorage.removeItem("sesion");
}

export async function api(metodo, ruta, datos) {
  const sesion = obtenerSesion();
  const encabezados = { "Content-Type": "application/json" };
  if (sesion) encabezados.Authorization = `Bearer ${sesion.token}`;

  const respuesta = await fetch(API_URL + ruta, {
    method: metodo,
    headers: encabezados,
    body: datos !== undefined ? JSON.stringify(datos) : undefined,
  });

  if (respuesta.status === 204) return null;
  const cuerpo = await respuesta.json().catch(() => null);
  if (!respuesta.ok) {
    throw new Error(mensajeDeError(cuerpo, respuesta.status));
  }
  return cuerpo;
}

/** Convierte la respuesta de error del backend en un texto para el usuario. */
export function mensajeDeError(cuerpo, estado) {
  if (cuerpo && typeof cuerpo.detail === "string") return cuerpo.detail;
  if (cuerpo && Array.isArray(cuerpo.detail)) {
    return cuerpo.detail.map((e) => e.msg.replace("Value error, ", "")).join(" ");
  }
  return `Error inesperado (${estado}).`;
}
