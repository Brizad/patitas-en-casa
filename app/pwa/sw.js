/* Service worker de la PWA ciudadana (HU-08, #59 y #61).
   Guarda solo la interfaz (/app/) para que abra sin señal. Las peticiones a /reportes/ siempre
   van a la red y nunca se guardan: por privacidad y para mostrar el estado actual. El reporte
   hecho sin señal lo guarda reportar.js en localStorage, no el service worker (RF-12). */
const VERSION = 'patitas-pwa-v3';  // #125: video opcional
const INTERFAZ = ['./', 'index.html', 'estilos.css', 'app.js', 'reportar.js', 'icono.svg', 'manifest.webmanifest'];

self.addEventListener('install', (evento) => {
  evento.waitUntil(caches.open(VERSION).then((cache) => cache.addAll(INTERFAZ)));
  self.skipWaiting();
});

self.addEventListener('activate', (evento) => {
  evento.waitUntil(caches.keys().then((nombres) => Promise.all(
    nombres.filter((nombre) => nombre !== VERSION).map((nombre) => caches.delete(nombre)))));
  self.clients.claim();
});

self.addEventListener('fetch', (evento) => {
  const url = new URL(evento.request.url);
  const esInterfaz = url.origin === self.location.origin && url.pathname.startsWith('/app/')
    && !url.pathname.startsWith('/reportes/');
  if (evento.request.method !== 'GET' || !esInterfaz) return;  // la red decide
  // Red primero (versión nueva si hay señal); sin señal, la copia guardada.
  evento.respondWith(fetch(evento.request).catch(() => caches.match(evento.request)
    .then((guardada) => guardada || caches.match('index.html'))));
});
