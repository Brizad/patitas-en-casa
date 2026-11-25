/* Modo piloto de usabilidad (RNF-06, #258). Se activa con el enlace que crea el administrador:
   /app/?piloto=TOKEN. El reporte va a /piloto/reportes, que lo valida y NO lo guarda (no llega
   a la cola ni a los rescatistas). Cronometra desde el primer toque hasta el código y luego pide
   el SUS de 10 frases. No pide ni guarda datos personales; los textos se pintan con textContent. */
(function () {
  'use strict';

  const CLAVE = 'patitas.piloto';  // sessionStorage: solo esta pestaña y mientras dure la prueba
  const FRASES = [
    'Creo que me gustaría usar esta aplicación con frecuencia.',
    'Encontré la aplicación innecesariamente compleja.',
    'Pensé que la aplicación era fácil de usar.',
    'Creo que necesitaría la ayuda de una persona con conocimientos técnicos para usarla.',
    'Encontré que las diferentes funciones de la aplicación estaban bien integradas.',
    'Pensé que había demasiada inconsistencia en la aplicación.',
    'Imagino que la mayoría de las personas aprendería a usarla muy rápido.',
    'Encontré la aplicación muy incómoda de usar.',
    'Me sentí muy seguro/a usando la aplicación.',
    'Necesité aprender muchas cosas antes de poder empezar a usarla.',
  ];
  const $ = (id) => document.getElementById(id);

  function leer() {
    try { return sessionStorage.getItem(CLAVE); } catch (error) { return null; }
  }
  function guardar(valor) {
    try {
      if (valor) sessionStorage.setItem(CLAVE, valor); else sessionStorage.removeItem(CLAVE);
    } catch (error) { /* sin memoria de sesión: la prueba sigue en esta página */ }
  }

  const enlace = new URLSearchParams(location.search).get('piloto');
  if (enlace) {
    guardar(enlace);
    // El token sale de la barra; sin pantalla elegida, la prueba empieza en «Reportar» (#428).
    history.replaceState(null, '', location.pathname + (location.hash || '#reportar'));
  }
  const token = enlace || leer();
  let inicio = null;
  let segundos = null;
  window.PatitasPiloto = { activo: Boolean(token), token, alRecibirCodigo };
  if (!token) return;

  $('aviso-piloto').hidden = false;
  const empezar = () => { if (inicio === null) inicio = performance.now(); };
  // El primer toque (o tecla, foco o texto escrito, por si usa teclado o autocompletar).
  for (const evento of ['pointerdown', 'keydown', 'focusin', 'input']) {
    document.addEventListener(evento, empezar, { capture: true });
  }

  function alRecibirCodigo(codigo) {
    segundos = Math.max(1, Math.round((performance.now() - (inicio ?? performance.now())) / 1000));
    window.Patitas.mostrarCodigo(codigo, 'Es una prueba: este código no sirve para consultar.');
    $('titulo-codigo').nextElementSibling.textContent = 'Este reporte de prueba no le llegó a nadie.';
    for (const id of ['copiar', 'ver-estado', 'otro-reporte']) $(id).hidden = true;
    $('ir-sus').hidden = false;
  }

  // --- Cuestionario SUS: 10 frases, cada una de 1 a 5 ---------------------------------
  const formulario = $('sus');
  FRASES.forEach((frase, i) => {
    const grupo = document.createElement('fieldset');
    grupo.className = 'sus-pregunta';
    const leyenda = document.createElement('legend');
    leyenda.textContent = (i + 1) + '. ' + frase;
    const escala = document.createElement('div');
    escala.className = 'sus-escala';
    for (let valor = 1; valor <= 5; valor++) {
      const etiqueta = document.createElement('label');
      const opcion = document.createElement('input');
      opcion.type = 'radio';
      opcion.name = 'sus_' + (i + 1);
      opcion.value = String(valor);
      etiqueta.append(opcion, document.createTextNode(String(valor)));
      escala.append(etiqueta);
    }
    grupo.append(leyenda, escala);
    formulario.insertBefore(grupo, $('enviar-sus'));
  });

  function avisar(texto, esError) {
    const mensaje = $('mensaje-sus');
    mensaje.textContent = texto;
    mensaje.classList.toggle('ds-msg--error', Boolean(esError));
    mensaje.hidden = !texto;
  }

  formulario.addEventListener('submit', async (evento) => {
    evento.preventDefault();
    const respuestas = FRASES.map((_, i) =>
      Number((formulario.querySelector('input[name="sus_' + (i + 1) + '"]:checked') || {}).value));
    const faltan = respuestas.map((r, i) => (r ? 0 : i + 1)).filter(Boolean);
    if (faltan.length) {
      avisar('Te falta responder: ' + faltan.join(', ') + '.', true);
      return;
    }
    $('enviar-sus').disabled = true;
    try {
      const respuesta = await fetch('/piloto/resultados', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Piloto': token },
        body: JSON.stringify({ segundos: segundos || 1, respuestas }),
      });
      if (respuesta.ok || respuesta.status === 409) {
        guardar(null);
        formulario.hidden = true;
        avisar('¡Gracias por participar! Ya puedes devolver el teléfono.');
      } else {
        avisar('No se pudieron guardar las respuestas. Avísale a quien dirige la prueba.', true);
      }
    } catch (error) {
      avisar('Sin señal: espera un momento y vuelve a tocar «Enviar respuestas».', true);
    } finally {
      $('enviar-sus').disabled = false;
    }
  });
})();
