import { useEffect, useState } from "react";
import { AnalisisVideo, ESTADOS_VIDEO, analisisVideo, urlTira, urlVista } from "./apiVideo";
import { NOMBRE_PRIORIDAD, evidenciaLegible, nombreModelo, textoError } from "./mensajes";

const CLASE_ESTADO: Record<string, string> = {
  terminado: "baja", enviado: "info", pendiente: "info", no_concluyente: "alta", fallido: "alta",
};

/** #125: estado del análisis de video, sus evidencias, la discrepancia (RF-19) y la tira de
 *  3 cuadros con los puntos del cuerpo. El video original nunca se guarda; solo esta vista previa, 7 días (RNF-08, #214). */
export default function VideoDelReporte({ token, codigo }: { token: string; codigo: string }) {
  const [analisis, setAnalisis] = useState<AnalisisVideo | null | undefined>(undefined);
  const [tira, setTira] = useState("");
  const [vista, setVista] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let vigente = true;
    let url = "";
    let urlDeVista = "";
    setAnalisis(undefined);
    setTira("");
    setVista("");
    setError("");
    analisisVideo(token, codigo).then(async (a) => {
      if (!vigente) return;
      setAnalisis(a);
      if (a?.tiene_tira) {
        url = await urlTira(token, codigo);
        if (vigente) setTira(url);
      }
      if (a?.tiene_vista) {
        urlDeVista = await urlVista(token, codigo).catch(() => "");
        if (vigente) setVista(urlDeVista);
      }
    }).catch((e) => vigente && setError(textoError(e)));
    return () => {
      vigente = false;
      if (url) URL.revokeObjectURL(url);
      if (urlDeVista) URL.revokeObjectURL(urlDeVista);
    };
  }, [token, codigo]);

  if (error) return <p className="ds-msg ds-msg--error" role="alert">{error}</p>;
  if (analisis === undefined) return null;
  if (analisis === null) return <p className="ds-suave">Este reporte no trae video.</p>;
  return (
    <div className="video">
      <h3>Análisis de video{" "}
        <span className={`ds-insignia ds-insignia--${CLASE_ESTADO[analisis.estado]}`}>
          {ESTADOS_VIDEO[analisis.estado]}</span></h3>
      {analisis.prioridad && (
        <p>El video sugiere prioridad <b>{NOMBRE_PRIORIDAD[analisis.prioridad]?.toLowerCase()
          ?? analisis.prioridad}</b>
          {analisis.confianza !== null && <> con {Math.round(analisis.confianza * 100)} % de seguridad</>}
          {analisis.version_modelo && <> (según el {nombreModelo(analisis.version_modelo)})</>}.</p>)}
      {analisis.discrepancia && (
        <p className="ds-msg ds-msg--aviso">El texto y el video sugieren prioridades distintas; gana la más
          {" "}alta (RN-07, RF-19).</p>)}
      {(analisis.estado === "no_concluyente" || analisis.estado === "fallido") && (
        <p className="ds-suave">El video no alcanzó para decidir: guíate por la descripción.</p>)}
      {analisis.estado === "pendiente" && (
        <p className="ds-suave">El análisis llega en unos minutos; puedes decidir sin esperarlo.</p>)}
      {analisis.motivo && <p className="ds-suave">{analisis.motivo}</p>}
      {analisis.evidencias.length > 0 && (
        <ul className="evidencias">{analisis.evidencias.map((ev) => (
          <li key={ev}>{evidenciaLegible(ev)}</li>))}</ul>)}
      {vista && (
        <figure className="tira-caja">
          <video className="tira" src={vista} controls preload="metadata"
            aria-label="Video del reporte con los puntos del cuerpo del animal dibujados" />
          <figcaption>Vista previa de baja calidad, con los puntos del cuerpo. Se borra a los 7 días
            o al cerrarse el reporte.</figcaption>
        </figure>)}
      {tira && (
        <figure className="tira-caja">
          <img className="tira" src={tira}
            alt="Tres cuadros del video con los puntos del cuerpo del animal dibujados" />
          <figcaption>Tres momentos del video, con los puntos del cuerpo que midió el análisis.
            </figcaption>
        </figure>)}
      {analisis.estado === "terminado" && !tira && (
        <p className="ds-suave">Este análisis no trae imágenes.</p>)}
    </div>
  );
}
