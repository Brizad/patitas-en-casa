/* Reglas del video del reporte (RN-01) sin tocar la pantalla, para poder probarlas con Node.
   validarVideo devuelve '' si el video sirve, o el mensaje que se le muestra al ciudadano. */
(function (raiz) {
  'use strict';

  const MAX_SEGUNDOS = 60;  // RN-01
  const MAX_MB = 50;

  function validarVideo(segundos, bytes) {
    const mb = bytes / (1024 * 1024);
    if (!(bytes > 0)) return 'El video está vacío. Prueba con otro.';
    if (mb > MAX_MB) return 'El video pesa ' + mb.toFixed(1) + ' MB; el máximo es ' + MAX_MB + ' MB.';
    if (typeof segundos !== 'number' || !isFinite(segundos)) {
      return 'No pudimos leer este video. Prueba con otro.';
    }
    if (segundos > MAX_SEGUNDOS) {
      return 'El video dura ' + Math.round(segundos) + ' s; el máximo es ' + MAX_SEGUNDOS + ' s.';
    }
    return '';
  }

  // 0 -> «0:00», 61 -> «1:01» (contador de la grabación).
  function formatoTiempo(segundos) {
    const total = Math.max(0, Math.floor(segundos));
    return Math.floor(total / 60) + ':' + String(total % 60).padStart(2, '0');
  }

  const api = { MAX_SEGUNDOS, MAX_MB, validarVideo, formatoTiempo };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else raiz.PatitasVideo = api;
})(typeof window !== 'undefined' ? window : globalThis);
