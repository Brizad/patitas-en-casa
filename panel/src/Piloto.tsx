import { useCallback, useEffect, useState } from "react";
import {
  Invitacion, META_PORCENTAJE, META_SEGUNDOS, META_SUS, ResultadosPiloto, csvPiloto, invitar,
  resultadosPiloto, resumenPiloto,
} from "./apiPiloto";
import { textoError } from "./mensajes";

/** RNF-06 (#258): el administrador abre la PWA en modo prueba para cada participante y ve los
 *  resultados anónimos (P01, P02…). Los reportes de prueba no llegan a la cola. */
export default function Piloto({ token }: { token: string }) {
  const [datos, setDatos] = useState<ResultadosPiloto | null>(null);
  const [invitacion, setInvitacion] = useState<Invitacion | null>(null);
  const [error, setError] = useState("");

  const recargar = useCallback(async () => {
    try {
      setDatos(await resultadosPiloto(token));
    } catch (e) {
      setError(textoError(e));
    }
  }, [token]);
  useEffect(() => { void recargar(); }, [recargar]);

  async function nuevoParticipante() {
    setError("");
    try {
      const nueva = await invitar(token);
      setInvitacion(nueva);
      window.open(nueva.enlace, "_blank", "noopener");
      await recargar();
    } catch (e) {
      setError(textoError(e));
    }
  }

  async function descargar() {
    try {
      const url = URL.createObjectURL(await csvPiloto(token));
      const enlace = document.createElement("a");
      enlace.href = url;
      enlace.download = "resultados_piloto.csv";
      enlace.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(textoError(e));
    }
  }

  const resumen = resumenPiloto(datos?.filas ?? []);
  return (
    <section className="ds-tarjeta">
      <div className="fila-titulo">
        <h2>Modo piloto (RNF-06)</h2>
        <button onClick={() => void recargar()}>Actualizar</button>
      </div>
      <p>Para cada participante, toca <b>Nuevo participante</b> en el celular de la prueba: se
        abre la app en modo prueba. Lo que envíe no llega a la cola ni a los rescatistas. El tiempo
        cuenta desde su primer toque hasta el código; al final responde el cuestionario SUS.</p>
      {error && <p className="ds-msg ds-msg--error" role="alert">{error}</p>}
      <div className="acciones">
        <button className="principal" onClick={() => void nuevoParticipante()}>Nuevo participante</button>
        <button onClick={() => void descargar()} disabled={!datos?.completos}>Descargar CSV</button>
      </div>
      {invitacion && (
        <p className="ds-msg ds-msg--ok" role="status">Participante <b>{invitacion.participante}</b>.
          Si no se abrió, copia este enlace en el celular (sirve una vez y por 24 horas):{" "}
          <code>{location.origin}{invitacion.enlace}</code></p>)}
      {datos && (
        <dl className="kpis">
          <div className="kpi"><dd>{datos.invitados}</dd><dt>Invitados</dt></div>
          <div className="kpi"><dd>{datos.completos}</dd><dt>Terminaron</dt></div>
        </dl>)}
      {resumen && (
        <ul>
          <li>Reportaron en {META_SEGUNDOS} s o menos: <b>{resumen.cumplen}</b> ({resumen.porcentaje} %;
            meta {META_PORCENTAJE} %){" "}
            <span className={`ds-insignia ds-insignia--${resumen.cumpleTiempo ? "baja" : "critica"}`}>
              {resumen.cumpleTiempo ? "cumple" : "no cumple"}</span></li>
          <li>SUS promedio: <b>{resumen.sus.toFixed(1)}</b> (meta {META_SUS}){" "}
            <span className={`ds-insignia ds-insignia--${resumen.cumpleSus ? "baja" : "critica"}`}>
              {resumen.cumpleSus ? "cumple" : "no cumple"}</span></li>
        </ul>)}
      {datos && datos.filas.length > 0 && (
        <div className="ds-tabla-caja" tabIndex={0} role="region" aria-label="Resultados del piloto">
          <table className="ds-tabla ds-tabla--tarjetas" role="table">
            <thead><tr role="row"><th role="columnheader">Participante</th>
              <th role="columnheader">Segundos</th><th role="columnheader">SUS</th></tr></thead>
            <tbody>
              {datos.filas.map((f) => (
                <tr role="row" key={f.participante}>
                  <td role="cell" data-etiqueta="Participante">{f.participante}</td>
                  <td role="cell" data-etiqueta="Segundos">{f.segundos}</td>
                  <td role="cell" data-etiqueta="SUS">{f.sus}</td>
                </tr>))}
            </tbody>
          </table></div>)}
    </section>
  );
}
