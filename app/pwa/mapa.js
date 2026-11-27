/* Mapa del paso «¿Dónde está?» (#430): Leaflet (copia local en vendor/leaflet, licencia BSD-2) con
   teselas de OpenStreetMap, gratis y sin clave. Un pin que se arrastra o se mueve tocando el mapa
   pone la latitud y la longitud con la misma función que el GPS (reportar.js); «Usar mi GPS»
   centra el mapa y mueve el pin. La dirección y la comuna siguen igual.
   El mapa es una ayuda: sin conexión, si Leaflet no cargó o si las teselas fallan, se oculta y el
   paso funciona igual con el GPS o la dirección. Nunca bloquea el envío. Las teselas no se guardan
   en el service worker (sw.js solo guarda /app/ y /diseno/). */
(function () {
  'use strict';

  const CUCUTA = [7.8939, -72.5078];
  const TESELAS = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
  const ATRIBUCION = '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
  // #498: el mapa del seguimiento (seguimiento-mapa.js) usa la misma capa y las mismas opciones.
  window.PatitasTeselas = { url: TESELAS, opciones: { maxZoom: 19, attribution: ATRIBUCION,
    referrerPolicy: 'strict-origin-when-cross-origin' } };
  const caja = document.getElementById('mapa-caja');
  const aviso = document.getElementById('mapa-aviso');
  let mapa = null;
  let pin = null;
  let fallas = 0;
  let propio = false; // la ubicación la puso el mapa: no hay que moverlo otra vez

  function sinMapa(texto) {
    caja.hidden = true;
    aviso.textContent = texto;
    aviso.hidden = false;
  }

  function moverPin(latitud, longitud, centrar) {
    if (!mapa) return;
    const punto = [latitud, longitud];
    if (pin) pin.setLatLng(punto);
    else {
      pin = window.L.marker(punto, { draggable: true, keyboard: true, title: 'Ubicación del animal',
        alt: 'Pin de la ubicación del animal' }).addTo(mapa);
      pin.on('dragend', () => marcar(pin.getLatLng(), false));
    }
    if (centrar) mapa.setView(punto, Math.max(mapa.getZoom(), 16));
  }

  /** El pin quedó en un punto: es la ubicación del reporte (igual que el GPS). */
  function marcar(punto, centrar) {
    const lat = Math.round(punto.lat * 1e6) / 1e6;
    const lng = Math.round(punto.lng * 1e6) / 1e6;
    moverPin(lat, lng, centrar);
    propio = true;
    window.PatitasReporte.ponerUbicacion(lat, lng, 'Marcada en el mapa');
    propio = false;
  }

  function crear() {
    if (mapa) { mapa.invalidateSize(); return; }
    if (!window.L) { sinMapa('El mapa no está disponible: usa el GPS o escribe la dirección.'); return; }
    if (navigator.onLine === false) { sinMapa('Sin conexión no se ve el mapa: usa el GPS o escribe la dirección.'); return; }
    caja.hidden = false;
    mapa = window.L.map('mapa', { center: CUCUTA, zoom: 13, scrollWheelZoom: false, tap: true });
    mapa.attributionControl.setPrefix(false);
    // La página va con Referrer-Policy: no-referrer; OSM bloquea (403) las teselas sin Referer.
    // Solo las teselas envían el origen del sitio (nunca la ruta ni el código del reporte).
    window.L.tileLayer(TESELAS, { maxZoom: 19, attribution: ATRIBUCION, referrerPolicy: 'strict-origin-when-cross-origin' })
      .on('tileerror', () => { if (++fallas > 6 && !pin) sinMapa('El mapa no cargó: usa el GPS o escribe la dirección.'); })
      .addTo(mapa);
    mapa.on('click', (evento) => marcar(evento.latlng, false));
    const ya = window.PatitasReporte.ubicacion();
    if (ya) moverPin(ya.latitud, ya.longitud, true);
  }

  if (!caja) return;
  // Leaflet necesita ver su caja: se crea la primera vez que se muestra el paso 2.
  document.addEventListener('patitas:paso', (evento) => { if (evento.detail.paso === 2) crear(); });
  // El GPS ya puso la ubicación: el mapa la muestra (sin volver a ponerla).
  document.addEventListener('patitas:ubicacion', (evento) => {
    const { latitud, longitud } = evento.detail;
    if (mapa && !propio) moverPin(latitud, longitud, true);
  });
  document.addEventListener('patitas:limpio', () => {
    if (pin) { pin.remove(); pin = null; }
    if (mapa) mapa.setView(CUCUTA, 13);
  });
})();
