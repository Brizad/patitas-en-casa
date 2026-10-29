import { useCallback, useEffect, useRef, useState } from "react";
import { Cuenta, ReporteEnCola, cola } from "./api";
import Confirmar, { resumenAvisos } from "./Confirmar";
import Descartar from "./Descartar";
import { etiquetaEstado, textoError } from "./mensajes";

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

  function terminado(codigo: string, texto: string) {
    setAviso({ codigo, texto });
    setElegido(null);
    void recargar();
    // D-08: con teclado, el foco vuelve a la cola en vez de perderse al cerrar el detalle.
    titulo.current?.focus();
  }

  return (
    <section className="cola">
      <div className="lista tarjeta">
        <div className="fila-titulo">
          <h2 id="cola" tabIndex={-1} ref={titulo}>Cola de triaje</h2>
          <button onClick={() => void recargar()} disabled={cargando}>Actualizar</button>
        </div>
        {error && <p className="error" role="alert">{error}</p>}
        {aviso && (
          <div className="resultado" role="status">
            <p><code>{aviso.codigo}</code>: {aviso.texto}</p>
            {aviso.estado && <p>{aviso.estado}</p>}
            <button onClick={async () => setAviso({ ...aviso,
              estado: await resumenAvisos(token, aviso.codigo) })}>
              Ver estado de los avisos</button>
          </div>)}
        {!cargando && !error && reportes.length === 0 && (
          <p className="vacio">No hay reportes por confirmar.</p>)}
        <ul>
          {reportes.map((r) => (
            <li key={r.codigo}>
              <button className={r.codigo === elegido ? "item activo" : "item"}
                onClick={() => setElegido(r.codigo)} aria-pressed={r.codigo === elegido}>
                <code>{r.codigo}</code>
                <span className={`chip ${r.prioridad}`}>{etiquetaEstado(r.estado, r.prioridad)}</span>
                <span>{r.confianza === null ? "—" : r.confianza.toFixed(2)}</span>
                {r.posibles_duplicados.length > 0 && (
                  <span className="chip">posible duplicado</span>)}
              </button>
            </li>))}
        </ul>
      </div>
      <div className="detalle tarjeta">
        {!detalle ? <p className="vacio">Elige un reporte de la cola.</p> : (
          <>
            <h2>Reporte <code>{detalle.codigo}</code></h2>
            <p>Sugerida: <b>{etiquetaEstado(detalle.estado, detalle.prioridad)}</b>
              {detalle.confianza !== null && <> · confianza {detalle.confianza.toFixed(2)}</>}</p>
            {detalle.version_modelo && (
              <p className="nota">Sugerida por {detalle.version_modelo} (RF-20).</p>)}
            {detalle.posibles_duplicados.length > 0 && (
              <p className="resultado">Posible duplicado de {detalle.posibles_duplicados.join(", ")}:
                {" "}reportado a menos de 200 m y 2 horas (RF-17).</p>)}
            <h3>Evidencias del triaje</h3>
            {detalle.evidencias.length === 0 ? <p className="vacio">Sin evidencias.</p> : (
              <ol>{detalle.evidencias.map((ev) => <li key={ev}>{ev}</li>)}</ol>)}
            {cuenta.rol === "veterinario" ? (
              <>
                <Confirmar key={detalle.codigo} token={token} reporte={detalle}
                  alTerminar={(texto) => terminado(detalle.codigo, texto)} />
                <Descartar key={`d-${detalle.codigo}`} token={token} reporte={detalle}
                  alTerminar={(texto) => terminado(detalle.codigo, texto)} />
              </>
            ) : (
              <p className="nota">Solo un veterinario puede confirmar la prioridad (RN-06).</p>)}
          </>)}
      </div>
    </section>
  );
}
