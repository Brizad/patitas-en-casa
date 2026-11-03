/* PWA ciudadana: reportar una emergencia sin cuenta (RF-01, #61) y envío sin señal (RF-12).
   Cada reporte recibe en el navegador una clave aleatoria (Idempotency-Key) y espera en
   localStorage hasta que la API responde. Si no hay señal se reintenta al volver la conexión
   (evento online), al abrir la app y cada 30 s; como la clave es la misma, la API devuelve el
   mismo código y el reporte nunca se duplica. Al enviarse se borra del teléfono.
   #125: el video opcional se sube DESPUÉS de crear el reporte, con la misma clave. Sin señal
   no se guarda en el teléfono (pesa hasta 50 MB): solo viaja el texto. */
(function () {
  'use strict';

  const PENDIENTES = 'patitas.pendientes';
  const MIN_CARACTERES = 20;  // RN-01
  const REINTENTO_MS = 30000;
  const VIDEO_MAX_SEGUNDOS = 60;  // RN-01
  const VIDEO_MAX_MB = 50;
  const $ = (id) => document.getElementById(id);
  const formulario = $('reporte');
  const descripcion = $('descripcion');
  const direccion = $('direccion');
  const comuna = $('comuna');
  const botonEnviar = $('enviar');
  const mensaje = $('mensaje-reporte');
  let gps = null;  // { latitud, longitud } cuando el ciudadano comparte su ubicación
  let cadena = Promise.resolve();  // los envíos van de uno en uno
  let ultimoRechazo = '';
  let video = null;  // { archivo, segundos, mb } cuando el ciudadano adjunta un video

  // 16 bytes del generador seguro del navegador = 32 caracteres hex (funciona sin HTTPS).
  function nuevaClave() {
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);
    return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
  }

  // --- Cola de reportes sin enviar ---------------------------------------------------

  function leerCola() {
    try {
      const cola = JSON.parse(localStorage.getItem(PENDIENTES) || '[]');
      return Array.isArray(cola) ? cola.filter((p) => p && p.clave && p.datos) : [];
    } catch (error) {
      return [];
    }
  }

  function escribirCola(cola) {
    try {
      if (cola.length) localStorage.setItem(PENDIENTES, JSON.stringify(cola));
      else localStorage.removeItem(PENDIENTES);
      return true;
    } catch (error) {
      return false;  // modo privado o almacenamiento lleno
    }
  }

  const quitarDeLaCola = (clave) => escribirCola(leerCola().filter((p) => p.clave !== clave));

  // Resultado: { tipo: 'enviado', codigo } | { tipo: 'rechazado', detalle } | { tipo: 'esperar' }
  async function enviar(pendiente) {
    let respuesta;
    try {
      respuesta = await fetch('/reportes', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json', Accept: 'application/json',
          'Idempotency-Key': pendiente.clave,
        },
        body: JSON.stringify(pendiente.datos),
      });
    } catch (error) {
      return { tipo: 'esperar' };  // sin señal
    }
    if (respuesta.ok) return { tipo: 'enviado', codigo: (await respuesta.json()).codigo };
    if (respuesta.status === 422) {
      const cuerpo = await respuesta.json().catch(() => ({}));
      const detalle = typeof cuerpo.detail === 'string' ? cuerpo.detail : 'Revisa los datos del reporte.';
      return { tipo: 'rechazado', detalle };
    }
    return { tipo: 'esperar' };  // servidor caído u ocupado: se reintenta luego
  }

  async function vaciarCola() {
    const resultados = new Map();
    for (const pendiente of leerCola()) {
      const resultado = await enviar(pendiente);
      resultados.set(pendiente.clave, resultado);
      if (resultado.tipo === 'esperar') break;  // sin señal: los demás tampoco saldrían
      quitarDeLaCola(pendiente.clave);
    }
    return resultados;
  }

  function enviarPendientes() {
    cadena = cadena.then(vaciarCola, vaciarCola);
    return cadena;
  }

  // Reintento automático (al volver la señal, al abrir la app y cada 30 s mientras haya cola).
  async function reintentar() {
    if (!leerCola().length) return;
    const resultados = await enviarPendientes();
    const enviados = [];
    for (const resultado of resultados.values()) {
      if (resultado.tipo === 'enviado') enviados.push(resultado.codigo);
      if (resultado.tipo === 'rechazado') ultimoRechazo = resultado.detalle;
    }
    pintarPendientes();
    if (enviados.length) {
      avisar('');  // el aviso «Sin señal…» ya no aplica
      const ultimo = enviados[enviados.length - 1];
      const otros = enviados.slice(0, -1);
      window.Patitas.mostrarCodigo(ultimo, otros.length
        ? 'Volvió la señal y se enviaron tus reportes guardados. Los otros códigos: ' + otros.join(', ') + '.'
        : 'Volvió la señal y tu reporte guardado ya se envió.');
    }
  }

  function pintarPendientes() {
    const caja = $('pendientes');
    const n = leerCola().length;
    const partes = [];
    if (n) {
      partes.push(document.createTextNode(n === 1
        ? 'Tienes 1 reporte guardado sin enviar. Se enviará solo cuando vuelva la señal.'
        : 'Tienes ' + n + ' reportes guardados sin enviar. Se enviarán solos cuando vuelva la señal.'));
      const boton = document.createElement('button');
      boton.type = 'button';
      boton.className = 'ds-btn ds-btn--chico';
      boton.textContent = 'Reintentar ahora';
      boton.addEventListener('click', reintentar);
      partes.push(boton);
    }
    if (ultimoRechazo) {
      const linea = document.createElement('span');
      linea.className = 'err-campo';
      linea.textContent = 'Un reporte guardado no se pudo enviar: ' + ultimoRechazo;
      partes.push(linea);
    }
    caja.replaceChildren(...partes);
    caja.hidden = partes.length === 0;
  }

  // --- Formulario (P-01) -------------------------------------------------------------

  function errorEn(campo, idError, texto) {
    const caja = $(idError);
    caja.textContent = texto || '';
    caja.hidden = !texto;
    if (texto) campo.setAttribute('aria-invalid', 'true');
    else campo.removeAttribute('aria-invalid');
  }

  function avisar(texto, esError) {
    mensaje.textContent = texto;
    mensaje.classList.toggle('ds-msg--error', Boolean(esError));
    mensaje.hidden = !texto;
  }

  function contar() {
    $('contador').textContent = 'Mínimo ' + MIN_CARACTERES + ' caracteres · '
      + descripcion.value.trim().length + '/500';
  }

  function validar() {
    const corta = descripcion.value.trim().length < MIN_CARACTERES;
    const sinUbicacion = !gps && !direccion.value.trim();
    errorEn(descripcion, 'error-descripcion', corta
      ? 'Describe un poco más: mínimo ' + MIN_CARACTERES + ' caracteres (RN-01).' : '');
    errorEn(direccion, 'error-ubicacion', sinUbicacion
      ? 'Indica la ubicación o usa el GPS (RN-01).' : '');
    if (corta) descripcion.focus();
    else if (sinUbicacion) direccion.focus();
    const sinPermiso = $('contacto').value.trim() !== '' && !$('autoriza-contacto').checked;
    errorEn($('contacto'), 'error-contacto', sinPermiso
      ? 'Marca la autorización o deja el contacto vacío.' : '');
    return !corta && !sinUbicacion && !sinPermiso;
  }

  // --- Video opcional (#125) ---------------------------------------------------------

  function duracion(archivo) {
    return new Promise((resolver) => {
      const url = URL.createObjectURL(archivo);
      const elemento = document.createElement('video');
      const fin = (valor) => { URL.revokeObjectURL(url); resolver(valor); };
      elemento.preload = 'metadata';
      elemento.addEventListener('loadedmetadata', () => fin(elemento.duration), { once: true });
      elemento.addEventListener('error', () => fin(null), { once: true });
      elemento.src = url;
    });
  }

  const TEXTO_VIDEO = 'Máximo 60 segundos y 50 MB. Grábalo de lado, que se vea el animal completo.';
  const { MAX_SEGUNDOS, validarVideo, formatoTiempo } = window.PatitasVideo;
  let grabacion = null;  // { flujo, grabador, trozos, temporizador, inicio } mientras se graba
  let urlVista = null;

  // Valida (RN-01: 60 s y 50 MB) y deja el video listo para subir. Devuelve true si sirve.
  async function aceptarVideo(archivo, segundosConocidos) {
    video = null;
    errorEn($('video'), 'error-video', '');
    // El MediaRecorder de algunos navegadores no escribe la duración: vale la del reloj.
    let segundos = await duracion(archivo);
    if (!isFinite(segundos) && segundosConocidos) segundos = segundosConocidos;
    const problema = validarVideo(segundos, archivo.size);
    if (problema) {
      errorEn($('video'), 'error-video', problema);
      $('info-video').textContent = TEXTO_VIDEO;
      return false;
    }
    const mb = archivo.size / (1024 * 1024);
    video = { archivo, segundos: Math.ceil(segundos), mb: Math.round(mb * 10) / 10 };
    const peso = mb < 1 ? Math.max(1, Math.round(archivo.size / 1024)) + ' KB' : video.mb + ' MB';
    $('info-video').textContent = 'Video listo: ' + video.segundos + ' s · ' + peso + '.';
    return true;
  }

  async function elegirVideo(evento) {
    const campo = evento.target;
    const archivo = campo.files && campo.files[0];
    campo.value = '';  // permite elegir el mismo archivo otra vez
    if (!archivo) return;
    cerrarGrabadora();
    await aceptarVideo(archivo, 0);
  }

  function cerrarGrabadora() {
    if (grabacion) {
      clearInterval(grabacion.temporizador);
      grabacion.descartar = true;
      if (grabacion.grabador.state !== 'inactive') grabacion.grabador.stop();
      grabacion.flujo.getTracks().forEach((pista) => pista.stop());
      grabacion = null;
    }
    const vista = $('vista-video');
    vista.pause();
    vista.srcObject = null;
    vista.removeAttribute('src');
    vista.controls = false;
    if (urlVista) { URL.revokeObjectURL(urlVista); urlVista = null; }
    $('grabadora').hidden = true;
  }

  function terminarGrabacion() {
    const actual = grabacion;
    if (!actual || actual.grabador.state === 'inactive') return;
    clearInterval(actual.temporizador);
    actual.grabador.stop();  // el evento «stop» arma el archivo
  }

  async function grabarVideo() {
    errorEn($('video'), 'error-video', '');
    video = null;
    if (!window.MediaRecorder || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      $('video-camara').click();  // sin MediaRecorder: la cámara del teléfono
      return;
    }
    cerrarGrabadora();
    let flujo;
    try {
      flujo = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' } }, audio: false });
    } catch (error) {
      errorEn($('video'), 'error-video', 'No pudimos abrir la cámara. Revisa el permiso o '
        + 'elige un video de la galería.');
      return;
    }
    const grabador = new MediaRecorder(flujo);
    const estado = { flujo, grabador, trozos: [], temporizador: null, inicio: Date.now(),
                     descartar: false };
    grabacion = estado;
    grabador.addEventListener('dataavailable', (e) => { if (e.data.size) estado.trozos.push(e.data); });
    grabador.addEventListener('stop', async () => {
      const segundos = (Date.now() - estado.inicio) / 1000;
      flujo.getTracks().forEach((pista) => pista.stop());
      if (estado.descartar) return;
      const archivo = new Blob(estado.trozos, { type: grabador.mimeType || 'video/webm' });
      const vista = $('vista-video');
      vista.srcObject = null;
      urlVista = URL.createObjectURL(archivo);
      vista.src = urlVista;
      vista.controls = true;
      $('detener-video').hidden = true;
      $('repetir-video').hidden = false;
      await aceptarVideo(archivo, Math.min(segundos, MAX_SEGUNDOS));
    });
    const vista = $('vista-video');
    vista.srcObject = flujo;
    vista.controls = false;
    vista.play().catch(() => {});
    $('grabadora').hidden = false;
    $('detener-video').hidden = false;
    $('repetir-video').hidden = true;
    $('contador-video').textContent = formatoTiempo(0);
    $('info-video').textContent = 'Grabando… se detiene solo a los ' + MAX_SEGUNDOS + ' s.';
    grabador.start();
    estado.temporizador = setInterval(() => {
      const pasados = (Date.now() - estado.inicio) / 1000;
      $('contador-video').textContent = formatoTiempo(pasados);
      if (pasados >= MAX_SEGUNDOS) terminarGrabacion();
    }, 250);
  }

  async function subirVideo(codigo, clave, elegido) {
    try {
      const respuesta = await fetch('/reportes/' + encodeURIComponent(codigo) + '/video', {
        method: 'POST',
        headers: { 'Idempotency-Key': clave, 'Content-Type': elegido.archivo.type || 'video/mp4' },
        body: elegido.archivo,
      });
      if (respuesta.ok) return 'Video recibido, se está analizando.';
      const cuerpo = await respuesta.json().catch(() => ({}));
      if (typeof cuerpo.detail === 'string') return cuerpo.detail;
    } catch (error) { /* sin señal: abajo */ }
    return 'No pudimos subir el video; tu reporte sí llegó y se atiende con la descripción.';
  }

  function datosDelFormulario() {
    const datos = { descripcion: descripcion.value.trim() };
    if (direccion.value.trim()) datos.direccion = direccion.value.trim();
    if (gps) { datos.latitud = gps.latitud; datos.longitud = gps.longitud; }
    if (comuna.value) datos.comuna = Number(comuna.value);
    if (video) { datos.video_segundos = video.segundos; datos.video_mb = video.mb; }
    // RF-18: el contacto solo viaja si la persona marcó la autorización.
    if ($('contacto').value.trim() && $('autoriza-contacto').checked) {
      datos.contacto = $('contacto').value.trim();
      datos.autoriza_contacto = true;
    }
    return datos;
  }

  function limpiar() {
    formulario.reset();
    gps = null;
    video = null;
    cerrarGrabadora();
    errorEn($('video'), 'error-video', '');
    $('info-video').textContent = TEXTO_VIDEO;
    $('estado-gps').textContent = 'o escribe la dirección';
    $('usar-gps').textContent = 'Usar mi GPS';
    contar();
  }

  formulario.addEventListener('submit', async (evento) => {
    evento.preventDefault();
    avisar('');
    if (!validar()) return;
    const pendiente = { clave: nuevaClave(), datos: datosDelFormulario(),
                        guardado_en: new Date().toISOString() };
    // Primero se guarda: si la señal se cae a mitad del envío, el reporte no se pierde.
    const guardado = escribirCola([...leerCola(), pendiente]);
    const elegido = video;
    botonEnviar.disabled = true;
    botonEnviar.textContent = 'Enviando…';
    try {
      const resultado = guardado
        ? (await enviarPendientes()).get(pendiente.clave) || { tipo: 'esperar' }
        : await enviar(pendiente);
      if (resultado.tipo === 'enviado') {
        limpiar();
        window.Patitas.mostrarCodigo(resultado.codigo, elegido ? 'Subiendo el video…' : '');
        if (elegido) {
          const nota = await subirVideo(resultado.codigo, pendiente.clave, elegido);
          window.Patitas.mostrarCodigo(resultado.codigo, nota);
        }
      } else if (resultado.tipo === 'rechazado') {
        avisar(resultado.detalle, true);  // el texto sigue en el formulario para corregirlo
      } else if (guardado) {
        limpiar();  // ya está en la cola: así no se envía dos veces con otra clave
        avisar('Sin señal: guardamos tu reporte en este teléfono y lo enviaremos solo '
          + 'cuando vuelva la conexión. Mantén la app abierta o vuelve a abrirla después.'
          + (elegido ? ' El video no se guarda en el teléfono: solo se enviará el texto.' : ''));
      } else {
        avisar('Sin señal y este navegador no permite guardar el reporte. '
          + 'Intenta de nuevo cuando vuelva la conexión.', true);
      }
    } finally {
      botonEnviar.disabled = false;
      botonEnviar.textContent = 'Enviar reporte';
      pintarPendientes();
    }
  });

  descripcion.addEventListener('input', contar);
  $('video').addEventListener('change', elegirVideo);
  $('video-camara').addEventListener('change', elegirVideo);
  $('elegir-video').addEventListener('click', () => $('video').click());
  $('grabar-video').addEventListener('click', grabarVideo);
  $('detener-video').addEventListener('click', terminarGrabacion);
  $('repetir-video').addEventListener('click', () => { cerrarGrabadora(); grabarVideo(); });
  direccion.addEventListener('input', () => {
    if (direccion.value.trim()) errorEn(direccion, 'error-ubicacion', '');
  });

  $('usar-gps').addEventListener('click', () => {
    const estado = $('estado-gps');
    if (!('geolocation' in navigator)) {
      estado.textContent = 'Este teléfono no permite usar el GPS: escribe la dirección.';
      return;
    }
    estado.textContent = 'Buscando tu ubicación…';
    navigator.geolocation.getCurrentPosition((posicion) => {
      gps = { latitud: posicion.coords.latitude, longitud: posicion.coords.longitude };
      estado.textContent = 'GPS listo · ±' + Math.round(posicion.coords.accuracy) + ' m';
      $('usar-gps').textContent = 'Actualizar GPS';
      errorEn(direccion, 'error-ubicacion', '');
    }, () => {
      estado.textContent = 'No pudimos usar el GPS: escribe la dirección.';
    }, { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 });
  });

  window.addEventListener('online', reintentar);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') reintentar();
  });
  window.addEventListener('storage', (evento) => {  // otra pestaña envió o guardó
    if (evento.key === PENDIENTES) pintarPendientes();
  });
  setInterval(reintentar, REINTENTO_MS);

  contar();
  pintarPendientes();
  reintentar();
})();
