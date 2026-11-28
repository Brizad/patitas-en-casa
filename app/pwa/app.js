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

  // #496: siempre la hora de Colombia, aunque el teléfono tenga otra zona horaria.
  const fecha = (iso) => new Date(iso).toLocaleString('es-CO', {
    day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit', timeZone: 'America/Bogota',
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
    } else if (nombre === 'codigo' && leer(ULTIMO_CODIGO)) {
      const ultimo = leer(ULTIMO_CODIGO);
      if (normalizar($('codigo-grande').textContent) !== ultimo) pintarCodigo(ultimo);
      mostrarPantalla('codigo');
    } else if (nombre === 'instalar') {
      mostrarPantalla('reportar');
      mostrarInstalar();
    } else {
      // Un solo inicio (#452): la portada es la página principal (/); /app/ (y el #inicio de
      // los enlaces viejos) abre directo en «Reportar».
      mostrarPantalla('reportar');
    }
    window.scrollTo(0, 0);
  }

  // --- Instalar la app (#464) --------------------------------------------------------
  // Chrome, Edge y Android avisan con «beforeinstallprompt» que la app se puede instalar: se
  // guarda y se ofrece un botón. Donde no existe (Safari en iPhone), se explica cómo hacerlo.
  let pedidoInstalar = null;
  window.addEventListener('beforeinstallprompt', (evento) => {
    evento.preventDefault();
    pedidoInstalar = evento;
    if (location.hash === '#instalar') mostrarInstalar();
  });

  function mostrarInstalar() {
    const texto = $('instalar-texto');
    const boton = $('instalar-boton');
    $('aviso-instalar').hidden = false;
    if (window.matchMedia('(display-mode: standalone)').matches) {
      texto.textContent = 'Ya tienes Patitas en Casa instalada en este equipo.';
      boton.hidden = true;
    } else if (pedidoInstalar) {
      texto.textContent = 'Instala Patitas en Casa para reportar más rápido, incluso con mala señal.';
      boton.hidden = false;
    } else {
      texto.textContent = 'Para instalarla, abre el menú del navegador y elige «Instalar app» o «Agregar a pantalla de inicio».';
      boton.hidden = true;
    }
  }

  $('instalar-boton').addEventListener('click', async () => {
    if (!pedidoInstalar) return;
    pedidoInstalar.prompt();
    const { outcome } = await pedidoInstalar.userChoice;
    pedidoInstalar = null;
    $('instalar-boton').hidden = true;
    $('instalar-texto').textContent = outcome === 'accepted'
      ? '¡Listo! Encontrarás Patitas en Casa con las demás apps.'
      : 'Puedes instalarla cuando quieras desde el menú del navegador.';
  });

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

  // #490 / #506: ilustración, título y frase según el estado real que devuelve el servidor. Solo
  // adorno: no cambia los pasos. El color del punto va en estilos.css (según data-etapa del texto).
  const ETAPAS = {
    espera: ['consultar-0-espera', 736, 414, 'Consulta tu reporte', 'Tu código está en el mensaje que recibiste al reportar.'],
    recibido: ['consultar-1-recibido', 736, 736, 'Recibimos tu reporte', 'Pronto un veterinario lo revisará.'],
    revisado: ['consultar-2-revisado', 736, 983, 'Un veterinario lo revisó', 'Ya sabemos qué tan urgente es.'],
    camino: ['consultar-3-rescate', 680, 1024, 'El rescate va en camino', 'Va directo hacia el lugar del reporte.'],
    sitio: ['consultar-3-rescate', 680, 1024, 'El rescatista llegó', 'Está con el animal en este momento.'],
    atendido: ['consultar-3-rescate', 680, 1024, '¡Lo atendimos!', 'El animal ya está en buenas manos.'],
    cerrado: ['consultar-4-cerrado', 735, 456, '¡Caso cerrado!', 'Gracias por ayudar. ¡Hiciste la diferencia!'],
    archivado: ['consultar-0-espera', 736, 414, 'Caso cerrado', 'No pudimos verificar el reporte.'],
  };
  let cambioDeEtapa = 0;

  function etapaDelReporte(datos) {
    const pasos = (datos && datos.pasos) || [];
    const hecho = (nombre) => pasos.some((paso) => paso.estado === 'hecho' && paso.nombre.startsWith(nombre));
    const actual = pasos.find((paso) => paso.estado === 'actual');
    if (!actual) {
      // Archivado (#496): solo «Recibido» y «Cerrado». Un descartado ya lo revisó el veterinario.
      if (hecho('Cerrado')) return hecho('Revisado por el veterinario') ? 'cerrado' : 'archivado';
      if (hecho('Atendido')) return 'atendido';
      return pasos.length ? 'revisado' : 'espera';
    }
    if (actual.nombre === 'Recibido' || actual.nombre === 'Revisado por el veterinario') return 'recibido';
    if (actual.nombre === 'Cerrado') return 'atendido';
    if (actual.nombre.startsWith('Atendido') || actual.nombre === 'El rescatista llegó al lugar') return 'sitio';
    if (actual.nombre === 'Rescatista en camino' && !actual.detalle) return 'camino';
    return 'revisado';  // «Buscando rescatista disponible» o atención programada por el refugio
  }

  const sinMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)');

  function mostrarEtapa(etapa) {
    const ilu = $('estado-ilu');
    if (ilu.dataset.etapa === etapa) return;
    ilu.dataset.etapa = etapa;
    const [archivo, ancho, alto, titulo, frase] = ETAPAS[etapa];
    const foto = ilu.querySelector('img');
    const texto = $('estado-texto');
    const turno = ++cambioDeEtapa;
    [foto, texto].forEach((e) => e.classList.add('fuera'));  // fundido de salida (.4 s) juntos; sin movimiento, directo
    setTimeout(() => {
      if (turno !== cambioDeEtapa) return;  // llegó otra consulta mientras tanto
      texto.dataset.etapa = etapa;  // el color del punto cambia con el texto, no antes
      $('estado-titulo').textContent = titulo;
      $('estado-frase').textContent = frase;
      ilu.querySelector('source').srcset = 'fotos/' + archivo + '.webp';
      foto.src = 'fotos/' + archivo + '.jpg';
      foto.width = ancho;
      foto.height = alto;
      const entrar = () => { if (turno === cambioDeEtapa) [foto, texto].forEach((e) => e.classList.remove('fuera')); };
      // Entra cuando la foto ya está lista, para que el fundido no muestre un hueco.
      if (foto.decode) foto.decode().then(entrar, entrar);
      else entrar();
    }, sinMovimiento.matches ? 0 : 200);
    const archivos = [...new Set(Object.values(ETAPAS).map(([nombre]) => nombre))];
    const siguiente = archivos[archivos.indexOf(archivo) + 1];
    if (siguiente) new Image().src = 'fotos/' + siguiente + '.webp';  // solo la siguiente
  }

  // #506: la tarjeta de los 6 pasos se ve mientras no hay resultado.
  function verResultado(si) {
    resultado.hidden = !si;
    $('estado-vacia').hidden = si;
  }

  function avisar(texto, esError) {
    mensaje.textContent = texto;
    mensaje.classList.toggle('ds-msg--error', Boolean(esError));
    mensaje.hidden = false;
    verResultado(false);
    if (esError) {  // código que no existe, sin señal o servidor con fallas
      mostrarEtapa('espera');
      mostrarMapa(null);
    }
  }

  function linea(texto, clase) {
    const span = document.createElement('span');
    span.textContent = texto;
    if (clase) span.className = clase;
    return span;
  }

  // #496: nivel después del triaje, con su color y una frase sencilla.
  const NIVELES = {
    urgente: ['Urgente', 'Lo atenderemos primero.'],
    alta: ['Alta', 'Está en los primeros de la lista.'],
    normal: ['Normal', 'Lo atenderemos en orden.'],
  };

  function textoCola(antes) {
    if (antes === 0) return 'Eres el siguiente en la cola.';
    return 'Tu reporte está en la cola del veterinario. Hay ' + antes
      + (antes === 1 ? ' caso antes que el tuyo.' : ' casos antes que el tuyo.');
  }

  function mostrarColaYNivel(datos) {
    const cola = $('res-cola');
    cola.hidden = !datos.cola;
    if (datos.cola) cola.textContent = textoCola(datos.cola.antes);
    const nivel = $('res-nivel');
    const [nombre, frase] = NIVELES[datos.nivel] || [];
    nivel.hidden = !nombre;
    if (!nombre) return;
    nivel.dataset.nivel = datos.nivel;
    $('res-nivel-etq').textContent = nombre;
    $('res-nivel-frase').textContent = frase;
  }

  function mostrar(datos) {
    mensaje.hidden = true;
    $('res-codigo').textContent = datos.codigo;
    $('res-ultimo').textContent = 'Último cambio: ' + fecha(datos.ultimo_cambio);
    mostrarColaYNivel(datos);
    const pasos = datos.pasos.map((paso) => {
      const item = document.createElement('li');
      if (paso.estado === 'hecho' || paso.estado === 'actual') item.className = paso.estado;
      if (paso.estado === 'actual') item.setAttribute('aria-current', 'step');
      const cuerpo = document.createElement('span');
      const nombre = document.createElement('b');
      nombre.textContent = paso.nombre;
      cuerpo.append(nombre);
      if (paso.estado === 'actual' && paso.detalle) cuerpo.append(linea(paso.detalle, 'mute detalle'));
      // #496: la hora real de cada paso hecho; si no quedó registrada, «—».
      if (paso.estado === 'hecho') cuerpo.append(linea(paso.fecha ? fecha(paso.fecha) : '—', 'mute detalle'));
      item.append(cuerpo);
      return item;
    });
    $('res-pasos').replaceChildren(...pasos);
    verResultado(true);
    mostrarEtapa(etapaDelReporte(datos));
    mostrarMapa(datos);
  }

  // #498: mientras el rescatista va en camino, el mapa en marco reemplaza la ilustración y la
  // consulta se repite sola cada 12 s. Al pasar a «Atendido» vuelve la ilustración.
  const SONDEO_MS = 12000;
  let sondeo = null;

  function mostrarMapa(datos) {
    const seguimiento = window.PatitasSeguimiento;
    // #500: la consulta puede responder antes de que carguen los scripts diferidos del mapa
    // (scripts diferidos): entonces el mapa se pinta en cuanto termine de cargar la página.
    if (datos && datos.rescatista && !seguimiento && document.readyState !== 'complete') {
      window.addEventListener('load', () => mostrarMapa(datos), { once: true });
    }
    const conMapa = Boolean(datos && datos.rescatista && seguimiento && seguimiento.mostrar(datos.rescatista));
    if (!conMapa && seguimiento) seguimiento.ocultar();
    $('estado-ilu').hidden = conMapa;
    clearTimeout(sondeo);
    if (datos && datos.rescatista) sondeo = setTimeout(() => refrescar(datos.codigo), SONDEO_MS);
  }

  async function refrescar(codigo) {
    if (!location.hash.startsWith('#estado') || normalizar(entrada.value) !== codigo) return;
    try {
      const respuesta = await fetch('/reportes/' + encodeURIComponent(codigo) + '/seguimiento', {
        headers: { Accept: 'application/json' },
      });
      if (respuesta.ok) { mostrar(await respuesta.json()); return; }
    } catch (error) { /* sin señal: se intenta otra vez */ }
    sondeo = setTimeout(() => refrescar(codigo), SONDEO_MS);
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
    $('consultando').hidden = false;
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
      $('consultando').hidden = true;
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
