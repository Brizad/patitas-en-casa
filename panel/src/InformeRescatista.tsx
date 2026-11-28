// #504: informe del rescatista en el sitio, pensado para el celular. Es el MISMO para el rescate
// real y el simulado: el servidor valida igual y, al enviarlo, el caso pasa a «Atendido».
import { useState } from "react";
import {
  Accion, DatosInforme, Encontrado, EstadoAnimal, NOMBRE_ACCION_RESCATE, NOMBRE_ENCONTRADO,
  NOMBRE_ESTADO_ANIMAL, enviarInforme, faltaEnInforme,
} from "./apiRescatista";
import { MAX_FOTOS, prepararFoto } from "./fotos";
import { textoError } from "./mensajes";

export default function InformeRescatista({ token, codigo, alEnviar }: {
  token: string; codigo: string; alEnviar: (texto: string) => void;
}) {
  const [datos, setDatos] = useState<DatosInforme>({ encontrado: "si", estados: [], accion: null, motivo: "", nota: "" });
  const [fotos, setFotos] = useState<{ blob: Blob; vista: string }[]>([]);
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);
  const noEstaba = datos.encontrado === "no_estaba";
  const cambiar = (parte: Partial<DatosInforme>) => setDatos({ ...datos, ...parte });

  async function agregarFoto(e: React.ChangeEvent<HTMLInputElement>) {
    const archivo = e.target.files?.[0];
    e.target.value = "";
    if (!archivo) return;
    setError("");
    try {
      const blob = await prepararFoto(archivo); // ≤1280 px, ~200 KB y sin EXIF
      setFotos((antes) => [...antes, { blob, vista: URL.createObjectURL(blob) }].slice(0, MAX_FOTOS));
    } catch {
      setError("No pudimos leer esa foto. Prueba con otra.");
    }
  }

  function quitarFoto(i: number) {
    URL.revokeObjectURL(fotos[i].vista);
    setFotos(fotos.filter((_, j) => j !== i));
  }

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    const falta = faltaEnInforme(datos, fotos.length);
    if (falta) { setError(falta); return; }
    setEnviando(true);
    setError("");
    try {
      const informe = await enviarInforme(token, codigo, datos, fotos.map((f) => f.blob));
      fotos.forEach((f) => URL.revokeObjectURL(f.vista));
      alEnviar(`Informe enviado: ${informe.resultado_texto.toLowerCase()}. El caso quedó atendido.`);
    } catch (err) {
      setError(textoError(err));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form className="informe-form" onSubmit={enviar} noValidate>
      <h3>Informe de rescate</h3>
      <fieldset>
        <legend>¿Encontraste al animal?</legend>
        <div className="opciones-informe">
          {(Object.keys(NOMBRE_ENCONTRADO) as Encontrado[]).map((v) => (
            <label key={v} className="opcion-informe">
              <input type="radio" name="encontrado" checked={datos.encontrado === v}
                onChange={() => cambiar({ encontrado: v })} /> {NOMBRE_ENCONTRADO[v]}</label>))}
        </div>
      </fieldset>
      {!noEstaba && (
        <>
          <fieldset>
            <legend>Estado del animal (puedes marcar varios)</legend>
            <div className="opciones-informe">
              {(Object.keys(NOMBRE_ESTADO_ANIMAL) as EstadoAnimal[]).map((v) => (
                <label key={v} className="opcion-informe">
                  <input type="checkbox" checked={datos.estados.includes(v)} onChange={(e) => cambiar({
                    estados: e.target.checked ? [...datos.estados, v] : datos.estados.filter((x) => x !== v) })} />
                  {" "}{NOMBRE_ESTADO_ANIMAL[v]}</label>))}
            </div>
          </fieldset>
          <fieldset>
            <legend>¿Qué se hizo?</legend>
            <div className="opciones-informe">
              {(Object.keys(NOMBRE_ACCION_RESCATE) as Accion[]).map((v) => (
                <label key={v} className="opcion-informe">
                  <input type="radio" name="accion" checked={datos.accion === v}
                    onChange={() => cambiar({ accion: v })} /> {NOMBRE_ACCION_RESCATE[v]}</label>))}
            </div>
          </fieldset>
          {datos.accion === "no_rescatado" && (
            <label>¿Por qué no se pudo? (obligatorio)
              <textarea rows={2} value={datos.motivo} onChange={(e) => cambiar({ motivo: e.target.value })} /></label>)}
        </>)}
      <fieldset>
        <legend>Fotos de evidencia ({noEstaba ? "opcionales" : "al menos 1"}, hasta {MAX_FOTOS})</legend>
        <ul className="fotos-informe">
          {fotos.map((f, i) => (
            <li key={f.vista}><img src={f.vista} alt={`Foto ${i + 1} lista para enviar`} />
              <button type="button" onClick={() => quitarFoto(i)}>Quitar</button></li>))}
        </ul>
        {fotos.length < MAX_FOTOS && (
          <label className="ds-btn tomar-foto">Tomar o elegir foto
            <input className="visualmente-oculto" type="file" accept="image/*" capture="environment"
              onChange={(e) => void agregarFoto(e)} /></label>)}
        <p className="ds-suave">Se reducen y se les quitan los datos de ubicación antes de enviarlas.</p>
      </fieldset>
      <label>Nota (opcional, hasta 500 caracteres)
        <textarea rows={3} maxLength={500} value={datos.nota} onChange={(e) => cambiar({ nota: e.target.value })} /></label>
      {error && <p className="ds-msg ds-msg--error" role="alert">{error}</p>}
      <button className="principal" disabled={enviando}>{enviando ? "Enviando…" : "Enviar informe"}</button>
    </form>
  );
}
