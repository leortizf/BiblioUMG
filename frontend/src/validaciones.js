/**
 * Validaciones del lado del cliente y utilidades de formato.
 * Son funciones puras (sin acceso al DOM), fáciles de probar con Vitest en la fase 2.
 */
export function validarCarne(carne) {
  return /^\d{4}-\d{2}-\d{3,6}$/.test(carne || "");
}

export function validarPassword(password) {
  const largo = (password || "").length;
  return largo >= 8 && largo <= 64;
}

export function formatearQuetzales(monto) {
  return `Q${Number(monto || 0).toFixed(2)}`;
}

export function formatearFecha(texto) {
  if (!texto) return "—";
  const [anio, mes, dia] = texto.slice(0, 10).split("-");
  return `${dia}/${mes}/${anio}`;
}

/** Días que faltan para el vencimiento (negativo si ya venció). */
export function diasParaVencer(fechaVencimiento, hoy = new Date()) {
  if (!fechaVencimiento) return null;
  const vence = new Date(`${fechaVencimiento}T00:00:00`);
  const base = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate());
  return Math.round((vence - base) / 86400000);
}

export const NOMBRE_ESTADO = {
  SOLICITADO: "Solicitado",
  ACTIVO: "Prestado",
  RENOVADO: "Renovado",
  VENCIDO: "Vencido",
  DEVUELTO: "Devuelto",
  RECHAZADO: "Rechazado",
  CANCELADO: "Cancelado",
};
