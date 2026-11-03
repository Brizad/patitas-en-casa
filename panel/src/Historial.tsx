import { useCallback, useEffect, useState } from "react";
import { FilaHistorial, NOMBRE_ACCION, NOMBRE_ESTADO, fechaLocal, historial } from "./apiHistorial";
import { NOMBRE_PRIORIDAD, textoError } from "./mensajes";

/** Reportes que este veterinario confirmó, ajustó o descartó, del más reciente al más viejo. */
export default function Historial({ token }: { token: string }) {
  const [filas, setFilas] = useState<FilaHistorial[]>([]);
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(true);

  const recargar = useCallback(async () => {
    setCargando(true);
    try {
      setFilas(await historial(token));
      setError("");
    } catch (e) {
      setError(textoError(e));
    } finally {
      setCargando(false);
    }
  }, [token]);

  useEffect(() => { void recargar(); }, [recargar]);

  const prioridad = (p: string | null) => (p ? NOMBRE_PRIORIDAD[p] : "—");
  return (
    <section className="pagina">
      <div className="ds-tarjeta">
        <div className="fila-titulo">
          <h2>Historial</h2>
          <button onClick={() => void recargar()} disabled={cargando}>Actualizar</button>
        </div>
        {error && <p className="ds-msg ds-msg--error" role="alert">{error}</p>}
        {!cargando && !error && filas.length === 0 && (
          <p className="ds-vacio">Aún no has confirmado ni descartado reportes.</p>)}
        {filas.length > 0 && (
          <div className="ds-tabla-caja" tabIndex={0} role="region" aria-label="Tabla del historial"><table className="ds-tabla">
            <thead><tr><th>Código</th><th>Fecha</th><th>Acción</th><th>Sugerida</th>
              <th>Final</th><th>Justificación</th><th>Estado actual</th></tr></thead>
            <tbody>
              {filas.map((f) => (
                <tr key={`${f.codigo}-${f.fecha}`}>
                  <td><code>{f.codigo}</code></td>
                  <td>{fechaLocal(f.fecha)}</td>
                  <td>{NOMBRE_ACCION[f.accion]}</td>
                  <td>{prioridad(f.prioridad_sugerida)}</td>
                  <td>{prioridad(f.prioridad_final)}</td>
                  <td>{f.justificacion ?? "—"}</td>
                  <td>{f.estado ? (NOMBRE_ESTADO[f.estado] ?? f.estado) : "—"}</td>
                </tr>))}
            </tbody>
          </table></div>)}
      </div>
    </section>
  );
}
