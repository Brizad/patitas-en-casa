import { useCallback, useEffect, useState } from "react";
import { fechaLocal } from "./apiHistorial";
import {
  FilaRescate, NOMBRE_ESTADO_RESCATE, misRescates, textoLlegada, textoResultado,
} from "./apiMisRescates";
import { textoError } from "./mensajes";

/** Los rescates que este rescatista aceptó, del más reciente al más viejo. */
export default function MisRescates({ token }: { token: string }) {
  const [filas, setFilas] = useState<FilaRescate[]>([]);
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(true);

  const recargar = useCallback(async () => {
    setCargando(true);
    try {
      setFilas(await misRescates(token));
      setError("");
    } catch (e) {
      setError(textoError(e));
    } finally {
      setCargando(false);
    }
  }, [token]);

  useEffect(() => { void recargar(); }, [recargar]);

  return (
    <section className="pagina">
      <div className="ds-tarjeta">
        <div className="fila-titulo">
          <h2>Mis rescates</h2>
          <button onClick={() => void recargar()} disabled={cargando}>Actualizar</button>
        </div>
        {error && <p className="ds-msg ds-msg--error" role="alert">{error}</p>}
        {!cargando && !error && filas.length === 0 && (
          <p className="ds-vacio">Aún no has aceptado rescates.</p>)}
        {filas.length > 0 && (
          <table className="ds-tabla">
            <thead><tr><th>Código</th><th>Aceptado</th><th>Llegada</th><th>Resultado</th>
              <th>Estado actual</th></tr></thead>
            <tbody>
              {filas.map((f) => (
                <tr key={f.codigo}>
                  <td><code>{f.codigo}</code></td>
                  <td>{fechaLocal(f.aceptado_en)}</td>
                  <td>{textoLlegada(f)}</td>
                  <td>{textoResultado(f)}</td>
                  <td>{NOMBRE_ESTADO_RESCATE[f.estado]}</td>
                </tr>))}
            </tbody>
          </table>)}
      </div>
    </section>
  );
}
