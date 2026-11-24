import { useCallback, useEffect, useState } from "react";
import Cargando from "./Cargando";
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
        {cargando && !error && filas.length === 0 && <Cargando que="tus rescates" />}
        {!cargando && !error && filas.length === 0 && (
          <p className="ds-vacio"><img src="/diseno/ilustraciones/sin-rescates.svg" alt="" width="160" height="120" /><strong>Aún no has aceptado rescates.</strong>
            Acepta uno en «Ofertas y rescate actual»: aquí queda el registro de cada rescate.</p>)}
        {filas.length > 0 && (
          <div className="ds-tabla-caja" tabIndex={0} role="region" aria-label="Tabla de mis rescates"><table className="ds-tabla ds-tabla--tarjetas" role="table">
            <thead><tr role="row"><th role="columnheader">Código</th><th role="columnheader">Aceptado</th><th role="columnheader">Llegada</th><th role="columnheader">Resultado</th>
              <th role="columnheader">Estado actual</th></tr></thead>
            <tbody>
              {filas.map((f) => (
                <tr role="row" key={f.codigo}>
                  <td role="cell" data-etiqueta="Código"><code>{f.codigo}</code></td>
                  <td role="cell" data-etiqueta="Aceptado">{fechaLocal(f.aceptado_en)}</td>
                  <td role="cell" data-etiqueta="Llegada">{textoLlegada(f)}</td>
                  <td role="cell" data-etiqueta="Resultado">{textoResultado(f)}</td>
                  <td role="cell" data-etiqueta="Estado actual">{NOMBRE_ESTADO_RESCATE[f.estado]}</td>
                </tr>))}
            </tbody>
          </table></div>)}
      </div>
    </section>
  );
}
