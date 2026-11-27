import { useCallback, useEffect, useRef, useState } from "react";
import { Cuenta, ReporteEnCola, cola, descartar } from "./api";
import { FilaHistorial, NOMBRE_ACCION, historial } from "./apiHistorial";
import {
  NOMBRE_NIVEL, colorEspera, esDeHoy, fechaExacta, textoEspecie, textoZona,
} from "./bandejas";
import Cargando from "./Cargando";
import Confirmar, { resumenAvisos } from "./Confirmar";
import Descartar from "./Descartar";
import { Lugar } from "./MiniMapa";
import VideoDelReporte from "./VideoDelReporte";
import {
  NOMBRE_PRIORIDAD, etiquetaEstado, evidenciaLegible, explicarSugerencia, faltaJustificacion,
  haceCuanto, nombreModelo, textoError,
} from "./mensajes";

type Pestana = "revisar" | "atrasados" | "hoy";

/** Cola priorizada (RF-04) con el orden único del servidor (#496): nivel y luego el más antiguo.
 *  Lo que lleva más de 72 h sin avanzar va en «Atrasados»; el detalle muestra las evidencias. */
export default function Cola({ token, cuenta }: { token: string; cuenta: Cuenta }) {
  const [reportes, setReportes] = useState<ReporteEnCola[]>([]);
  const [elegido, setElegido] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(true);
  const titulo = useRef<HTMLHeadingElement>(null);
  const [aviso, setAviso] = useState<{ codigo: string; texto: string; estado?: string } | null>(
    null);
  const [pestana, setPestana] = useState<Pestana>("revisar");
  const [archivando, setArchivando] = useState<string | null>(null);

  const recargar = useCallback(async () => {
    setCargando(true);
    try {
      setReportes(await cola(token));
      setError("");
    } catch (e) {
      setError(textoError(e));
    } finally {
      setCargando(false);
    }
  }, [token]);

  useEffect(() => { void recargar(); }, [recargar]);
  const porRevisar = reportes.filter((r) => !r.atrasado);
  const atrasados = reportes.filter((r) => r.atrasado);
  const visibles = pestana === "atrasados" ? atrasados : porRevisar;
  const detalle = reportes.find((r) => r.codigo === elegido) ?? null;
  const tituloDetalle = useRef<HTMLHeadingElement>(null);
  // Prueba de punta a punta (#121): en el celular el detalle queda debajo de la lista; al
  // elegir un reporte el foco (y la vista) van al detalle, donde están las acciones.
  useEffect(() => {
    if (elegido) {
      tituloDetalle.current?.focus();
      tituloDetalle.current?.scrollIntoView?.({ block: "start" });
    }
  }, [elegido]);

  function terminado(codigo: string, texto: string) {
    setAviso({ codigo, texto });
    setElegido(null);
    void recargar();
    // D-08: con teclado, el foco vuelve a la cola en vez de perderse al cerrar el detalle.
    titulo.current?.focus();
  }

  return (
    <section className="cola">
      <div className="lista ds-tarjeta">
        <div className="fila-titulo">
          <h2 id="cola" tabIndex={-1} ref={titulo}>Cola de triaje</h2>
          <button onClick={() => void recargar()} disabled={cargando}>Actualizar</button>
        </div>
        {/* #496: resumen con los datos reales de la cola. */}
        <p className="resumen-cola">Por revisar: <b>{porRevisar.length}</b> · Urgentes:{" "}
          <b>{porRevisar.filter((r) => r.nivel === "urgente").length}</b> · Atrasados: <b>{atrasados.length}</b></p>
        <div className="pestanas-bandeja" role="tablist" aria-label="Bandeja del veterinario">
          {([["revisar", "Por revisar", porRevisar.length], ["atrasados", "Atrasados", atrasados.length],
            ["hoy", "Revisados hoy", null]] as [Pestana, string, number | null][]).map(([id, nombre, n]) => (
            <button key={id} role="tab" aria-selected={pestana === id} onClick={() => setPestana(id)}>
              {nombre}{n !== null && <span className={`contador${id === "atrasados" && n > 0 ? " contador--rojo" : ""}`}>{n}</span>}
            </button>))}
        </div>
        {error && <p className="ds-msg ds-msg--error" role="alert">{error}</p>}
        {aviso && (
          <div className="ds-msg ds-msg--ok" role="status">
            <p><code>{aviso.codigo}</code>: {aviso.texto}</p>
            {aviso.estado && <p>{aviso.estado}</p>}
            <button onClick={async () => setAviso({ ...aviso,
              estado: await resumenAvisos(token, aviso.codigo) })}>
              Ver estado de los avisos</button>
          </div>)}
        {pestana === "hoy" ? <RevisadosHoy token={token} /> : (
          <>
            {cargando && !error && reportes.length === 0 && <Cargando que="la cola" />}
            {pestana === "atrasados" && atrasados.length > 0 && (
              <p className="ds-msg aviso-atrasados">Estos casos llevan más de 3 días sin avanzar. Revísalos o archívalos.</p>)}
            {!cargando && !error && visibles.length === 0 && (pestana === "revisar" ? (
              <p className="ds-vacio"><img src="/diseno/ilustraciones/sin-reportes.svg" alt="" width="160" height="120" /><strong>No hay reportes por confirmar.</strong>
                Cuando un ciudadano envíe uno, aparecerá aquí ordenado por prioridad.</p>)
              : <p className="ds-vacio"><strong>No hay casos atrasados.</strong></p>)}
            <ul>
              {visibles.map((r) => (
                <li key={r.codigo}>
                  <TarjetaCaso r={r} elegido={r.codigo === elegido} alElegir={() => setElegido(r.codigo)} />
                  {r.atrasado && cuenta.rol === "veterinario" && (
                    <div className="acciones acciones-atrasado">
                      <button onClick={() => setElegido(r.codigo)}>Revisar ahora</button>
                      <button onClick={() => setArchivando(archivando === r.codigo ? null : r.codigo)}
                        aria-expanded={archivando === r.codigo}>Archivar: no se pudo verificar</button>
                    </div>)}
                  {archivando === r.codigo && (
                    <Archivar token={token} codigo={r.codigo} alCancelar={() => setArchivando(null)}
                      alTerminar={(texto) => { setArchivando(null); terminado(r.codigo, texto); }} />)}
                </li>))}
            </ul>
          </>)}
      </div>
      <div className={`detalle ds-tarjeta${detalle ? "" : " detalle--vacio"}`}>
        {!detalle ? <p className="ds-vacio"><strong>Elige un reporte de la lista.</strong>
          Verás qué pasó, dónde y cuándo, y podrás confirmar o ajustar su prioridad.</p> : (
          <>
            <div className="fila-titulo">
              <h2 tabIndex={-1} ref={tituloDetalle}>Reporte <code>{detalle.codigo}</code></h2>
              <span className={`ds-insignia ds-insignia--${detalle.prioridad}`}>
                {etiquetaEstado(detalle.estado, detalle.prioridad)}</span>
            </div>
            <p className="ds-suave" title={fechaExacta(detalle.creado_en)}>
              Reportado {haceCuanto(detalle.creado_en)} · {fechaExacta(detalle.creado_en)}
              {" "}· {textoEspecie(detalle.especie)} · {textoZona(detalle.ubicacion.comuna)}</p>
            <h3>Qué pasó</h3>
            <blockquote className="relato">{detalle.descripcion}</blockquote>
            <h3>Dónde</h3>
            <p>{detalle.ubicacion.direccion ?? (detalle.ubicacion.latitud !== null
              ? `GPS ${detalle.ubicacion.latitud}, ${detalle.ubicacion.longitud}` : "Sin dato")}
              {detalle.ubicacion.comuna ? ` · comuna ${detalle.ubicacion.comuna}` : ""}</p>
            <Lugar u={detalle.ubicacion} />
            <h3>Sugerencia del sistema</h3>
            {/* #432: anillo con la confianza del modelo; la decisión sigue siendo del veterinario. */}
            <div className="sugerencia">
              {detalle.confianza !== null && (
                <span className="anillo-confianza" aria-hidden="true"
                  style={{ "--grados": `${Math.round(detalle.confianza * 360)}deg` } as React.CSSProperties}>
                  <span>{Math.round(detalle.confianza * 100)}%</span></span>)}
              <p>{explicarSugerencia(detalle.estado, detalle.prioridad, detalle.confianza,
                detalle.version_modelo)}</p>
            </div>
            {detalle.posibles_duplicados.length > 0 && (
              <p className="ds-msg ds-msg--ok">Posible duplicado de {detalle.posibles_duplicados.join(", ")}:
                {" "}reportado a menos de 200 m y 2 horas.</p>)}
            <h3>En qué se basa</h3>
            {detalle.evidencias.length === 0 ? <p className="ds-vacio">Sin evidencias.</p> : (
              <ul className="evidencias evidencias--chips">{detalle.evidencias.map((ev) => (
                <li key={ev}>{evidenciaLegible(ev)}</li>))}</ul>)}
            {detalle.version_modelo && (
              <p className="ds-suave">Sugerencia hecha con {nombreModelo(detalle.version_modelo)}.</p>)}
            {detalle.video_segundos !== null
              ? <VideoDelReporte token={token} codigo={detalle.codigo} />
              : <p className="ds-suave">Este reporte no trae video.</p>}
            {cuenta.rol === "veterinario" ? (
              <>
                <Confirmar key={detalle.codigo} token={token} reporte={detalle}
                  alTerminar={(texto) => terminado(detalle.codigo, texto)} />
                <Descartar key={`d-${detalle.codigo}`} token={token} reporte={detalle}
                  alTerminar={(texto) => terminado(detalle.codigo, texto)} />
              </>
            ) : (
              <p className="ds-suave">Solo un veterinario puede confirmar la prioridad.</p>)}
          </>)}
      </div>
    </section>
  );
}

