/* Reportar en 4 pasos (#428), como el prototipo: Qué pasa → Dónde → Video → Aviso. Solo muestra
   un paso a la vez y valida el que se deja con las mismas reglas de reportar.js (RN-01). El envío,
   la cola sin señal, el video y el modo piloto siguen en reportar.js y piloto.js sin cambios.
   Los textos que vienen de la persona se pintan con textContent, nunca como HTML. */
(function () {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const TOTAL = 4;
  const sonar = (nombre) => window.PatitasSonido && window.PatitasSonido.tocar(nombre);
  const reporte = window.PatitasReporte;
  const descripcion = $('descripcion');
  const comuna = $('comuna');
  let paso = 1;

  // --- Validación por paso: solo el 1 y el 2 son obligatorios; el 4 revisa el permiso ---
  function valido(n, enfocar) {
    if (n === 1) return reporte.validarDescripcion(enfocar);
    if (n === 2) return reporte.validarUbicacion(enfocar);
    if (n === 4) return reporte.validarContacto(enfocar);
    return true;
  }
  /** Se puede ir al paso n si los anteriores están bien (sin marcar errores). */
  function alcanzable(n) {
    const texto = descripcion.value.trim();
    if (n >= 2 && texto.length < 20) return false;
    if (n >= 3 && !reporte.ubicacion() && !$('direccion').value.trim()) return false;
    return true;
  }

  function pintar(enfocar) {
    for (const bloque of document.querySelectorAll('#reporte .paso')) {
      bloque.hidden = Number(bloque.dataset.paso) !== paso;
    }
    $('paso-atras').hidden = paso === 1;
    $('paso-siguiente').hidden = paso === TOTAL;
    $('enviar').hidden = paso !== TOTAL;
    const sinVideo = paso === 3 && !reporte.video();
    $('texto-siguiente').textContent = sinVideo ? 'Saltar este paso' : 'Siguiente';
    for (const li of document.querySelectorAll('.progreso li')) {
      const n = Number(li.dataset.barra);
      li.className = n < paso ? 'hecho' : n === paso ? 'ahora' : '';
    }
    for (const boton of document.querySelectorAll('.paso-boton')) {
      const n = Number(boton.dataset.ir);
      boton.classList.toggle('ahora', n === paso);
      boton.classList.toggle('hecho', n < paso);
      if (n === paso) boton.setAttribute('aria-current', 'step'); else boton.removeAttribute('aria-current');
      boton.querySelector('.paso-num').textContent = n < paso ? '✓' : String(n);
    }
    $('paso-actual').textContent = 'Paso ' + paso + ' de ' + TOTAL;
    if (paso === TOTAL) resumen();
    document.dispatchEvent(new CustomEvent('patitas:paso', { detail: { paso } }));
    if (enfocar) $('titulo-paso-' + paso).focus();
  }

  function ir(n, sonido) {
    if (n === paso) return;
    paso = Math.min(TOTAL, Math.max(1, n));
    sonar(sonido);
    pintar(true);
  }

  $('paso-siguiente').addEventListener('click', () => {
    if (!valido(paso, true)) { sonar('tic'); return; }
    ir(paso + 1, 'siguiente');
  });
  $('paso-atras').addEventListener('click', () => ir(paso - 1, 'atras'));
  for (const boton of document.querySelectorAll('.paso-boton')) {
    boton.addEventListener('click', () => {
      const n = Number(boton.dataset.ir);
      if (n > paso && !valido(paso, true)) return;
      if (alcanzable(n)) ir(n, 'tic');
    });
  }

  // Si al enviar algo quedó mal (por ejemplo, se borró la dirección), se vuelve a ese paso.
  document.addEventListener('patitas:invalido', (evento) => {
    paso = evento.detail.paso;
    pintar(false);
  });
  // Enviado o guardado sin señal: el formulario quedó limpio y se empieza de nuevo.
  document.addEventListener('patitas:limpio', () => {
    paso = 1;
    for (const boton of document.querySelectorAll('.sintoma')) boton.setAttribute('aria-pressed', 'false');
    elegirComuna('');
    pintar(false);
  });
  document.addEventListener('patitas:codigo', () => sonar('enviado'));
  document.addEventListener('patitas:ubicacion', () => sonar('gps'));

  // Un error que ya se corrigió se quita mientras se escribe (no hay que tocar «Siguiente»).
  descripcion.addEventListener('input', () => {
    if (!$('error-descripcion').hidden) reporte.validarDescripcion(false);
  });

  // --- Paso 1: los botones rápidos escriben el comienzo de la descripción ---------------
  const SEPARADOR = ' — ';
  function sintomas() {
    const frases = [...document.querySelectorAll('.sintoma[aria-pressed="true"]')]
      .map((b) => b.dataset.frase);
    const propio = descripcion.value.includes(SEPARADOR)
      ? descripcion.value.split(SEPARADOR).slice(1).join(SEPARADOR)
      : (descripcion.dataset.auto === '1' ? '' : descripcion.value);
    if (frases.length) {
      const inicio = frases.join(', ');
      descripcion.value = (inicio.charAt(0).toUpperCase() + inicio.slice(1) + SEPARADOR + propio).slice(0, 500);
      descripcion.dataset.auto = '1';
    } else {
      descripcion.value = propio;
      descripcion.dataset.auto = '';
    }
    reporte.contar();
    descripcion.dispatchEvent(new Event('input'));
  }
  for (const boton of document.querySelectorAll('.sintoma')) {
    boton.addEventListener('click', () => {
      boton.setAttribute('aria-pressed', String(boton.getAttribute('aria-pressed') !== 'true'));
      sonar('pop');
      sintomas();
    });
  }

  // --- Paso 2: las comunas son botones; el <select> oculto es el que lee reportar.js ---
  function elegirComuna(valor) {
    comuna.value = valor;
    for (const boton of document.querySelectorAll('.comuna')) {
      boton.setAttribute('aria-pressed', String(boton.dataset.comuna === valor));
    }
  }
  for (const boton of document.querySelectorAll('.comuna')) {
    boton.addEventListener('click', () => { elegirComuna(boton.dataset.comuna); sonar('tic'); });
  }

  // --- Paso 4: resumen antes de enviar --------------------------------------------------
  function fila(nombre, valor) {
    const dt = document.createElement('dt');
    dt.textContent = nombre;
    const dd = document.createElement('dd');
    dd.textContent = valor;
    return [dt, dd];
  }
  function resumen() {
    const lugar = reporte.ubicacion() ? 'Ubicación por GPS' : ($('direccion').value.trim() || '—');
    const video = reporte.video();
    $('resumen').replaceChildren(
      ...fila('Qué pasa', descripcion.value.trim() || '—'),
      ...fila('Dónde', lugar + (comuna.value ? ' · Comuna ' + comuna.value : '')),
      ...fila('Video', video ? 'Sí, ' + video.segundos + ' segundos' : 'Sin video'));
  }

  // El texto de «Siguiente» en el paso del video cambia cuando hay un video listo.
  new MutationObserver(() => pintar(false)).observe($('info-video'), { childList: true, characterData: true, subtree: true });

  pintar(false);
})();
