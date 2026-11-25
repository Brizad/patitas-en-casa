/* PWA ciudadana: pantallas, código de seguimiento y consulta del estado (HU-08, #59 y #61).
   La consulta usa GET /reportes/{codigo}/seguimiento (RN-14: sin datos personales). Los textos
   que llegan de la API se pintan con textContent, nunca como HTML. */
(function () {
  'use strict';

  const CODIGO_VALIDO = /^[A-Z0-9]{8}$/;
  const ULTIMO_CODIGO = 'patitas.ultimoCodigo';  // solo el código: nada personal
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

  // localStorage puede fallar (modo privado, almacenamiento lleno): la app sigue sin él.
  function leer(clave) {
    try { return localStorage.getItem(clave); } catch (error) { return null; }
  }
  function escribir(clave, valor) {
    try { localStorage.setItem(clave, valor); } catch (error) { /* sin memoria local */ }
  }

  // --- Pantallas: #reportar (inicio), #codigo y #estado/CODIGO -------------------------

  function mostrarPantalla(nombre) {
    document.body.dataset.pantalla = nombre;  // #428: el CSS ajusta la barra según la pantalla
    for (const seccion of document.querySelectorAll('.pantalla')) {
      seccion.hidden = seccion.id !== 'pantalla-' + nombre;
    }
    for (const enlace of document.querySelectorAll('.pestanas a')) {
      const activa = enlace.dataset.pantalla === nombre
        || (nombre === 'codigo' && enlace.dataset.pantalla === 'reportar');
      if (activa) enlace.setAttribute('aria-current', 'page');
      else enlace.removeAttribute('aria-current');
    }
  }

  function segunLaDireccion() {
    const [nombre, codigo] = location.hash.replace(/^#/, '').split('/');
    if (nombre === 'estado') {
      mostrarPantalla('estado');
      if (codigo && CODIGO_VALIDO.test(normalizar(codigo))) {
        entrada.value = normalizar(codigo);
        consultar(entrada.value);
      }
    } else if (nombre === 'sus' && window.PatitasPiloto && window.PatitasPiloto.activo) {
      mostrarPantalla('sus');  // RNF-06 (#258): solo en modo piloto
    } else if (nombre === '' || nombre === 'inicio') {
      mostrarPantalla('inicio');  // #428: portada de la app, como el prototipo
      fotosDeLaPortada();
    } else if (nombre === 'codigo' && leer(ULTIMO_CODIGO)) {
      const ultimo = leer(ULTIMO_CODIGO);
      if (normalizar($('codigo-grande').textContent) !== ultimo) pintarCodigo(ultimo);
      mostrarPantalla('codigo');
    } else {
      mostrarPantalla('reportar');
      if (window.matchMedia('(min-width: 1024px)').matches) fotosDeLaPortada();  // panel derecho
    }
    window.scrollTo(0, 0);
  }

  // #428: fotos reales de los animales publicados en la portada (si no hay, quedan los colores).
  let fotosPuestas = false;
  async function fotosDeLaPortada() {
    if (fotosPuestas) return;
    fotosPuestas = true;
    try {
      const respuesta = await fetch('/adopciones/animales', { headers: { Accept: 'application/json' } });
      const conFoto = (respuesta.ok ? await respuesta.json() : []).filter((a) => a.foto);
      for (const hueco of document.querySelectorAll('[data-animal]')) {
        const animal = conFoto.find((a) => a.nombre === hueco.dataset.animal) || conFoto.shift();
        if (!animal) continue;
        const img = document.createElement('img');
        img.src = animal.foto;
        img.alt = '';
        img.addEventListener('error', () => img.remove());
        hueco.replaceChildren(img);
      }
    } catch (error) { /* sin señal: la portada se ve igual, sin fotos */ }
  }

  // --- Código de seguimiento (P-02) --------------------------------------------------

  function pintarCodigo(codigo, nota) {
    $('codigo-grande').textContent = codigo.slice(0, 4) + ' ' + codigo.slice(4);
    $('mensaje-codigo').textContent = nota || '';
    $('mensaje-codigo').hidden = !nota;
  }

  // «nota»: aviso opcional, por ejemplo cuando el reporte salió al volver la señal.
  function mostrarCodigo(codigo, nota) {
    escribir(ULTIMO_CODIGO, codigo);
    $('copiar').classList.remove('copiado');
    $('copiar-texto').textContent = 'Copiar código';
    document.dispatchEvent(new CustomEvent('patitas:codigo'));
    pintarCodigo(codigo, nota);
    if (location.hash === '#codigo') segunLaDireccion();
    else location.hash = '#codigo';
  }

  $('copiar').addEventListener('click', async () => {
    const codigo = leer(ULTIMO_CODIGO) || normalizar($('codigo-grande').textContent);
    const aviso = $('mensaje-codigo');
    try {
      await navigator.clipboard.writeText(codigo);
      aviso.textContent = 'Código copiado.';
      $('copiar').classList.add('copiado');
      $('copiar-texto').textContent = '¡Copiado!';
    } catch (error) {
      aviso.textContent = 'Anota tu código: ' + codigo;
    }
    aviso.hidden = false;
  });

  $('ver-estado').addEventListener('click', () => {
    const codigo = leer(ULTIMO_CODIGO) || normalizar($('codigo-grande').textContent);
    location.hash = '#estado/' + codigo;
  });

  // --- Consulta del estado (P-03) ----------------------------------------------------

  function avisar(texto, esError) {
    mensaje.textContent = texto;
    mensaje.classList.toggle('ds-msg--error', Boolean(esError));
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

  // Render gratis se duerme: la primera petición puede tardar hasta un minuto. Si pasan 4 s
  // sin respuesta se avisa, para que no parezca que la app se quedó colgada.
  const DESPERTANDO = 'El servidor está despertando: puede tardar hasta un minuto. '
    + 'No cierres esta página.';

  function avisarSiTarda(alTardar, milisegundos) {
    const reloj = setTimeout(alTardar, milisegundos || 4000);
    return () => clearTimeout(reloj);
  }

  async function consultar(codigo) {
    boton.disabled = true;
    const yaRespondio = avisarSiTarda(() => avisar(DESPERTANDO));
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
      yaRespondio();
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

  // reportar.js muestra el código con esta función al enviar un reporte.
  window.Patitas = { mostrarCodigo, avisarSiTarda, DESPERTANDO };

  // H-2: el aviso de «sin conexión» solo se ve cuando de verdad no hay señal.
  function pintarConexion() {
    $('aviso-sin-conexion').hidden = navigator.onLine !== false;
  }
  window.addEventListener('online', pintarConexion);
  window.addEventListener('offline', pintarConexion);
  pintarConexion();

  window.addEventListener('hashchange', segunLaDireccion);
  segunLaDireccion();

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('sw.js').catch(() => { /* la app funciona igual */ });
    });
  }
})();
