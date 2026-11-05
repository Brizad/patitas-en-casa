import { useCallback, useEffect, useRef, useState } from "react";
import { Cuenta, ReporteEnCola, cola } from "./api";
import Confirmar, { resumenAvisos } from "./Confirmar";
import Descartar from "./Descartar";
import VideoDelReporte from "./VideoDelReporte";
import {
  enlaceMapa, etiquetaEstado, evidenciaLegible, explicarSugerencia, haceCuanto, nombreModelo,
  textoError,
} from "./mensajes";

/** Cola priorizada (RF-04): mismo orden que GET /cola; el detalle muestra las evidencias. */
export default function Cola({ token, cuenta }: { token: string; cuenta: Cuenta }) {
  const [reportes, setReportes] = useState<ReporteEnCola[]>([]);
  const [elegido, setElegido] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(true);
  const titulo = useRef<HTMLHeadingElement>(null);
  const [aviso, setAviso] = useState<{ codigo: string; texto: string; estado?: string } | null>(
    null);

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
        {error && <p className="ds-msg ds-msg--error" role="alert">{error}</p>}
        {aviso && (
          <div className="ds-msg ds-msg--ok" role="status">
            <p><code>{aviso.codigo}</code>: {aviso.texto}</p>
            {aviso.estado && <p>{aviso.estado}</p>}
            <button onClick={async () => setAviso({ ...aviso,
              estado: await resumenAvisos(token, aviso.codigo) })}>
              Ver estado de los avisos</button>
          </div>)}
        {!cargando && !error && reportes.length === 0 && (
          <p className="ds-vacio">No hay reportes por confirmar.</p>)}
        <ul>
          {reportes.map((r) => (
            <li key={r.codigo}>
              <button className={`item item--${r.prioridad}${r.codigo === elegido ? " activo" : ""}`}
                onClick={() => setElegido(r.codigo)} aria-pressed={r.codigo === elegido}>
                <code>{r.codigo}</code>
                <span className={`ds-insignia ds-insignia--${r.prioridad}`}>{etiquetaEstado(r.estado, r.prioridad)}</span>
                <span className="ds-suave">{haceCuanto(r.creado_en)}</span>
                <span className="resumen">{r.descripcion}</span>
                {r.posibles_duplicados.length > 0 && (
                  <span className="ds-insignia ds-insignia--info">posible duplicado</span>)}
              </button>
            </li>))}
        </ul>
      </div>
      <div className="detalle ds-tarjeta">
        {!detalle ? <p className="ds-vacio">Elige un reporte de la cola.</p> : (
          <>
            <div className="fila-titulo">
              <h2 tabIndex={-1} ref={tituloDetalle}>Reporte <code>{detalle.codigo}</code></h2>
              <span className={`ds-insignia ds-insignia--${detalle.prioridad}`}>
                {etiquetaEstado(detalle.estado, detalle.prioridad)}</span>
            </div>
            <p className="ds-suave" title={new Date(detalle.creado_en).toLocaleString()}>
              Reportado {haceCuanto(detalle.creado_en)} · {new Date(detalle.creado_en).toLocaleString()}</p>
            <h3>Qué pasó</h3>
            <blockquote className="relato">{detalle.descripcion}</blockquote>
            <h3>Dónde</h3>
            <p>{detalle.ubicacion.direccion ?? (detalle.ubicacion.latitud !== null
              ? `GPS ${detalle.ubicacion.latitud}, ${detalle.ubicacion.longitud}` : "Sin dato")}
              {detalle.ubicacion.comuna ? ` · comuna ${detalle.ubicacion.comuna}` : ""}
              {enlaceMapa(detalle.ubicacion) && <> · <a href={enlaceMapa(detalle.ubicacion) ?? undefined}
                target="_blank" rel="noopener noreferrer">Abrir en Google Maps</a></>}</p>
            <h3>Sugerencia del sistema</h3>
            <p className="ds-msg ds-msg--info">{explicarSugerencia(detalle.estado, detalle.prioridad,
              detalle.confianza, detalle.version_modelo)}</p>
            {detalle.posibles_duplicados.length > 0 && (
              <p className="ds-msg ds-msg--ok">Posible duplicado de {detalle.posibles_duplicados.join(", ")}:
                {" "}reportado a menos de 200 m y 2 horas (RF-17).</p>)}
            <h3>En qué se basa</h3>
            {detalle.evidencias.length === 0 ? <p className="ds-vacio">Sin evidencias.</p> : (
              <ul className="evidencias">{detalle.evidencias.map((ev) => (
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
              <p className="ds-suave">Solo un veterinario puede confirmar la prioridad (RN-06).</p>)}
          </>)}
      </div>
    </section>
  );
}
