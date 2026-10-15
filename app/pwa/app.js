/* PWA ciudadana: consultar el estado de un reporte con el código (HU-08, #59).
   Usa GET /reportes/{codigo}/seguimiento (RN-14: sin datos personales). Los textos que llegan
   de la API se pintan con textContent, nunca como HTML. */
(function () {
  'use strict';

  const CODIGO_VALIDO = /^[A-Z0-9]{8}$/;
  const $ = (id) => document.getElementById(id);
  const formulario = $('consulta');
  const entrada = $('codigo');
  const boton = formulario.querySelector('button');
  const mensaje = $('mensaje');
  const resultado = $('resultado');

  // Igual que el servidor: acepta minúsculas y espacios ("f2hw 5rtb").
  const normalizar = (texto) => texto.replace(/[\s-]/g, '').toUpperCase();

  const fecha = (iso) => new Date(iso).toLocaleString('es-CO', {
    day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit',
  });

  function avisar(texto, esError) {
    mensaje.textContent = texto;
    mensaje.classList.toggle('err', Boolean(esError));
    mensaje.hidden = false;
    resultado.hidden = true;
  }

  function linea(texto, clase) {
    const span = document.createElement('span');
    span.textContent = texto;
    if (clase) span.className = clase;
    return span;
  }

  function mostrar(datos) {
    mensaje.hidden = true;
    $('res-codigo').textContent = datos.codigo;
    $('res-ultimo').textContent = 'Último cambio: ' + fecha(datos.ultimo_cambio);
    const pasos = datos.pasos.map((paso) => {
      const item = document.createElement('li');
      if (paso.estado === 'hecho' || paso.estado === 'actual') item.className = paso.estado;
      if (paso.estado === 'actual') item.setAttribute('aria-current', 'step');
      const cuerpo = document.createElement('span');
      const nombre = document.createElement('b');
      nombre.textContent = paso.nombre;
      cuerpo.append(nombre);
      if (paso.estado === 'actual' && paso.detalle) cuerpo.append(linea(paso.detalle, 'mute detalle'));
      if (paso.estado === 'hecho' && paso.fecha) cuerpo.append(linea(fecha(paso.fecha), 'mute detalle'));
      item.append(cuerpo);
      return item;
    });
    $('res-pasos').replaceChildren(...pasos);
    resultado.hidden = false;
  }

  async function consultar(codigo) {
    boton.disabled = true;
    try {
      const respuesta = await fetch('/reportes/' + encodeURIComponent(codigo) + '/seguimiento', {
        headers: { Accept: 'application/json' },
      });
      if (respuesta.status === 404) {
        avisar('No encontramos el código ' + codigo + '. Revísalo e intenta de nuevo.', true);
      } else if (!respuesta.ok) {
        avisar('No pudimos consultar ahora. Intenta de nuevo en unos minutos.', true);
      } else {
        mostrar(await respuesta.json());
      }
    } catch (error) {
      avisar('Sin conexión. Intenta cuando vuelva la señal.', true);
    } finally {
      boton.disabled = false;
    }
  }

  formulario.addEventListener('submit', (evento) => {
    evento.preventDefault();
    const codigo = normalizar(entrada.value);
    if (!CODIGO_VALIDO.test(codigo)) {
      avisar('El código tiene 8 letras o números, por ejemplo F2HW5RTB.', true);
      entrada.focus();
      return;
    }
    entrada.value = codigo;
    consultar(codigo);
  });

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('sw.js').catch(() => { /* la consulta funciona igual */ });
    });
  }
})();
