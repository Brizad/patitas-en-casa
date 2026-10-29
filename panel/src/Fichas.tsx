import { useCallback, useEffect, useState } from "react";
import {
  FichaAnimal, MOTIVOS_EGRESO, MotivoEgreso, TIPOS_NOTA, TipoNota, agregarNota, animales,
  egresar, ficha,
} from "./apiRefugio";
import { textoError } from "./mensajes";

/** Fichas clínicas (RF-06, RF-24) y egresos (RF-26) del refugio de la persona. */
export default function Fichas({ token, rol, version, alCambiarCupo }: {
  token: string; rol: string; version?: string; alCambiarCupo: () => void;
}) {
  const [lista, setLista] = useState<FichaAnimal[]>([]);
  const [elegido, setElegido] = useState<FichaAnimal | null>(null);
  const [error, setError] = useState("");

  const recargar = useCallback(async () => {
    try {
      setLista(await animales(token));
    } catch (e) {
      setError(textoError(e));
    }
  }, [token]);

  // «version» es la ocupación: cambia con cada ingreso y obliga a pedir la lista otra vez.
  useEffect(() => { void recargar(); }, [recargar, version]);

  async function abrir(id: number) {
    try {
      setElegido(await ficha(token, id));
      setError("");
    } catch (e) {
      setError(textoError(e));
    }
  }

  const presentes = lista.filter((a) => !a.egresado_en);
  return (
    <div className="tarjeta">
      <h2>Animales del refugio ({presentes.length})</h2>
      {error && <p className="error" role="alert">{error}</p>}
      <ul className="lista-simple">
        {lista.map((a) => (
          <li key={a.id}>
            <button className="enlace" onClick={() => void abrir(a.id)}>{a.nombre}</button>
            {" "}· {a.especie} · {a.egresado_en ? `egresó (${a.motivo_egreso})` : "en el refugio"}
          </li>))}
      </ul>
      {elegido && (
        <Ficha token={token} rol={rol} animal={elegido}
          alCambiar={async (cupo) => {
            await abrir(elegido.id);
            await recargar();
            if (cupo) alCambiarCupo();
          }} />)}
    </div>
  );
}

function Ficha({ token, rol, animal, alCambiar }: {
  token: string; rol: string; animal: FichaAnimal; alCambiar: (cupo: boolean) => Promise<void>;
}) {
  const [tipo, setTipo] = useState<TipoNota>("observacion");
  const [texto, setTexto] = useState("");
  const [motivo, setMotivo] = useState<MotivoEgreso>("adopcion");
  const [mensaje, setMensaje] = useState("");

  async function hacer(accion: () => Promise<unknown>, exito: string, cupo: boolean) {
    try {
      await accion();
      setMensaje(exito);
      setTexto("");
      await alCambiar(cupo);
    } catch (e) {
      setMensaje(textoError(e));
    }
  }

  return (
    <section className="ajuste" aria-label={`Ficha de ${animal.nombre}`}>
      <h3>Ficha de {animal.nombre}</h3>
      <p>{animal.especie} · {animal.estado_salud} · {animal.vacunado ? "vacunado" : "sin vacunas"}
        {" "}· {animal.esterilizado ? "esterilizado" : "sin esterilizar"}</p>
      {mensaje && <p role="status">{mensaje}</p>}
      <h4>Historial clínico</h4>
      {animal.historial.length === 0 ? <p className="vacio">Sin notas todavía.</p> : (
        <ol>{animal.historial.map((n, i) => (
          <li key={i}><b>{TIPOS_NOTA[n.tipo]}</b> · {new Date(n.registrada_en).toLocaleString()}
            {" "}· {n.autor}<br />{n.texto}</li>))}</ol>)}
      {rol === "veterinario" && (
        <form onSubmit={(e) => {
          e.preventDefault();
          void hacer(() => agregarNota(token, animal.id, tipo, texto.trim()), "Nota agregada.", false);
        }}>
          <label>Tipo<select value={tipo} onChange={(e) => setTipo(e.target.value as TipoNota)}>
            {(Object.keys(TIPOS_NOTA) as TipoNota[]).map((t) => (
              <option key={t} value={t}>{TIPOS_NOTA[t]}</option>))}</select></label>
          <label>Nota<textarea rows={2} required value={texto}
            onChange={(e) => setTexto(e.target.value)} /></label>
          <button className="principal">Agregar al historial</button>
        </form>)}
      {rol === "coordinador" && !animal.egresado_en && (
        <form onSubmit={(e) => {
          e.preventDefault();
          void hacer(() => egresar(token, animal.id, motivo),
            `Egreso de ${animal.nombre} registrado: el cupo quedó libre.`, true);
        }}>
          <label>Motivo del egreso
            <select value={motivo} onChange={(e) => setMotivo(e.target.value as MotivoEgreso)}>
              {(Object.keys(MOTIVOS_EGRESO) as MotivoEgreso[]).map((m) => (
                <option key={m} value={m}>{MOTIVOS_EGRESO[m]}</option>))}</select></label>
          <button>Registrar egreso</button>
        </form>)}
    </section>
  );
}
