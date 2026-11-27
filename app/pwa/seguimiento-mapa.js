/* Mapa del rescate en «Estado del reporte» (#498): mientras el rescatista va en camino, en el
   lugar de la ilustración se ve un mapa en marco con el animal (huella rosa), el rescatista (círculo
   lila con una patita y su nombre de pila), una línea punteada entre los dos y una franja con la
   distancia en línea recta y el tiempo aproximado (los calcula el servidor). Las posiciones llegan
   redondeadas a ~50 m. El marcador se mueve suave de una posición a otra (sin animación con
   «reducir movimiento»). Las teselas son las de mapa.js (window.PatitasTeselas). Si Leaflet no
   está, no hay mapa: sigue la ilustración. app.js llama a mostrar() y ocultar(). */
(function () {
  'use strict';

  const CUCUTA = [7.8939, -72.5078];
  const LLEGANDO_M = 300;
  const caja = document.getElementById('estado-mapa');
  const lienzo = document.getElementById('mapa-lienzo');
  const franja = document.getElementById('mapa-franja');
  const demo = document.getElementById('mapa-demo');
  const sinMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)');
  const PATITA = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="15.5" r="4.5"/>'
    + '<circle cx="6" cy="10" r="2.2"/><circle cx="10" cy="6" r="2.2"/><circle cx="14" cy="6" r="2.2"/>'
    + '<circle cx="18" cy="10" r="2.2"/></svg>';
  let mapa = null;
  let animal = null;
  let rescatista = null;
  let linea = null;
  let animacion = null;

  function icono(clase) {
    return window.L.divIcon({ className: 'marca-mapa ' + clase, html: PATITA, iconSize: [34, 34], iconAnchor: [17, 17] });
  }

  function crear() {
    if (mapa) { mapa.invalidateSize(); return; }
    mapa = window.L.map(lienzo, { center: CUCUTA, zoom: 14, scrollWheelZoom: false, zoomControl: false });
    mapa.attributionControl.setPrefix(false);
    const teselas = window.PatitasTeselas;
    window.L.tileLayer(teselas.url, teselas.opciones).addTo(mapa);
  }

  function texto(metros) {
    if (metros < 1000) return Math.max(10, Math.round(metros / 10) * 10) + ' m';
    return (metros / 1000).toLocaleString('es-CO', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + ' km';
  }

  function pintarFranja(r) {
    const llegando = r.distancia_m !== null && r.distancia_m < LLEGANDO_M;
    franja.classList.toggle('llegando', llegando);
    if (!r.ubicacion) {
      franja.textContent = 'El rescatista va en camino. Su ubicación aparecerá aquí cuando la comparta.';
    } else if (llegando) {
      franja.textContent = '¡Está llegando!';
    } else if (r.distancia_m === null) {
      franja.textContent = r.nombre + ' va en camino.';
    } else {
      franja.textContent = 'A ' + texto(r.distancia_m) + ' · llega en unos ' + r.minutos + ' min (aprox.)';
    }
  }

  /** De la posición actual a la nueva en 1 s; con «reducir movimiento», de una vez. */
  function moverSuave(destino) {
    if (animacion) cancelAnimationFrame(animacion);
    const origen = rescatista.getLatLng();
    if (sinMovimiento.matches) { rescatista.setLatLng(destino); linea.setLatLngs(puntos()); return; }
    const inicio = performance.now();
    const paso = (ahora) => {
      const f = Math.min(1, (ahora - inicio) / 1000);
      rescatista.setLatLng([origen.lat + (destino[0] - origen.lat) * f, origen.lng + (destino[1] - origen.lng) * f]);
      if (linea) linea.setLatLngs(puntos());
      animacion = f < 1 ? requestAnimationFrame(paso) : null;
    };
    animacion = requestAnimationFrame(paso);
  }

  function puntos() {
    return [animal, rescatista].filter(Boolean).map((m) => m.getLatLng());
  }

  /** Muestra el mapa con los datos de «rescatista» del seguimiento. false si no hay Leaflet. */
  function mostrar(r) {
    if (!caja || !window.L || !window.PatitasTeselas) return false;
    caja.hidden = false;
    crear();
    pintarFranja(r);
    demo.hidden = !r.simulada;
    if (r.animal && !animal) {
      animal = window.L.marker([r.animal.latitud, r.animal.longitud], { icon: icono('marca-animal'), keyboard: false })
        .bindTooltip('Tu reporte', { direction: 'top', offset: [0, -14] }).addTo(mapa);
    }
    if (r.ubicacion) {
      const destino = [r.ubicacion.latitud, r.ubicacion.longitud];
      if (!rescatista) {
        rescatista = window.L.marker(destino, { icon: icono('marca-rescatista'), keyboard: false })
          .bindTooltip(r.nombre, { permanent: true, direction: 'top', offset: [0, -16], className: 'nombre-rescatista' })
          .addTo(mapa);
      } else {
        moverSuave(destino);
      }
      if (animal && !linea) {
        linea = window.L.polyline(puntos(), { color: '#2B2340', weight: 3, dashArray: '6 8' }).addTo(mapa);
      }
    }
    const todos = [r.animal && [r.animal.latitud, r.animal.longitud], r.ubicacion && [r.ubicacion.latitud, r.ubicacion.longitud]]
      .filter(Boolean);
    if (todos.length === 2) mapa.fitBounds(todos, { padding: [60, 40], maxZoom: 17, animate: !sinMovimiento.matches });
    else if (todos.length === 1) mapa.setView(todos[0], 16, { animate: false });
    return true;
  }

  /** Fuera de «en camino»: se quita el mapa y vuelve la ilustración del estado. */
  function ocultar() {
    if (!caja) return;
    caja.hidden = true;
    if (animacion) cancelAnimationFrame(animacion);
    [animal, rescatista, linea].forEach((capa) => { if (capa) capa.remove(); });
    animal = rescatista = linea = animacion = null;
  }

  window.PatitasSeguimiento = { mostrar, ocultar };
})();
