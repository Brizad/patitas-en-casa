import { useEffect, useState } from "react";
import { AnalisisVideo, ESTADOS_VIDEO, analisisVideo, urlTira } from "./apiVideo";
import { textoError } from "./mensajes";

/** #125: estado del análisis de video, sus evidencias, la discrepancia (RF-19) y la tira de
 *  3 cuadros con los puntos del cuerpo. El video mismo nunca se guarda (RNF-08). */
export default function VideoDelReporte({ token, codigo }: { token: string; codigo: string }) {
  const [analisis, setAnalisis] = useState<AnalisisVideo | null | undefined>(undefined);
  const [tira, setTira] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let vigente = true;
    let url = "";
    setAnalisis(undefined);
    setTira("");
    setError("");
    analisisVideo(token, codigo).then(async (a) => {
      if (!vigente) return;
      setAnalisis(a);
      if (a?.tiene_tira) {
        url = await urlTira(token, codigo);
        if (vigente) setTira(url);
      }
    }).catch((e) => vigente && setError(textoError(e)));
    return () => {
      vigente = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [token, codigo]);

  if (error) return <p className="error" role="alert">{error}</p>;
  if (analisis === undefined) return null;
  if (analisis === null) return <p className="nota">Este reporte no trae video.</p>;
  return (
    <div>
      <h3>Análisis de video: {ESTADOS_VIDEO[analisis.estado]}</h3>
      {analisis.prioridad && (
        <p>El video sugiere <b>{analisis.prioridad}</b>
          {analisis.confianza !== null && <> · confianza {analisis.confianza.toFixed(2)}</>}
          {analisis.version_modelo && <> · {analisis.version_modelo}</>}</p>)}
      {analisis.discrepancia && (
        <p className="resultado">El texto y el video sugieren prioridades distintas; gana la más
          {" "}alta (RN-07, RF-19).</p>)}
      {analisis.motivo && <p className="nota">{analisis.motivo}</p>}
      {analisis.evidencias.length > 0 && (
        <ol>{analisis.evidencias.map((ev) => <li key={ev}>{ev}</li>)}</ol>)}
      {tira && <img className="tira" src={tira}
        alt="Tres cuadros del video con los puntos del cuerpo del animal dibujados" />}
    </div>
  );
}
