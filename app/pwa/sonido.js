/* Sonidos suaves al tocar (#428), sintetizados con Web Audio: sin archivos y sin música. Mismas
   recetas que el panel (panel/src/sonido.ts, «pop», «siguiente», «atras»); aquí se suman «tic»,
   «gps» y «enviado» del prototipo ciudadano. Una prueba compara las frecuencias de los dos
   archivos para que no se separen. Se apagan con el botón de la barra y se recuerda en este
   navegador (si el almacenamiento falla, siguen prendidos). Nunca suenan solos: solo al tocar. */
(function () {
  'use strict';

  const CLAVE = 'patitas.pwa.efectos';
  // [frecuencia, inicio (s), duración (s), onda, volumen, frecuencia final]
  const RECETAS = {
    pop: [[560, 0, 0.14, 'sine', 0.3, 1100]],
    siguiente: [[523, 0, 0.15, 'triangle', 0.22], [784, 0.07, 0.15, 'triangle', 0.22]],
    atras: [[659, 0, 0.15, 'triangle', 0.2], [440, 0.07, 0.15, 'triangle', 0.2]],
    tic: [[1200, 0, 0.06, 'square', 0.06]],
    gps: [[880, 0, 0.1, 'sine', 0.15], [1175, 0.12, 0.1, 'sine', 0.15], [880, 0.24, 0.1, 'sine', 0.15],
      [1175, 0.36, 0.1, 'sine', 0.15]],
    enviado: [[523, 0, 0.26, 'triangle', 0.2], [659, 0.09, 0.26, 'triangle', 0.2],
      [784, 0.18, 0.26, 'triangle', 0.2], [1047, 0.27, 0.26, 'triangle', 0.2],
      [1319, 0.36, 0.26, 'triangle', 0.2]],
  };

  let activo = true;
  try { activo = localStorage.getItem(CLAVE) !== 'no'; } catch (error) { /* sigue prendido */ }
  let ctx = null;

  function audio() {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      try { ctx = new AC(); } catch (error) { return null; }
    }
    if (ctx.state === 'suspended') ctx.resume();
    return ctx;
  }

  function tocar(nombre) {
    if (!activo || !RECETAS[nombre]) return;
    const c = audio();
    if (!c) return;
    const t0 = c.currentTime + 0.01;
    for (const [f, inicio, d, onda, vol, fFin] of RECETAS[nombre]) {
      const o = c.createOscillator();
      const g = c.createGain();
      const t = t0 + inicio;
      o.type = onda;
      o.frequency.setValueAtTime(f, t);
      if (fFin) o.frequency.exponentialRampToValueAtTime(fFin, t + d * 0.45);
      g.gain.setValueAtTime(0.0001, t);
      g.gain.exponentialRampToValueAtTime(vol, t + 0.015);
      g.gain.exponentialRampToValueAtTime(0.0001, t + d);
      o.connect(g);
      g.connect(c.destination);
      o.start(t);
      o.stop(t + d + 0.05);
    }
  }

  function pintar(boton) {
    boton.setAttribute('aria-pressed', String(activo));
    boton.title = activo ? 'Apagar los sonidos' : 'Prender los sonidos';
  }

  document.addEventListener('DOMContentLoaded', () => {
    const boton = document.getElementById('sonido');
    if (!boton) return;
    pintar(boton);
    boton.addEventListener('click', () => {
      activo = !activo;
      try { localStorage.setItem(CLAVE, activo ? 'si' : 'no'); } catch (error) { /* solo esta vez */ }
      pintar(boton);
      tocar('pop');
    });
  });

  window.PatitasSonido = { tocar, RECETAS };
})();