/** #496: nivel con color, animal y estado, zona, video y la espera con su color. */
function TarjetaCaso({ r, elegido, alElegir }: { r: ReporteEnCola; elegido: boolean; alElegir: () => void }) {
  const conVideo = r.video_segundos !== null;
  return (
    <button className={`item tarjeta-caso item--${r.prioridad}${elegido ? " activo" : ""}`}
      onClick={alElegir} aria-pressed={elegido}>
      <span className={`nivel nivel--${r.nivel}`}>{NOMBRE_NIVEL[r.nivel]}</span>
      {/* Los reportes no traen foto: si trae video se indica; si no, «—» (sin inventar). */}
      <span className="miniatura" title={conVideo ? "Trae video" : "Sin foto ni video"}>
        {conVideo ? <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l11-7z" /></svg> : "—"}
        <span className="visualmente-oculto">{conVideo ? "Con video" : "Sin foto"}</span></span>
      <span className="caso-datos">
        <b>{textoEspecie(r.especie)}{r.estado_animal ? ` · ${r.estado_animal}` : ""}</b>
        <span className="ds-suave">{textoZona(r.ubicacion.comuna)} · <code>{r.codigo}</code>
          {r.estado === "requiere_revision" || r.estado === "sin_clasificar"
            ? ` · ${etiquetaEstado(r.estado, r.prioridad)}` : ""}</span>
        <span className="resumen">{r.descripcion}</span>
      </span>
      <span className={`espera espera--${colorEspera(r.creado_en)}`} title={fechaExacta(r.creado_en)}>
        {haceCuanto(r.creado_en)}</span>
      {r.posibles_duplicados.length > 0 && (
        <span className="ds-insignia ds-insignia--info">posible duplicado</span>)}
    </button>
  );
}

/** #496: archivar un caso atrasado que no se pudo verificar, con motivo obligatorio (RN-16, D-07). */
function Archivar({ token, codigo, alCancelar, alTerminar }: {
  token: string; codigo: string; alCancelar: () => void; alTerminar: (texto: string) => void;
}) {
  const [motivo, setMotivo] = useState("");
  const [error, setError] = useState("");
  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    if (faltaJustificacion("critica", "alta", motivo)) {
      setError("Escribe el motivo: 10 caracteres o más, con palabras.");
      return;
    }
    try {
      await descartar(token, codigo, "archivado", motivo.trim());
      alTerminar("Archivado: no se pudo verificar. El ciudadano lo verá cerrado.");
    } catch (err) {
      setError(textoError(err));
    }
  }
  return (
    <form className="ajuste" onSubmit={enviar} noValidate>
      <label>Motivo del archivo (obligatorio)
        <textarea value={motivo} onChange={(e) => setMotivo(e.target.value)} rows={2} /></label>
      {error && <p className="ds-msg ds-msg--error" role="alert">{error}</p>}
      <div className="acciones">
        <button className="principal">Archivar</button>
        <button type="button" onClick={alCancelar}>Cancelar</button>
      </div>
    </form>
  );
}

/** #496: lo que este veterinario decidió hoy (día de Colombia). */
function RevisadosHoy({ token }: { token: string }) {
  const [filas, setFilas] = useState<FilaHistorial[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    historial(token).then((h) => setFilas(h.filter((f) => esDeHoy(f.fecha))))
      .catch((e) => setError(textoError(e)));
  }, [token]);
  if (error) return <p className="ds-msg ds-msg--error" role="alert">{error}</p>;
  if (!filas) return <Cargando que="lo revisado hoy" />;
  if (filas.length === 0) return <p className="ds-vacio"><strong>Hoy aún no has revisado casos.</strong></p>;
  return (
    <ul className="lista-simple revisados-hoy">
      {filas.map((f) => (
        <li key={`${f.codigo}-${f.fecha}`}><code>{f.codigo}</code> · {NOMBRE_ACCION[f.accion]}
          {f.prioridad_final ? ` · ${NOMBRE_PRIORIDAD[f.prioridad_final]}` : ""}
          {" "}<span className="ds-suave" title={fechaExacta(f.fecha)}>{haceCuanto(f.fecha)}</span></li>))}
    </ul>
  );
}
