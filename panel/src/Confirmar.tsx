import { useState } from "react";
import { ErrorApi, Prioridad, ReporteEnCola, confirmar, estadoAvisos } from "./api";
import {
  NOMBRE_PRIORIDAD, faltaJustificacion, mensajeConfirmacion, sugerida, textoAvisos, textoError,
} from "./mensajes";

const PRIORIDADES: Prioridad[] = ["critica", "alta", "media", "baja"];

/** HU-02: confirmar la sugerida o ajustarla con justificación. El servidor decide (RN-06). */
export default function Confirmar({ token, reporte, alTerminar }: {
  token: string; reporte: ReporteEnCola; alTerminar: (mensaje: string) => void;
}) {
  const propuesta = sugerida(reporte.estado, reporte.prioridad);
  const [ajustando, setAjustando] = useState(false);
  const [elegida, setElegida] = useState<Prioridad>(propuesta);
  const [texto, setTexto] = useState("");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function enviar(prioridad?: Prioridad, justificacion?: string) {
    setEnviando(true);
    setError("");
    try {
      const respuesta = await confirmar(token, reporte.codigo, prioridad, justificacion);
      alTerminar(mensajeConfirmacion(respuesta));
    } catch (e) {
      if (e instanceof ErrorApi && e.estado === 409) {
        alTerminar("Otro veterinario ya confirmó este reporte. La cola se actualizó.");
      } else {
        setError(textoError(e));
      }
    } finally {
      setEnviando(false);
    }
  }

  function guardarAjuste(evento: React.FormEvent) {
    evento.preventDefault();
    if (faltaJustificacion(propuesta, elegida, texto)) {
      setError("Escribe con palabras por qué cambias la prioridad (mínimo 10 caracteres, RN-16).");
      return;
    }
    void enviar(elegida, elegida === propuesta ? undefined : texto.trim());
  }

  return (
    <div className="confirmar">
      <div className="acciones">
        <button className="principal" disabled={enviando} onClick={() => void enviar()}>
          Confirmar {NOMBRE_PRIORIDAD[propuesta].toLowerCase()}
        </button>
        <button aria-expanded={ajustando} onClick={() => setAjustando(!ajustando)}>
          Ajustar prioridad…
        </button>
      </div>
      {ajustando && (
        <form className="ajuste" onSubmit={guardarAjuste}>
          <label>Nueva prioridad
            <select value={elegida} onChange={(e) => setElegida(e.target.value as Prioridad)}>
              {PRIORIDADES.map((p) => <option key={p} value={p}>{NOMBRE_PRIORIDAD[p]}</option>)}
            </select></label>
          {elegida !== propuesta && (
            <label>Justificación (obligatoria si cambias la prioridad)
              <textarea value={texto} onChange={(e) => setTexto(e.target.value)} rows={3}
                aria-describedby="error-ajuste" /></label>)}
          <button className="principal" disabled={enviando}>Guardar ajuste</button>
        </form>)}
      {error && <p className="error" id="error-ajuste" role="alert">{error}</p>}
    </div>
  );
}

export async function resumenAvisos(token: string, codigo: string): Promise<string> {
  try {
    const datos = await estadoAvisos(token, codigo);
    return textoAvisos(datos.resumen, datos.avisos);
  } catch (e) {
    return textoError(e);
  }
}
