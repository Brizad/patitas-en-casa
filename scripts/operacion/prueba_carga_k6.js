// k6: carga sobre POST /reportes (endpoint más crítico: el triaje corre dentro) — RNF-01 / RNF-14
// SOLO contra un servidor local con base de pruebas. Nunca contra Render (producción).
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE = __ENV.BASE_URL || 'http://127.0.0.1:8001';
if (/onrender\.com|neon\.tech/.test(BASE)) { throw new Error('Prueba de carga bloqueada: BASE_URL apunta a producción'); }

export const options = {
  stages: [
    { duration: '20s', target: 30 },   // rampa: 30 reportantes concurrentes (RNF-01)
    { duration: '60s', target: 50 },   // pico: 50 usuarios concurrentes (RNF-14)
    { duration: '10s', target: 0 },
  ],
  thresholds: {
    'http_req_duration{endpoint:reportes}': ['p(95)<3000'],   // RNF-01: prioridad en ≤ 3 s (p95)
    'http_req_duration{endpoint:seguimiento}': ['p(95)<800'],
    http_req_failed: ['rate<0.01'],                              // menos de 1 % de errores
    checks: ['rate>0.99'],
  },
};

const TEXTOS = ['Perro atropellado en la avenida, no se mueve y sangra mucho',
  'Gato con una herida abierta en el lomo debajo de un carro',
  'Perrito que cojea un poco y no come hace dos días',
  'Perra con sarna y garrapatas que duerme en el parque'];

// Cada VU simula ciudadanos con IP distinta: el límite A-02 (20 reportes por IP) es por persona.
export default function () {
  const cuerpo = JSON.stringify({ descripcion: TEXTOS[__ITER % 4], latitud: 7.89, longitud: -72.5, comuna: 1 + (__VU % 10) });
  const r = http.post(`${BASE}/reportes`, cuerpo, { headers: { 'Content-Type': 'application/json', 'X-Forwarded-For': `10.0.${__VU}.${__ITER % 250}` }, tags: { endpoint: 'reportes' } });
  check(r, { 'reporte 201': (x) => x.status === 201, 'trae código': (x) => !!x.json('codigo') });
  if (r.status === 201) {
    const s = http.get(`${BASE}/reportes/${r.json('codigo')}/seguimiento`, { tags: { endpoint: 'seguimiento' } });
    check(s, { 'seguimiento 200': (x) => x.status === 200 });
  }
  sleep(1 + Math.random() * 2);   // tiempo de "pensar" de una persona real
}
