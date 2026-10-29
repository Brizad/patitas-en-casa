import { useState } from "react";
import { ErrorApi, ReporteEnCola, descartar } from "./api";
import { faltaJustificacion, textoError } from "./mensajes";

/** D-02: descartar un reporte falso o duplicado. La justificación sigue RN-16 y D-07. */
export default function Descartar({ token, reporte, alTerminar }: {
  token: string; reporte: ReporteEnCola; alTerminar: (mensaje: string) => void;
}) {
  const [abierto, setAbierto] = useState(false);
  const [motivo, setMotivo] = useState<"falso" | "duplicado">(
    reporte.posibles_duplicados.length ? "duplicado" : "falso");
  const [original, setOriginal] = useState(reporte.posibles_duplicados[0] ?? "");
  const [texto, setTexto] = useState("");
  const [error, setError] = useState("");

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    // Misma regla que el ajuste de prioridad: «critica» ≠ «alta» fuerza la comprobación.
    if (faltaJustificacion("critica", "alta", texto)) {
      setError("Explica con palabras por qué se descarta (mínimo 10 caracteres).");
      return;
    }
    try {
      await descartar(token, reporte.codigo, motivo, texto.trim(),
                      motivo === "duplicado" && original ? original : undefined);
      alTerminar(`Reporte descartado como ${motivo}. Salió de la cola.`);
    } catch (e) {
      if (e instanceof ErrorApi && e.estado === 409) {
        alTerminar("Otro veterinario ya decidió este reporte. La cola se actualizó.");
      } else {
        setError(textoError(e));
      }
    }
  }

  return (
    <div className="descartar">
      <button aria-expanded={abierto} onClick={() => setAbierto(!abierto)}>
        Descartar reporte…</button>
      {abierto && (
        <form className="ajuste" onSubmit={enviar}>
          <label>Motivo
            <select value={motivo}
              onChange={(e) => setMotivo(e.target.value as "falso" | "duplicado")}>
              <option value="falso">Falso o no verificable</option>
              <option value="duplicado">Duplicado de otro reporte</option>
            </select></label>
          {motivo === "duplicado" && (
            <label>Reporte original (opcional)
              <select value={original} onChange={(e) => setOriginal(e.target.value)}>
                <option value="">Sin indicar</option>
                {reporte.posibles_duplicados.map((c) => <option key={c} value={c}>{c}</option>)}
              </select></label>)}
          <label>Justificación (obligatoria)
            <textarea rows={3} value={texto} onChange={(e) => setTexto(e.target.value)}
              aria-describedby="error-descarte" /></label>
          {error && <p className="error" id="error-descarte" role="alert">{error}</p>}
          <button className="principal">Descartar</button>
        </form>)}
    </div>
  );
}
