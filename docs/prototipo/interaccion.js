/* Patitas en Casa · Prototipo interactivo (Semana 3)
 *
 * Hace que los botones de los dashboards funcionen con datos simulados en el navegador.
 * No hay servidor: el estado vive en esta pestaña (sessionStorage) y se puede reiniciar.
 * Las reglas son las mismas del código real v0.1.0 (y del PR #19):
 *   RN-01  descripción de 20 caracteres o más y ubicación obligatoria; video hasta 60 s y 50 MB.
 *   RF-02  triaje por reglas v0: mismo léxico, negación por palabra completa y confianza 0,5 + 0,15 por señal.
 *   RN-02  confianza < 0,6 con prioridad media o baja => "Requiere revisión".
 *   RN-03  si el clasificador falla => prioridad alta "sin clasificar" (falla segura).
 *   RN-06  solo el veterinario confirma; ajustar exige justificación (RN-16).
 *   RN-04  alerta al alcanzar el 90 % de ocupación y bloqueo con el espacio lleno.
 *   RN-08  un rescate tiene un solo rescatista y un rescatista un solo rescate activo.
 *   RN-14  la consulta por código no muestra datos personales.
 * Este archivo se carga después del visor (index.html) y reemplaza las vistas de cuatro roles.
 */
(function () {
  'use strict';

  /* ---------- 1. Reglas del sistema (puerto de app/triaje y app/reportes) ---------- */
  const LEXICO = [
    ['no respira', 'cri'], ['convulsion', 'cri'], ['atropellad', 'cri'], ['inconsciente', 'cri'],
    ['hemorragia', 'cri'], ['envenen', 'cri'], ['no se para', 'alt'], ['no se puede parar', 'alt'],
    ['fractura', 'alt'], ['sangr', 'alt'], ['herida', 'alt'], ['vomit', 'med'], ['cojea', 'med'],
    ['desnutrid', 'med'], ['no come', 'med'], ['sarna', 'baj'], ['garrapata', 'baj'], ['abandonad', 'baj']
  ];
  const ORDEN = ['cri', 'alt', 'med', 'baj'];
  const NOMBRE = { cri: 'Crítica', alt: 'Alta', med: 'Media', baj: 'Baja' };
  const UMBRAL_CONFIANZA = 0.6;
  const ALERTA_OCUPACION = 0.9;
  const MIN_CARACTERES = 20;
  const VIDEOS = { no: null, v42: { s: 42, mb: 18, t: 'video_perro.mp4 · 0:42 · 18 MB' }, v75: { s: 75, mb: 31, t: 'video_largo.mp4 · 1:15 · 31 MB' } };

  function normalizar(t) {
    return t.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').split(/\s+/).filter(Boolean).join(' ');
  }
  function apareceSinNegacion(senal, texto) {
    if (senal.startsWith('no ')) return texto.includes(senal);
    let i = texto.indexOf(senal);
    while (i !== -1) {
      const previas = texto.slice(0, i).split(' ').filter(Boolean);
      if (!previas.length || previas[previas.length - 1] !== 'no') return true;
      i = texto.indexOf(senal, i + 1);
    }
    return false;
  }
  function clasificar(texto) {
    const t = normalizar(texto);
    const senales = LEXICO.filter(([s]) => apareceSinNegacion(s, t));
    if (!senales.length) return { p: 'baj', conf: 0.3, ev: [] };
    const p = ORDEN.find(o => senales.some(([, q]) => q === o));
    const n = senales.filter(([, q]) => q === p).length;
    return { p, conf: Math.round(Math.min(0.5 + 0.15 * n, 0.95) * 100) / 100, ev: senales.map(([s, q]) => `“${s}” → ${NOMBRE[q].toLowerCase()}`) };
  }
  function triaje(texto, iaCaida) {
    if (iaCaida) return { p: 'alt', conf: 0, ev: ['clasificador no disponible: revisar manualmente'], triaje: 'sin' };
    const r = clasificar(texto);
    r.triaje = (r.conf < UMBRAL_CONFIANZA && (r.p === 'med' || r.p === 'baj')) ? 'rev' : 'ok';
    return r;
  }
  const RANGO = r => r.triaje === 'rev' ? 2 : { cri: 0, alt: 1, med: 3, baj: 4 }[r.p];
  const ALFABETO = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  function nuevoCodigo() {
    let c;
    do { c = Array.from({ length: 8 }, () => ALFABETO[Math.floor(Math.random() * ALFABETO.length)]).join(''); }
    while (S.reportes.some(r => r.cod === c));
    return c;
  }

  /* ---------- 2. Estado de la demostración ---------- */
  const CLAVE = 'patitas-prototipo-v1';
  const ahora = () => Date.now();
  const min = m => ahora() - m * 60000;
  function estadoInicial() {
    const rep = (cod, desc, barrio, minutos, extra) => {
      const t = triaje(desc, false);
      return Object.assign({ cod, desc, barrio, video: null, creado: min(minutos), p: t.p, conf: t.conf, ev: t.ev, triaje: t.triaje,
        estado: 'pendiente', confirmada: null, just: '', rescatista: null, resultado: null, hist: [[min(minutos), 'Recibido']] }, extra || {});
    };
    const k7 = rep('K7PQ2MZD', 'Gata con convulsiones y vómito en la acera', 'La Libertad', 32);
    k7.estado = 'rescate'; k7.confirmada = 'cri'; k7.rescatista = 'otro'; k7.hist.push([min(28), 'Revisado por el veterinario'], [min(25), 'Rescatista en camino']);
    const t4 = rep('T4GN8CWE', 'Gato atrapado en un canal, herida en la cabeza', 'Atalaya', 15);
    t4.estado = 'confirmado'; t4.confirmada = 'alt'; t4.hist.push([min(9), 'Revisado por el veterinario']);
    const r9 = rep('R9TB4LXA', 'Perro tirado en el andén, no se mueve, vecinos preocupados', 'Atalaya', 9);
    Object.assign(r9, { p: 'alt', conf: 0, ev: ['clasificador no disponible: revisar manualmente'], triaje: 'sin' });
    return {
      v: 1, iaCaida: false, guia: false, sel: null, ajustar: false, consulta: '', ultimo: null,
      draft: { desc: '', ubic: '', video: 'no', avisos: false, nombre: '', especie: 'Perro', edad: '', origen: 'Entrega voluntaria', espacio: 'Perros adultos', salud: '', trat: '', vac: '', est: '', nueva: 'cri', just: '', nota: '', res: 'trasladado' },
      errores: {}, msgIng: null, msgRes: null,
      reportes: [k7, t4, r9,
        rep('H3WD8NQE', 'Perro cojea mucho, tiene una herida en la pata', 'Caobos', 14),
        rep('M5CJ1VKS', 'Perro muy flaco en el parque, no se ve herido', 'El Rodeo', 21),
        rep('P8LN6GHT', 'Cachorros abandonados en una caja de cartón', 'Motilones', 25)],
      espacios: [['Perros adultos', 18, 20], ['Cachorros', 7, 8], ['Gatos', 9, 10], ['Aislamiento', 2, 2]],
      resc: { disponible: true, activo: null, mes: 7 },
      bitacora: [[min(28), 'Veterinaria confirmó K7PQ2MZD como crítica'], [min(9), 'Veterinaria confirmó T4GN8CWE como alta']]
    };
  }
  let S;
  try { S = JSON.parse(sessionStorage.getItem(CLAVE)); } catch (e) { S = null; }
  if (!S || S.v !== 1) S = estadoInicial();
  const guardar = () => { try { sessionStorage.setItem(CLAVE, JSON.stringify(S)); } catch (e) { /* sin almacenamiento: sigue en memoria */ } };
  const buscar = c => S.reportes.find(r => r.cod === c);
  const hora = t => new Date(t).toLocaleTimeString('es-CO', { hour: 'numeric', minute: '2-digit' });
  const espera = t => Math.max(0, Math.round((ahora() - t) / 60000)) + ' min';
  const pl = (n, uno, varios) => `${n} ${n === 1 ? uno : varios}`;
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const prio = r => r.confirmada || r.p;
  const chipDe = r => r.triaje === 'sin' && !r.confirmada ? chip('alt', 'Sin clasificar · alta') : r.triaje === 'rev' && !r.confirmada ? chip('rev', 'Requiere revisión') : chip(prio(r), NOMBRE[prio(r)]);
  const ocupacion = () => S.espacios.reduce((a, e) => [a[0] + e[1], a[1] + e[2]], [0, 0]);
  const log = txt => S.bitacora.push([ahora(), txt]);
  const msg = (m) => m ? `<div class="msg ${m.t}" role="status">${m.x}</div>` : '';
  const err = k => S.errores[k] ? `<span class="fe">${S.errores[k]}</span>` : '';

  /* ---------- 3. Vistas interactivas ---------- */
  const rol = id => R.find(r => r.id === id);
  const ultimoHito = (r, txt) => { const h = r.hist.slice().reverse().find(x => x[1] === txt); return h ? h[0] : null; };
  const tiempoDe = (r, i) => i === 0 ? r.creado : i === 1 ? ultimoHito(r, 'Revisado por el veterinario') : i === 2 ? (ultimoHito(r, 'Rescatista en camino') || ultimoHito(r, 'Revisado por el veterinario')) : i === 3 ? (r.resultado ? ultimoHito(r, RES[r.resultado]) : null) : i === 4 ? (r.resultado ? ultimoHito(r, RES[r.resultado]) : null) : null;

  // Ciudadano: reportar (P-01), código (P-02) y consulta (P-03)
  rol('ciudadano').vistas[0].html = () => {
    const d = S.draft, n = d.desc.trim().length, ult = S.ultimo && buscar(S.ultimo);
    const reportar = phone('Reportar emergencia', `
<div class="card" style="padding:14px">${mk(1)}<label class="f">¿Qué le pasa al animal?<textarea class="in area" data-bind="desc" maxlength="500" placeholder="Ej.: perro atropellado en la avenida, no se levanta y sangra">${esc(d.desc)}</textarea></label><span class="tag" id="cnt">Mínimo 20 caracteres · ${n}/500</span>${err('desc')}</div>
<div class="card" style="padding:14px">${mk(2)}<label class="f">Ubicación<input class="in" data-bind="ubic" value="${esc(d.ubic)}" placeholder="Barrio o dirección"></label><div class="row" style="margin-top:6px"><button class="btn" data-act="gps" style="padding:6px 10px;font-size:13px">${ic('pin', 16)} Usar mi GPS</button><span class="tag">o escribe la dirección</span></div>${err('ubic')}</div>
<div class="card" style="padding:14px">${mk(3)}<label class="f">Video (opcional)<select class="in" data-bind="video" data-redraw><option value="no"${d.video === 'no' ? ' selected' : ''}>Sin video</option><option value="v42"${d.video === 'v42' ? ' selected' : ''}>${VIDEOS.v42.t}</option><option value="v75"${d.video === 'v75' ? ' selected' : ''}>${VIDEOS.v75.t}</option></select></label><span class="tag">Hasta 60 s y 50 MB</span>${err('video')}</div>
<div class="card" style="padding:12px 14px">${mk(4)}<button class="row tg" data-act="avisos" aria-pressed="${d.avisos}" style="font-size:13.5px"><span class="sw${d.avisos ? '' : ' off'}" style="width:36px;height:20px"></span>Quiero recibir avisos (WhatsApp o correo)</button></div>
<button class="btn pri" data-act="enviar" style="justify-content:center;padding:13px;position:relative">${mk(5)}Enviar reporte</button>
<div class="mute" style="font-size:12.5px;text-align:center">Sin conexión, el reporte se guarda y se envía solo al volver la señal.</div>`, '1. Reportar emergencia');
    const codigo = phone('Reporte enviado', ult ? `
<div style="text-align:center;padding-top:20px"><div class="ph art" style="margin:0 auto;width:120px;height:120px;border-radius:50%;background:none">${dog()}</div>
<h3 style="margin:14px 0 4px;font-size:20px">¡Gracias por avisar!</h3><div class="mute" style="font-size:14px">Tu reporte ya está en la cola del refugio.</div></div>
<div style="position:relative">${mk(6)}<div class="tag" style="text-align:center;margin-bottom:6px;font-weight:700">TU CÓDIGO DE SEGUIMIENTO</div><div class="big">${ult.cod.slice(0, 4)} ${ult.cod.slice(4)}</div></div>
<div class="card" style="padding:14px;font-size:14px">${mk(7)}<b>Guárdalo:</b> con este código consultas el estado sin dar tu nombre ni tu número.</div>
<button class="btn" data-act="copiar" style="justify-content:center">Copiar código</button><button class="btn pri" data-act="verestado" style="justify-content:center">Ver estado del reporte</button>` : `
<div class="vacio">${dog()}<b>Aún no has enviado un reporte</b><span>Llena el formulario de la izquierda y pulsa <b>Enviar reporte</b>. Aquí aparecerá tu código.</span></div>`, '2. Código de seguimiento');
    const r = S.consulta && buscar(S.consulta);
    let estado = '';
    if (S.consulta && !r) estado = `<div class="msg err">No encontramos el código <b>${esc(S.consulta)}</b>. Revísalo e intenta de nuevo.</div>`;
    if (r) {
      const pasos = ['Recibido', 'Revisado por el veterinario', ['cri', 'alt'].includes(prio(r)) ? 'Rescatista en camino' : 'Atención programada por el refugio', r.resultado ? 'Atendido · ' + RES[r.resultado] : 'Atendido', 'Cerrado'];
      const k = { pendiente: 1, confirmado: 2, rescate: 2, sitio: 3, atendido: 5 }[r.estado];
      const txt = { pendiente: '', confirmado: ['cri', 'alt'].includes(prio(r)) ? 'Buscando rescatista disponible' : '', rescate: '', sitio: 'Rescatista en el sitio', atendido: r.resultado ? RES[r.resultado] : '' }[r.estado];
      estado = `<div class="card" style="padding:14px">${mk(8)}<div class="tag" style="font-weight:700">CÓDIGO</div><div class="mono" style="font-size:18px">${r.cod}</div><div class="mute" style="font-size:13px;margin-top:4px">Último cambio: ${hora(r.hist[r.hist.length - 1][0])}</div></div>
<div class="card" style="padding:16px">${mk(9)}<div class="tl">${pasos.map((p, i) => `<div class="${i < k ? 'ok' : i === k ? 'now' : ''}"><span><b>${p}</b>${i === k && txt ? `<br><span class="mute">${txt}</span>` : ''}${i < k && tiempoDe(r, i) ? `<br><span class="mute">${hora(tiempoDe(r, i))}</span>` : ''}</span></div>`).join('')}</div></div>`;
    }
    const consulta = phone('Estado del reporte', `
<div class="card" style="padding:14px"><label class="f">Código de seguimiento<input class="in mono" data-bind="consultaIn" value="${esc(S.draft.consultaIn || '')}" placeholder="Ej.: F2HW5RTB" maxlength="9" style="text-transform:uppercase"></label><button class="btn pri" data-act="consultar" style="justify-content:center;margin-top:10px;width:100%">Consultar</button></div>
${estado}
<div class="mute" style="font-size:12.5px">Por privacidad no se muestran la dirección exacta ni datos de otras personas.</div>`, '3. Consultar estado');
    return `<div class="phones">${reportar}${codigo}${consulta}</div>`;
  };

  // Veterinario: cola de triaje (P-04)
  rol('veterinario').vistas[0].html = () => {
    const cola = S.reportes.filter(r => r.estado === 'pendiente').sort((a, b) => RANGO(a) - RANGO(b) || a.creado - b.creado);
    NAV_V[0][2] = cola.length || null;
    const sel = buscar(S.sel) && buscar(S.sel).estado === 'pendiente' ? buscar(S.sel) : cola[0];
    const cri = cola.filter(r => r.p === 'cri' && r.triaje === 'ok');
    const confirmados = S.reportes.filter(r => r.confirmada).length;
    const tabla = cola.length ? `<table class="t"><tr><th>Código</th><th>Resumen</th><th>Sugerida</th><th>Conf.</th><th>Espera</th></tr>${cola.map(r => `<tr data-act="sel" data-cod="${r.cod}" class="${sel && r.cod === sel.cod ? 'sel' : ''}" tabindex="0"><td class="mono">${r.cod}</td><td>${esc(r.desc.length > 52 ? r.desc.slice(0, 50) + '…' : r.desc)} · ${esc(r.barrio)}</td><td>${chipDe(r)}</td><td>${r.triaje === 'sin' ? '—' : r.conf.toFixed(2).replace('.', ',')}</td><td>${espera(r.creado)}</td></tr>`).join('')}</table>`
      : `<div class="vacio" style="padding:30px 0">${cat()}<b>Cola vacía</b><span>No hay reportes por confirmar. Envía uno desde el rol Ciudadano.</span></div>`;
    let det = '<div class="mute">Selecciona un reporte de la cola.</div>';
    if (sel) {
      const dup = S.reportes.find(o => o !== sel && o.estado !== 'atendido' && normalizar(o.barrio) === normalizar(sel.barrio));
      const sug = sel.triaje === 'sin' ? 'alt' : sel.p;
      det = `<h4>${sel.cod} ${chipDe(sel)}</h4>
<div class="mute" style="font-size:13.5px;margin-bottom:8px">Recibido ${hora(sel.creado)} · ${esc(sel.barrio)} · ${sel.video ? 'texto y video' : 'solo texto'}</div>
<div style="font-size:14px;margin-bottom:8px">“${esc(sel.desc)}”</div>
<div style="font-weight:800;font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:var(--p-mute)">Evidencias ${sel.triaje === 'sin' ? '' : `(confianza ${sel.conf.toFixed(2).replace('.', ',')})`}</div>
${sel.ev.length ? sel.ev.map((e, i) => `<div class="ev"><i>${i + 1}</i>${esc(e)}</div>`).join('') : '<div class="ev"><i>–</i>Sin señales clínicas en el texto: por eso no se asigna baja automática (RN-02).</div>'}
${sel.triaje !== 'sin' && sel.ev.length < 3 ? `<div class="tag">Las reglas v0 dieron ${pl(sel.ev.length, 'evidencia', 'evidencias')}; el modelo final deberá dar al menos 3 (RNF-09).</div>` : ''}
${sel.video ? `<div style="position:relative;margin-top:8px">${mk(4)}<div class="ph" style="height:80px;justify-content:flex-start;gap:12px;padding:0 14px"><div style="width:60px;height:60px;flex:none">${dog('#C98B4F', '#8A5A2B', '#FFF4E6', false)}</div><span style="font-size:13.5px"><b>Video ${sel.video.s} s</b><br>Análisis de marcha pendiente (incremento I6)</span></div></div>` : ''}
${dup ? `<div class="card" style="padding:10px 12px;margin-top:10px;background:#FFF8EF;border-color:#F4D9B5;font-size:13.5px">${mk(5)}Posible duplicado: ${dup.cod} en el mismo sector (${esc(dup.barrio)}).</div>` : ''}
<div class="row" style="margin-top:12px;position:relative">${mk(6)}<button class="btn pri" data-act="confirmar" data-cod="${sel.cod}">Confirmar ${NOMBRE[sug].toLowerCase()}</button><button class="btn" data-act="ajustar" aria-expanded="${S.ajustar}">Ajustar prioridad…</button></div>
${S.ajustar ? `<div class="card" style="margin-top:10px;padding:12px;background:#F7FAF9"><div class="grid g2" style="gap:10px"><label class="f">Nueva prioridad<select class="in" data-bind="nueva">${ORDEN.map(o => `<option value="${o}"${S.draft.nueva === o ? ' selected' : ''}>${NOMBRE[o]}</option>`).join('')}</select></label><div></div></div><label class="f" style="margin-top:8px">Justificación (obligatoria)<textarea class="in" data-bind="just" style="min-height:60px" placeholder="Ej.: en el video camina sin dificultad">${esc(S.draft.just)}</textarea></label>${err('just')}<button class="btn pri" data-act="guardarajuste" data-cod="${sel.cod}" style="margin-top:8px">Guardar ajuste</button></div>` : ''}
<div class="tag" style="margin-top:6px">Ajustar exige justificación. La IA sugiere; la decisión es tuya.</div>`;
    }
    const fecha = new Date().toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' });
    return desk(NAV_V, 'Cola de triaje', 'Cola de triaje', `${fecha.charAt(0).toUpperCase() + fecha.slice(1)} · ordenada por prioridad y luego por antigüedad`, ['DV', 'Dra. Valentina R.'], `
<div class="grid g4">${kpi(1, 'En cola', cola.length, `${pl(cri.length, 'crítico', 'críticos')} · ${cola.filter(r => r.triaje === 'rev').length} por revisar`)}${kpi(1, 'Críticos sin confirmar', cri.length, cri.length ? 'El más antiguo: ' + espera(Math.min(...cri.map(r => r.creado))) : 'Ninguno', cri.length ? 'alert' : '')}${kpi(1, 'Requieren revisión', cola.filter(r => r.triaje !== 'ok').length, 'Baja confianza o IA sin respuesta')}${kpi(1, 'Confirmados', confirmados, 'Prioridad decidida por veterinario')}</div>
<div class="grid g21">
<div class="card">${mk(2)}<h4>Reportes pendientes<span class="r">Clic en una fila para verla</span></h4>${tabla}</div>
<div class="card">${mk(3)}${det}</div></div>`, 'Turno: 7:00 a. m. – 3:00 p. m.<br>Datos simulados');
  };

  // Coordinador: panel (P-05) e ingreso (P-06)
  const RES = { trasladado: 'Trasladado a refugio', sitio: 'Atendido en el sitio', noencontrado: 'No encontrado', fallecido: 'Fallecido' };
  const ESTADO = r => ({ pendiente: r.triaje === 'rev' ? 'En cola · requiere revisión' : 'En cola del veterinario', confirmado: ['cri', 'alt'].includes(prio(r)) ? 'Confirmado · sin rescatista' : 'Confirmado · atención programada', rescate: 'Rescate asignado', sitio: 'Rescatista en el sitio', atendido: r.resultado ? RES[r.resultado] : 'Atendido' }[r.estado]);
  const coord = rol('coordinador');
  coord.vistas[0].html = () => {
    const [oc, cap] = ocupacion(), pct = oc / cap;
    const curso = S.reportes.filter(r => r.estado === 'rescate' || r.estado === 'sitio');
    const sinAceptar = S.reportes.filter(r => r.estado === 'confirmado' && ['cri', 'alt'].includes(prio(r)));
    const porIngresar = S.reportes.filter(r => r.resultado === 'trasladado' && !r.ingresado);
    NAV_K[1][2] = S.reportes.length; NAV_K[2][2] = curso.length || null;
    const recientes = S.reportes.slice().sort((a, b) => b.creado - a.creado).slice(0, 6);
    const alertas = [];
    if (pct >= ALERTA_OCUPACION) alertas.push(['#9B1C1C', `<b>Ocupación en ${Math.floor(pct * 100)} %.</b> ${oc >= cap ? 'Refugio lleno: no se pueden registrar ingresos.' : 'Los nuevos ingresos requieren un egreso o traslado.'}`]);
    sinAceptar.forEach(r => alertas.push(['#C2410C', `<b>Rescate ${NOMBRE[prio(r)].toLowerCase()} sin aceptar</b> (${r.cod}) hace ${espera(r.hist[r.hist.length - 1][0])}.`]));
    porIngresar.forEach(r => alertas.push(['#0F6B5E', `<b>Animal en camino al refugio</b> desde el rescate ${r.cod}. <button class="lnk" data-act="ir" data-to="P-06">Registrar ingreso</button>`]));
    alertas.push(['#B07A00', '<b>Seguimiento de 30 días vencido:</b> Luna, adoptada el 28 de agosto.']);
    return desk(NAV_K, 'Inicio', 'Panel del refugio', 'Datos simulados · se actualiza con cada acción de la demostración', ['CM', 'Carlos M. · Coordinador'], `
<div class="grid g4">${kpi(1, 'Ocupación', `${oc} / ${cap}`, `${Math.floor(pct * 100)} %${pct >= ALERTA_OCUPACION ? ' · alerta activa' : ''}`, pct >= ALERTA_OCUPACION ? 'alert' : '')}${kpi(1, 'Reportes', S.reportes.length, `${pl(S.reportes.filter(r => prio(r) === 'cri').length, 'crítico', 'críticos')} · ${pl(S.reportes.filter(r => prio(r) === 'alt').length, 'alto', 'altos')}`)}${kpi(1, 'Rescates en curso', curso.length, sinAceptar.length ? `${pl(sinAceptar.length, 'confirmado', 'confirmados')} sin aceptar` : 'Todos asignados')}${kpi(1, 'Adopciones del mes', '6', '2 solicitudes por decidir')}</div>
<div class="grid g21">
<div class="card">${mk(2)}<h4>Ocupación por espacio<button class="r lnk" data-act="ir" data-to="P-06">Registrar ingreso</button></h4>
<div class="stack">${S.espacios.map(([n, o, c]) => `<div><div class="row" style="justify-content:space-between;font-size:14px"><span>${n}</span><b>${o} / ${c}</b></div><div class="pb"><span class="${o / c >= ALERTA_OCUPACION ? 'hot' : ''}" style="width:${o / c * 100}%"></span></div></div>`).join('')}</div>
<div style="margin-top:8px;position:relative;padding-top:16px">${mk(3)}<div class="row" style="justify-content:space-between"><b style="font-size:14px">Ingresos y egresos · últimos 7 días</b><span class="tag">— ingresos  - - egresos</span></div>${line([2, 3, 1, 4, 2, 3, 2], 5, ['mar', 'mié', 'jue', 'vie', 'sáb', 'dom', 'lun'], 620, 150, [1, 1, 2, 1, 3, 1, 1])}</div></div>
<div class="card">${mk(4)}<h4>Alertas</h4>${alertas.map(([c, t]) => `<div class="al"><span class="dot" style="background:${c}"></span><span>${t}</span></div>`).join('')}</div></div>
<div class="grid g2">
<div class="card">${mk(5)}<h4>Reportes recientes</h4><table class="t"><tr><th>Código</th><th>Barrio</th><th>Prioridad</th><th>Estado</th></tr>${recientes.map(r => `<tr><td class="mono">${r.cod}</td><td>${esc(r.barrio)}</td><td>${chipDe(r)}</td><td>${ESTADO(r)}</td></tr>`).join('')}</table></div>
<div class="card">${mk(6)}<h4>Bitácora reciente<span class="r">RF-32</span></h4>${S.bitacora.slice(-6).reverse().map(([t, x]) => `<div class="al"><span class="mono" style="flex:none;color:var(--p-mute)">${hora(t)}</span><span>${esc(x)}</span></div>`).join('')}</div></div>`, 'Refugio de ejemplo · Cúcuta<br>Datos simulados');
  };
  coord.vistas[1].html = () => {
    const d = S.draft, e = S.espacios.find(x => x[0] === d.espacio) || S.espacios[0], [oc, cap] = ocupacion();
    const lleno = e[1] >= e[2] || oc >= cap, pctDesp = (oc + 1) / cap;
    const origenes = ['Entrega voluntaria'].concat(S.reportes.filter(r => r.resultado === 'trasladado' && !r.ingresado).map(r => 'Rescate ' + r.cod + ' · ' + r.barrio));
    const campo = (k, l, ph) => `<label class="f">${l}<input class="in" data-bind="${k}" value="${esc(d[k])}" placeholder="${ph}"></label>`;
    return desk(NAV_K, 'Animales', 'Registrar ingreso', 'Ficha clínica mínima · el cupo se valida antes de guardar', ['CM', 'Carlos M. · Coordinador'], `
<div class="grid g21">
<div class="card">${mk(7)}<h4>Datos del animal</h4>
<div class="grid g2" style="gap:12px">
<label class="f">Especie<select class="in" data-bind="especie">${['Perro', 'Gato'].map(x => `<option${d.especie === x ? ' selected' : ''}>${x}</option>`).join('')}</select></label>
${campo('nombre', 'Nombre provisional', 'Ej.: Rocky')}${err('nombre')}
${campo('edad', 'Sexo y edad aproximada', 'Ej.: macho · 3 años aprox.')}
<label class="f">Origen<select class="in" data-bind="origen">${origenes.map(x => `<option${d.origen === x ? ' selected' : ''}>${esc(x)}</option>`).join('')}</select></label>
<label class="f">Espacio asignado<select class="in" data-bind="espacio" data-redraw>${S.espacios.map(([n, o, c]) => `<option value="${n}"${d.espacio === n ? ' selected' : ''}>${n} (${o}/${c})</option>`).join('')}</select></label>
<label class="f">Fecha de ingreso<input class="in" value="${new Date().toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric' })} · ${hora(ahora())}" readonly></label>
</div>
<label class="f" style="margin-top:12px">Estado de salud<textarea class="in area" data-bind="salud" style="min-height:64px" placeholder="Ej.: fractura en pata trasera; consciente y alerta">${esc(d.salud)}</textarea></label>${err('salud')}
<div class="grid g3" style="gap:12px;margin-top:12px">${campo('trat', 'Tratamientos', 'Ej.: analgésico')}${campo('vac', 'Vacunas', 'Ej.: desconocidas')}${campo('est', 'Esterilización', 'Ej.: pendiente')}</div>
<div class="row" style="margin-top:16px"><button class="btn pri" data-act="guardaringreso">Guardar ingreso</button><button class="btn" data-act="limpiaringreso">Limpiar</button></div>${msg(S.msgIng)}</div>
<div class="stack" style="gap:16px">
<div class="card">${mk(8)}<h4>Cupo disponible</h4>
<div class="row" style="justify-content:space-between;font-size:14px"><span>${e[0]}</span><b>${e[1]} / ${e[2]}${lleno ? ' · lleno' : ` → ${e[1] + 1} / ${e[2]}`}</b></div><div class="pb" style="margin:6px 0 12px"><span class="${e[1] / e[2] >= ALERTA_OCUPACION ? 'hot' : ''}" style="width:${e[1] / e[2] * 100}%"></span></div>
<div class="row" style="justify-content:space-between;font-size:14px"><span>Total del refugio</span><b>${oc} / ${cap}${oc >= cap ? ' · lleno' : lleno ? '' : ` → ${oc + 1} / ${cap}`}</b></div><div class="pb" style="margin-top:6px"><span class="${oc / cap >= ALERTA_OCUPACION ? 'hot' : ''}" style="width:${oc / cap * 100}%"></span></div>
<div class="card" style="margin-top:12px;padding:10px 12px;background:${lleno ? '#FFF7F5' : '#F3F8F6'};border-color:${lleno ? '#F2B8B0' : '#CFE3DC'};font-size:13.5px">${lleno ? `<b>No hay cupo en ${e[0]}.</b> El sistema no deja guardar (RN-04). Registra un egreso o elige otro espacio.` : `Con este ingreso la ocupación queda en ${Math.floor(pctDesp * 100)} %.${pctDesp >= ALERTA_OCUPACION ? ' Se avisará a los coordinadores (RN-04).' : ''}`}</div>
<button class="btn" data-act="egreso" style="margin-top:10px;font-size:13px;padding:7px 10px"${e[1] ? '' : ' disabled'}>Registrar egreso de un animal de ${e[0]} (RF-26)</button></div>
<div class="card">${mk(9)}<h4>Fotos</h4><div class="grid g3" style="gap:8px"><div class="ph art" style="height:86px;background:#FBE7CF"><div style="width:76px;height:76px">${d.especie === 'Gato' ? cat() : dog('#D8A86B', '#9C6B3A', '#FBE7CF', false)}</div></div><div class="ph" style="height:86px;background:#F6F5F1;border:2px dashed #D9D4C7;color:#5B6670;flex-direction:column;font-size:12.5px;font-weight:700">${ic('cam', 22)}Agregar</div></div>
<div class="tag" style="margin-top:10px">Al guardar queda en la bitácora quién lo registró y la ocupación antes y después.</div></div></div></div>`, 'Refugio de ejemplo · Cúcuta<br>Datos simulados');
  };

  // Rescatista: ofertas (P-07), rescate en curso (P-08) y resultado (P-09)
  rol('rescatista').vistas[0].html = () => {
    const rs = S.resc, act = rs.activo && buscar(rs.activo);
    const ofertas = S.reportes.filter(r => r.estado === 'confirmado' && ['cri', 'alt'].includes(prio(r)));
    const km = c => ((c.charCodeAt(0) + c.charCodeAt(3)) % 40 / 10 + 0.6).toFixed(1).replace('.', ',');
    const p1 = phone('Rescates', `
<div class="card" style="padding:12px 14px">${mk(1)}<button class="row tg" data-act="disponible" aria-pressed="${rs.disponible}" style="justify-content:space-between;width:100%"><span style="text-align:left"><b>${rs.disponible ? 'Disponible' : 'No disponible'}</b><br><span class="tag">Zona: Comuna 6 y alrededores</span></span><span class="sw${rs.disponible ? '' : ' off'}"></span></button></div>
<div style="font-weight:800;font-size:13px;color:var(--p-mute);text-transform:uppercase;letter-spacing:.04em">Ofertas cerca de ti</div>
${!rs.disponible ? '<div class="msg warn">No recibes ofertas mientras no estés disponible.</div>' : ofertas.length ? ofertas.map((r, i) => `<div class="card" style="padding:14px">${i ? '' : mk(2)}<div class="row" style="justify-content:space-between">${chip(prio(r), NOMBRE[prio(r)])}<b>${km(r.cod)} km</b></div><div style="margin:8px 0 4px;font-weight:700">${esc(r.desc.length > 44 ? r.desc.slice(0, 42) + '…' : r.desc)} · ${esc(r.barrio)}</div><div class="tag">Confirmado por veterinario hace ${espera(r.hist[r.hist.length - 1][0])}</div><div class="row" style="margin-top:10px"><button class="btn pri" data-act="aceptar" data-cod="${r.cod}" style="flex:1;justify-content:center"${act ? ' disabled title="Ya tienes un rescate activo (RN-08)"' : ''}>Aceptar rescate</button></div></div>`).join('') + (act ? '<div class="tag">Ya tienes un rescate activo: termínalo o libéralo para aceptar otro (RN-08).</div>' : '')
        : '<div class="msg ok">No hay rescates pendientes por ahora. Cuando un veterinario confirme un caso crítico o alto, aparecerá aquí.</div>'}`, '1. Ofertas de rescate');
    const pasos = act ? [['Aceptado · ' + hora(ultimoHito(act, 'Rescatista en camino')), 'ok'], ['En camino', act.estado === 'rescate' ? 'now' : 'ok'], ['En el sitio', act.estado === 'sitio' ? 'now' : '']] : [];
    const p2 = phone('Rescate asignado', act ? `
<div class="map" style="position:relative">${mk(3)}<span class="pin" style="left:62%;top:30%;background:#9B1C1C"></span><span class="pin" style="left:${act.estado === 'sitio' ? 58 : 22}%;top:${act.estado === 'sitio' ? 36 : 66}%;background:#0F6B5E"></span></div>
<div class="card" style="padding:14px"><div class="row" style="justify-content:space-between"><b class="mono">${act.cod}</b>${chip(prio(act), NOMBRE[prio(act)])}</div><div class="tag" style="margin-top:4px">${esc(act.barrio)} (ubicación aproximada) · ${km(act.cod)} km</div></div>
<div class="card" style="padding:14px">${mk(4)}<div class="tl">${pasos.map(([t, c]) => `<div class="${c}"><span>${c === 'now' ? `<b>${t}</b>` : t}</span></div>`).join('')}</div></div>
<button class="btn pri" data-act="llegue" style="justify-content:center"${act.estado === 'sitio' ? ' disabled' : ''}>${act.estado === 'sitio' ? 'Ya estás en el sitio' : 'Llegué al sitio'}</button>
<button class="btn" data-act="liberar" style="justify-content:center;position:relative">${mk(5)}Liberar rescate</button>` : `<div class="vacio">${dog('#B07A4A', '#6E4526', '#E8F1EA')}<b>Sin rescate activo</b><span>Acepta una oferta en la pantalla 1.</span></div>`, '2. Rescate en curso');
    const p3 = phone('Resultado del rescate', `
<div style="font-weight:800">¿Cómo terminó el rescate?</div>
<div class="stack" style="position:relative">${mk(6)}${Object.entries(RES).map(([k, t]) => `<button class="in row opt${S.draft.res === k ? ' on' : ''}" data-act="res" data-v="${k}" aria-pressed="${S.draft.res === k}">${ic({ trasladado: 'home', sitio: 'heart', noencontrado: 'search', fallecido: 'doc' }[k], 18)} ${S.draft.res === k ? `<b>${t}</b>` : t}</button>`).join('')}</div>
<label class="f">Nota (opcional)<textarea class="in area" data-bind="nota" style="min-height:70px" placeholder="Ej.: fractura en pata trasera, consciente">${esc(S.draft.nota)}</textarea></label>
<button class="btn pri" data-act="resultado" style="justify-content:center;padding:13px">Registrar resultado</button>${msg(S.msgRes)}
<div class="card" style="padding:12px 14px">${mk(7)}<b>Este mes:</b> ${rs.mes} rescates · tiempo medio de llegada 18 min</div>`, '3. Registrar resultado');
    return `<div class="phones">${p1}${p2}${p3}</div>`;
  };

  /* ---------- 4. Acciones ---------- */
  const avisar = (txt, tipo) => {
    const t = document.getElementById('toast');
    t.textContent = txt; t.className = 'toast show ' + (tipo || '');
    clearTimeout(avisar.t); avisar.t = setTimeout(() => { t.className = 'toast'; }, 4200);
  };
  const cambiarRol = (id, vista) => {
    st.rol = id; draw();
    if (vista) requestAnimationFrame(() => { const v = document.querySelector(`.vista[data-id="${vista}"]`); if (v) v.scrollIntoView({ behavior: 'smooth', block: 'start' }); });
  };
  const A = {
    gps() { S.draft.ubic = 'Barrio San Rafael · GPS ±12 m'; },
    avisos() { S.draft.avisos = !S.draft.avisos; },
    enviar() {
      const d = S.draft, e = {};
      if (d.desc.trim().length < MIN_CARACTERES) e.desc = `Describe un poco más: mínimo ${MIN_CARACTERES} caracteres (RN-01).`;
      if (!d.ubic.trim()) e.ubic = 'Indica la ubicación o usa el GPS (RN-01).';
      const v = VIDEOS[d.video];
      if (v && (v.s > 60 || v.mb > 50)) e.video = 'El video supera 60 s. Recórtalo o envía el reporte sin video; tu texto no se pierde.';
      S.errores = e;
      if (Object.keys(e).length) { avisar('Revisa los campos marcados.', 'err'); return; }
      const t = triaje(d.desc, S.iaCaida);
      const r = { cod: nuevoCodigo(), desc: d.desc.trim(), barrio: d.ubic.replace(/^Barrio\s+/i, '').replace(/ · GPS.*$/, '').trim(), video: v, creado: ahora(), p: t.p, conf: t.conf, ev: t.ev, triaje: t.triaje,
        estado: 'pendiente', confirmada: null, just: '', rescatista: null, resultado: null, hist: [[ahora(), 'Recibido']] };
      S.reportes.push(r); S.ultimo = r.cod; S.sel = r.cod; S.draft.consultaIn = r.cod;
      S.draft.desc = ''; S.draft.ubic = ''; S.draft.video = 'no';
      log(`Ciudadano envió ${r.cod}; triaje: ${t.triaje === 'sin' ? 'sin clasificar (falla segura → alta)' : NOMBRE[t.p].toLowerCase() + ' con confianza ' + t.conf.toFixed(2).replace('.', ',')}`);
      avisar(`Reporte enviado. Código ${r.cod}. Ya está en la cola del veterinario.`, 'ok');
    },
    copiar() { try { navigator.clipboard.writeText(S.ultimo); avisar('Código copiado.', 'ok'); } catch (e) { avisar('Copia el código: ' + S.ultimo); } },
    verestado() { S.draft.consultaIn = S.ultimo; S.consulta = S.ultimo; },
    consultar() { S.consulta = (S.draft.consultaIn || '').toUpperCase().replace(/\s+/g, ''); },
    sel(el) { S.sel = el.dataset.cod; S.ajustar = false; S.errores = {}; },
    ajustar() { S.ajustar = !S.ajustar; S.errores = {}; },
    confirmar(el) { confirmarCon(el.dataset.cod, null); },
    guardarajuste(el) {
      if (S.draft.just.trim().length < 10) { S.errores = { just: 'Escribe por qué cambias la prioridad (mínimo 10 caracteres, RN-16).' }; return; }
      confirmarCon(el.dataset.cod, S.draft.nueva, S.draft.just.trim());
    },
    ir(el) { cambiarRol(st.rol, el.dataset.to); return 'nodraw'; },
    guardaringreso() {
      const d = S.draft, e = {}; S.msgIng = null;
      if (!d.nombre.trim()) e.nombre = 'La ficha clínica exige un nombre provisional.';
      if (!d.salud.trim()) e.salud = 'La ficha clínica exige el estado de salud (RF-06).';
      S.errores = e;
      if (Object.keys(e).length) { S.msgIng = { t: 'err', x: 'Faltan datos obligatorios de la ficha clínica.' }; return; }
      const esp = S.espacios.find(x => x[0] === d.espacio), [oc, cap] = ocupacion();
      if (esp[1] >= esp[2] || oc >= cap) { S.msgIng = { t: 'err', x: `<b>Sin cupo en ${esp[0]}.</b> El ingreso no se guardó (RN-04, error 409).` }; avisar('Ingreso rechazado: no hay cupo.', 'err'); return; }
      const antes = oc; esp[1] += 1;
      const m = /^Rescate (\w+)/.exec(d.origen); if (m && buscar(m[1])) buscar(m[1]).ingresado = true;
      log(`Coordinador registró el ingreso de ${d.nombre.trim()} (${d.especie.toLowerCase()}) en ${esp[0]}; ocupación ${antes}/${cap} → ${antes + 1}/${cap}`);
      const pct = (antes + 1) / cap;
      S.msgIng = { t: 'ok', x: `<b>${esc(d.nombre.trim())}</b> quedó registrado en ${esp[0]}. Ocupación del refugio: ${antes + 1}/${cap} (${Math.floor(pct * 100)} %).` };
      if (pct >= ALERTA_OCUPACION) { log(`Alerta de ocupación enviada a coordinadores (${Math.floor(pct * 100)} %)`); avisar(`Ingreso guardado. Alerta: ocupación en ${Math.floor(pct * 100)} % (RN-04).`, 'warn'); }
      else avisar('Ingreso guardado.', 'ok');
      Object.assign(d, { nombre: '', edad: '', salud: '', trat: '', vac: '', est: '', origen: 'Entrega voluntaria' });
    },
    limpiaringreso() { Object.assign(S.draft, { nombre: '', edad: '', salud: '', trat: '', vac: '', est: '' }); S.errores = {}; S.msgIng = null; },
    egreso() {
      const esp = S.espacios.find(x => x[0] === S.draft.espacio); if (!esp || !esp[1]) return;
      esp[1] -= 1; log(`Coordinador registró un egreso en ${esp[0]} (adopción o traslado); se liberó un cupo`);
      S.msgIng = { t: 'ok', x: `Se liberó un cupo en ${esp[0]} (${esp[1]}/${esp[2]}).` };
    },
    disponible() { S.resc.disponible = !S.resc.disponible; },
    aceptar(el) {
      const r = buscar(el.dataset.cod);
      if (S.resc.activo) { avisar('Ya tienes un rescate activo (RN-08).', 'err'); return; }
      if (!r || r.estado !== 'confirmado') { avisar('Otro rescatista ya tomó este rescate.', 'err'); return; }
      r.estado = 'rescate'; r.rescatista = 'yo'; r.hist.push([ahora(), 'Rescatista en camino']); S.resc.activo = r.cod; S.msgRes = null;
      log(`Rescatista aceptó ${r.cod}`); avisar(`Rescate ${r.cod} aceptado. El ciudadano ya ve “Rescatista en camino”.`, 'ok');
    },
    llegue() { const r = buscar(S.resc.activo); if (!r) return; r.estado = 'sitio'; r.hist.push([ahora(), 'Rescatista en el sitio']); log(`Rescatista llegó al sitio de ${r.cod}`); },
    liberar() {
      const r = buscar(S.resc.activo); if (!r) return;
      r.estado = 'confirmado'; r.rescatista = null; r.hist.push([ahora(), 'Rescate liberado: se ofrece de nuevo']); S.resc.activo = null;
      log(`Rescatista liberó ${r.cod}; vuelve a ofrecerse (RN-08)`); avisar('Rescate liberado: vuelve a la lista de ofertas.', 'warn');
    },
    res(el) { S.draft.res = el.dataset.v; },
    resultado() {
      const r = buscar(S.resc.activo);
      if (!r) { S.msgRes = { t: 'err', x: 'No tienes un rescate activo.' }; return; }
      if (r.estado !== 'sitio') { S.msgRes = { t: 'warn', x: 'Primero marca <b>Llegué al sitio</b>.' }; return; }
      r.estado = 'atendido'; r.resultado = S.draft.res; r.hist.push([ahora(), RES[S.draft.res]]); S.resc.activo = null; S.resc.mes += 1;
      S.msgRes = { t: 'ok', x: `Resultado registrado: ${RES[S.draft.res]}.` }; S.draft.nota = '';
      if (S.draft.res === 'trasladado') { S.draft.origen = 'Rescate ' + r.cod + ' · ' + r.barrio; avisar('Resultado registrado. El coordinador ya ve el animal pendiente de ingreso.', 'ok'); }
      log(`Rescatista registró el resultado de ${r.cod}: ${RES[S.draft.res].toLowerCase()}`);
    }
  };
  function confirmarCon(cod, nueva, just) {
    const r = buscar(cod); if (!r || r.estado !== 'pendiente') return;
    const sug = r.triaje === 'sin' ? 'alt' : r.p, final = nueva || sug;
    r.confirmada = final; r.just = just || ''; r.estado = 'confirmado'; r.hist.push([ahora(), 'Revisado por el veterinario']);
    S.ajustar = false; S.draft.just = ''; S.errores = {};
    log(nueva && nueva !== sug ? `Veterinaria ajustó ${cod} de ${NOMBRE[sug].toLowerCase()} a ${NOMBRE[final].toLowerCase()}: “${just}”` : `Veterinaria confirmó ${cod} como ${NOMBRE[final].toLowerCase()}`);
    avisar(['cri', 'alt'].includes(final) ? `Prioridad ${NOMBRE[final].toLowerCase()} confirmada. Se avisó a los rescatistas disponibles (RF-05).` : `Prioridad ${NOMBRE[final].toLowerCase()} confirmada. El refugio programará la atención.`, 'ok');
  }

  /* ---------- 5. Conexión con el visor ---------- */
  const sc = document.getElementById('sc');
  sc.addEventListener('click', e => {
    const el = e.target.closest('[data-act]'); if (!el || !sc.contains(el) || el.disabled) return;
    e.preventDefault();
    const r = A[el.dataset.act] && A[el.dataset.act](el);
    guardar(); if (r !== 'nodraw') draw();
  });
  sc.addEventListener('keydown', e => {
    if ((e.key === 'Enter' || e.key === ' ') && e.target.matches('tr[data-act]')) { e.preventDefault(); e.target.click(); }
    if (e.key === 'Enter' && e.target.matches('input[data-bind="consultaIn"]')) { e.preventDefault(); A.consultar(); guardar(); draw(); }
  });
  sc.addEventListener('input', e => {
    const k = e.target.dataset && e.target.dataset.bind; if (!k) return;
    S.draft[k] = e.target.value; if (S.errores[k]) { delete S.errores[k]; }
    if (k === 'desc') { const c = document.getElementById('cnt'); if (c) c.textContent = `Mínimo 20 caracteres · ${e.target.value.trim().length}/500`; }
    guardar();
    if (e.target.hasAttribute('data-redraw')) draw();
  });

  // Barra de demostración, recorrido guiado y avisos
  const css = document.createElement('style');
  css.textContent = `
.scr input.in,.scr select.in,.scr textarea.in{width:100%;font:inherit;font-weight:500;font-size:14.5px;color:var(--p-ink)}
.scr textarea.in{resize:vertical;line-height:1.35}
.scr button.btn,.scr button.in,.scr button.tg,.scr button.lnk{font-family:inherit;cursor:pointer}
.scr button.btn[disabled]{opacity:.45;cursor:not-allowed}
.scr button.tg{background:none;border:0;padding:0;color:inherit;text-align:left}
.scr button.lnk{background:none;border:0;padding:0;color:var(--p-teal);font-weight:700;font-size:13px;text-decoration:underline}
.scr .card h4 button.lnk{margin-left:auto}
.scr button.opt{text-align:left;width:100%}
.scr button.opt.on{border-color:var(--p-teal);border-width:2px}
.scr .sw.off{background:#C9CFCC}.scr .sw.off:after{right:auto;left:3px}
.scr tr[data-act]{cursor:pointer}.scr tr[data-act]:hover td{background:#F7FAF9}
.scr .fe{color:var(--c-cri);font-size:12.5px;font-weight:700}
.scr .msg{border-radius:10px;padding:10px 12px;font-size:13.5px;margin-top:10px;border:1px solid}
.scr .msg.ok{background:#EEF7F3;border-color:#BFDCD1;color:#0F4F47}
.scr .msg.err{background:#FFF1EE;border-color:#F2B8B0;color:#8A1C1C}
.scr .msg.warn{background:#FFF8EB;border-color:#F4D9B5;color:#6F4A00}
.scr .vacio{display:flex;flex-direction:column;align-items:center;text-align:center;gap:8px;padding:30px 10px;color:var(--p-mute);font-size:14px}
.scr .vacio svg{width:110px;height:110px}.scr .vacio b{color:var(--p-ink);font-size:16px}
.wf .scr .msg{background:#fff;border:2px dashed #777;color:#2B2B2B}
.wf .scr .sw.off{background:#ddd}
.demo{display:flex;flex-wrap:wrap;align-items:center;gap:10px;background:var(--panel);border:1px solid var(--line);border-left:5px solid var(--accent-2);border-radius:12px;padding:12px 14px;font-size:14px}
.demo p{margin:0;flex:1 1 360px;color:var(--ink)}
.demo button{border:1px solid var(--line);background:var(--panel);color:var(--ink);font:600 13.5px var(--f-ui);padding:7px 12px;border-radius:999px;cursor:pointer}
.demo button[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:var(--panel)}
.guia{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 16px}
.guia ol{margin:6px 0 0;padding-left:20px;display:grid;gap:6px;font-size:14px}
.guia button{border:0;background:none;color:var(--accent);font:700 13.5px var(--f-ui);cursor:pointer;text-decoration:underline;padding:0 4px}
.toast{position:fixed;left:50%;bottom:22px;transform:translate(-50%,30px);opacity:0;pointer-events:none;background:#16282A;color:#fff;font:600 14px var(--f-ui);padding:12px 18px;border-radius:12px;max-width:min(560px,calc(100vw - 32px));box-shadow:0 8px 24px rgba(0,0,0,.2);transition:opacity .2s,transform .2s;z-index:50}
.toast.show{opacity:1;transform:translate(-50%,0)}
.toast.ok{background:#0F4F47}.toast.err{background:#8A1C1C}.toast.warn{background:#7A4B00}
body.shot .demo,body.shot .guia,body.shot .toast{display:none}`;
  document.head.appendChild(css);
  const p = document.querySelector('header.top p');
  if (p) p.textContent = 'Prototipo de la Semana 3: cada rol tiene su dashboard en wireframe y mockup. En los roles Ciudadano, Veterinario, Coordinador y Rescatista los botones funcionan con datos simulados: puedes recorrer el flujo completo de una emergencia.';
  const barra = document.createElement('div');
  barra.className = 'demo';
  barra.innerHTML = `<p><b>Prototipo interactivo.</b> Los botones funcionan con datos simulados en tu navegador; nada se envía a un servidor. Las reglas son las mismas del código real v0.1.0.</p>
<button id="d-guia" aria-pressed="false">Recorrido guiado</button><button id="d-ia" aria-pressed="false">Simular falla de la IA</button><button id="d-reset">Reiniciar datos</button>`;
  const guia = document.createElement('div');
  guia.className = 'guia'; guia.hidden = true;
  guia.innerHTML = `<b>Recorrido de una emergencia (unos 3 minutos)</b><ol>
<li><button data-r="ciudadano">Ciudadano</button>: escribe “perro atropellado en la calle 10, no se levanta”, pulsa <b>Usar mi GPS</b> y <b>Enviar reporte</b>. Copia tu código.</li>
<li><button data-r="veterinario">Veterinario</button>: el reporte aparece primero en la cola como crítico. Revisa las evidencias y pulsa <b>Confirmar</b> (o <b>Ajustar</b>, que exige justificación).</li>
<li><button data-r="rescatista">Rescatista</button>: acepta el rescate, pulsa <b>Llegué al sitio</b> y registra el resultado <b>Trasladado a refugio</b>.</li>
<li><button data-r="ciudadano">Ciudadano</button>: en <b>Consultar</b> ve cómo avanzó su reporte, sin datos personales.</li>
<li><button data-r="coordinador">Coordinador</button>: registra el ingreso del animal. Mira la alerta del 90 % y prueba un espacio lleno, como Aislamiento.</li>
<li>Prueba también: un texto de menos de 20 caracteres, el video de 1:15, “perro muy flaco” (requiere revisión) y <b>Simular falla de la IA</b> (sale alta, sin clasificar).</li></ol>`;
  const toast = document.createElement('div'); toast.id = 'toast'; toast.className = 'toast'; toast.setAttribute('role', 'status'); toast.setAttribute('aria-live', 'polite');
  const meta = document.getElementById('meta');
  meta.parentNode.insertBefore(barra, meta); meta.parentNode.insertBefore(guia, meta); document.body.appendChild(toast);
  const pintarBarra = () => { document.getElementById('d-ia').setAttribute('aria-pressed', S.iaCaida); document.getElementById('d-guia').setAttribute('aria-pressed', S.guia); guia.hidden = !S.guia; };
  document.getElementById('d-guia').onclick = () => { S.guia = !S.guia; guardar(); pintarBarra(); };
  document.getElementById('d-ia').onclick = () => { S.iaCaida = !S.iaCaida; guardar(); pintarBarra(); avisar(S.iaCaida ? 'Falla simulada: los próximos reportes quedarán “sin clasificar” con prioridad alta (RN-03).' : 'El clasificador volvió a responder.', S.iaCaida ? 'warn' : 'ok'); };
  document.getElementById('d-reset').onclick = () => { S = estadoInicial(); guardar(); pintarBarra(); draw(); avisar('Datos de la demostración reiniciados.', 'ok'); };
  guia.addEventListener('click', e => { const b = e.target.closest('button[data-r]'); if (b) cambiarRol(b.dataset.r); });
  pintarBarra();
  draw();
})();
