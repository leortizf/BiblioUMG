/**
 * Prueba de carga de BiblioUMG con k6 (E14).
 *
 * Escenario: rampa de 0 a 50 usuarios virtuales en 1 minuto, 50 sostenidos durante
 * 5 minutos y bajada en 30 segundos. Dos endpoints críticos:
 *   - GET  /libros?q=...   (búsqueda del catálogo)  → RNF-01
 *   - POST /auth/login     (inicio de sesión)       → RNF-02
 * Los umbrales (thresholds) son los requerimientos no funcionales de E1.
 */
import http from "k6/http";
import { check, sleep } from "k6";

const BASE = __ENV.BASE_URL || "https://biblioumg-api.onrender.com";
const BUSQUEDAS = ["software", "datos", "Guatemala", "Pérez", "redes", "978"];

export const options = {
  setupTimeout: "5m", // la primera respuesta de Render puede tardar si el servicio estaba dormido
  stages: [
    { duration: "1m", target: 50 },
    { duration: "5m", target: 50 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    "http_req_duration{endpoint:catalogo}": ["p(95)<1500"], // RNF-01
    "http_req_duration{endpoint:login}": ["avg<2000"],      // RNF-02
    http_req_failed: ["rate<0.01"],                         // RNF-03
  },
};

export function setup() {
  // Despierta el servicio gratuito de Render antes de medir.
  for (let i = 0; i < 10; i++) {
    if (http.get(`${BASE}/salud`, { timeout: "90s" }).status === 200) return;
    sleep(5);
  }
}

export default function () {
  const q = BUSQUEDAS[Math.floor(Math.random() * BUSQUEDAS.length)];
  const catalogo = http.get(`${BASE}/libros?q=${encodeURIComponent(q)}`, { tags: { endpoint: "catalogo" } });
  check(catalogo, { "catálogo responde 200": (r) => r.status === 200 });

  const login = http.post(`${BASE}/auth/login`,
    JSON.stringify({ email: "estudiante@biblioumg.com", password: "Estudiante123" }),
    { headers: { "Content-Type": "application/json" }, tags: { endpoint: "login" } });
  check(login, { "login responde 200": (r) => r.status === 200 });

  sleep(1);
}

export function handleSummary(data) {
  const m = data.metrics;
  const val = (nombre, campo) => (m[nombre] ? m[nombre].values[campo] : null);
  const fila = (nombre) => `${(val(nombre, "avg") ?? 0).toFixed(0)} ms promedio, ${(val(nombre, "p(95)") ?? 0).toFixed(0)} ms p95`;
  const texto = [
    "RESULTADOS DE LA PRUEBA DE CARGA — BiblioUMG",
    `URL: ${BASE}`,
    `Solicitudes totales: ${val("http_reqs", "count")}`,
    `Throughput: ${(val("http_reqs", "rate") ?? 0).toFixed(2)} solicitudes/s`,
    `Tasa de error: ${((val("http_req_failed", "rate") ?? 0) * 100).toFixed(2)} %`,
    `Global: ${fila("http_req_duration")}`,
    `Catálogo (GET /libros): ${fila("http_req_duration{endpoint:catalogo}")}`,
    `Login (POST /auth/login): ${fila("http_req_duration{endpoint:login}")}`,
    "",
  ].join("\n");
  return { stdout: texto, "carga/resultados.json": JSON.stringify(data, null, 2), "carga/resultados.txt": texto };
}
