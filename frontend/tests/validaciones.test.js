/**
 * Pruebas UNITARIAS de frontend/src/validaciones.js con Vitest.
 * Son funciones puras: reciben un valor y devuelven un resultado.
 */
import { describe, expect, it } from "vitest";
import { diasParaVencer, formatearFecha, formatearQuetzales, validarCarne, validarPassword } from "../src/validaciones.js";

describe("validarCarne", () => {
  it("acepta un carné con formato correcto", () => expect(validarCarne("0901-22-12345")).toBe(true));
  it("rechaza letras en el carné", () => expect(validarCarne("0901-AB-12345")).toBe(false));
  it("rechaza vacío o nulo", () => {
    expect(validarCarne("")).toBe(false);
    expect(validarCarne(null)).toBe(false);
  });
});

describe("validarPassword (valores límite 8 y 64)", () => {
  it("rechaza 7 caracteres", () => expect(validarPassword("a".repeat(7))).toBe(false));
  it("acepta 8 caracteres", () => expect(validarPassword("a".repeat(8))).toBe(true));
  it("acepta 64 caracteres", () => expect(validarPassword("a".repeat(64))).toBe(true));
  it("rechaza 65 caracteres", () => expect(validarPassword("a".repeat(65))).toBe(false));
});

describe("formatos", () => {
  it("formatea quetzales con dos decimales", () => expect(formatearQuetzales(14)).toBe("Q14.00"));
  it("formatea una fecha ISO como dd/mm/aaaa", () => expect(formatearFecha("2026-10-30")).toBe("30/10/2026"));
  it("muestra un guion si no hay fecha", () => expect(formatearFecha(null)).toBe("—"));
});

describe("diasParaVencer", () => {
  const hoy = new Date(2026, 9, 30); // 30 de octubre de 2026
  it("cuenta los días que faltan", () => expect(diasParaVencer("2026-11-06", hoy)).toBe(7));
  it("es negativo si ya venció", () => expect(diasParaVencer("2026-10-28", hoy)).toBe(-2));
});
