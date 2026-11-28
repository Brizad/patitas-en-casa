// #504: «Informes de rescate» para el veterinario y el coordinador: resultado, estado del animal,
// nota, hora, rescatista y la galería de fotos (clic para ampliar). Los más recientes primero.
import { useCallback, useEffect, useState } from "react";
import { InformeEnviado, informesRecientes } from "./apiRescatista";
import Cargando from "./Cargando";
import { InformeDeRescate } from "./Evidencias";
import { textoError } from "./mensajes";

export default function Informes({ token }: { token: string }) {
  const [informes, setInformes] = useState<InformeEnviado[] | null>(null);
  const [error, setError] = useState("");
  const cargar = useCallback(() => {
    informesRecientes(token).then((i) => { setInformes(i); setError(""); })
      .catch((e) => setError(textoError(e)));
  }, [token]);
  useEffect(() => { cargar(); }, [cargar]);
  return (
    <section className="pagina">
      <div className="fila-titulo">
        <h2>Informes de rescate</h2>
        <button onClick={cargar}>Actualizar</button>
      </div>
      {error && <p className="ds-msg ds-msg--error" role="alert">{error}</p>}
      {!informes && !error && <Cargando que="los informes" />}
      {informes && informes.length === 0 && (
        <p className="ds-vacio"><strong>Aún no hay informes.</strong> Aparecen cuando un rescatista termina un rescate.</p>)}
      {informes?.map((i) => <InformeDeRescate key={i.codigo} token={token} informe={i} />)}
    </section>
  );
}
