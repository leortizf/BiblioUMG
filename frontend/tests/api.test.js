/**
 * Pruebas UNITARIAS de frontend/src/api.js con Vitest.
 * Usan un MOCK de fetch: no se llama al servidor real; se simula su respuesta.
 * Justificación: se prueba solo cómo el frontend arma la petición y traduce errores,
 * sin depender de que la API en Render esté encendida.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, mensajeDeError } from "../src/api.js";

const memoria = {};
beforeEach(() => {
  vi.stubGlobal("sessionStorage", {
    getItem: (k) => memoria[k] ?? null,
    setItem: (k, v) => { memoria[k] = v; },
    removeItem: (k) => { delete memoria[k]; },
  });
});
afterEach(() => { vi.unstubAllGlobals(); delete memoria.sesion; });

describe("mensajeDeError", () => {
  it("usa el detalle de texto del backend", () => expect(mensajeDeError({ detail: "Sin ejemplares" }, 409)).toBe("Sin ejemplares"));
  it("une los errores de validación", () => expect(mensajeDeError({ detail: [{ msg: "Value error, Carné inválido" }] }, 422)).toBe("Carné inválido"));
  it("da un mensaje genérico si no hay detalle", () => expect(mensajeDeError(null, 500)).toBe("Error inesperado (500)."));
});

describe("api (fetch simulado)", () => {
  it("envía el token de la sesión en el encabezado", async () => {
    memoria.sesion = JSON.stringify({ token: "abc" });
    const fetchFalso = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ ok: 1 }) });
    vi.stubGlobal("fetch", fetchFalso);
    await api("GET", "/auth/yo");
    expect(fetchFalso.mock.calls[0][1].headers.Authorization).toBe("Bearer abc");
  });

  it("lanza un error con el mensaje del backend", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 409, json: async () => ({ detail: "Límite alcanzado" }) }));
    await expect(api("POST", "/prestamos", { libro_id: 1 })).rejects.toThrow("Límite alcanzado");
  });
});
