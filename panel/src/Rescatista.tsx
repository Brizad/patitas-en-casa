import { useCallback, useEffect, useState } from "react";
import { NOMBRE_PRIORIDAD, textoError } from "./mensajes";
import { Lugar } from "./MiniMapa";
import {
  EstadoRescatista, MiRescate, NOMBRE_RESULTADO, Oferta, Resultado, cambiarDisponibilidad,
  cambiarZona, miEstado, miRescate, nombreComunas, ofertas, paso, registrarResultado,
} from "./apiRescatista";

const COMUNAS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

/** HU-06 en el panel (RF-15, RF-21, RF-22): disponibilidad y zona, ofertas y mi rescate. */
export default function Rescatista({ token }: { token: string }) {
  const [estado, setEstado] = useState<EstadoRescatista | null>(null);
  const [lista, setLista] = useState<Oferta[]>([]);
  const [actual, setActual] = useState<MiRescate | null>(null);
  const [mensaje, setMensaje] = useState("");
  const [error, setError] = useState("");

  const recargar = useCallback(async () => {
    try {
      const [e, mio] = await Promise.all([miEstado(token), miRescate(token)]);
      setEstado(e);
      setActual(mio);
      // Con un rescate activo no se ofrecen otros (RN-08): no hace falta pedirlos.
      setLista(e.disponible && !mio ? await ofertas(token) : []);
      setError("");
    } catch (err) {
      setError(textoError(err));
    }
  }, [token]);

  useEffect(() => { void recargar(); }, [recargar]);

  async function hacer(accion: () => Promise<unknown>, exito: string) {
    try {
      await accion();
      setMensaje(exito);
    } catch (err) {
      setMensaje("");
      setError(textoError(err));
    }
    await recargar();
  }

  function alternarComuna(n: number) {
    if (!estado) return;
    const comunas = estado.comunas.includes(n)
      ? estado.comunas.filter((c) => c !== n) : [...estado.comunas, n];
    void hacer(() => cambiarZona(token, comunas), `Zona: ${nombreComunas(comunas)}.`);
  }

  return (
    <section className="pagina">
      {error && <p className="ds-msg ds-msg--error" role="alert">{error}</p>}
      {mensaje && <p className="ds-msg ds-msg--ok" role="status">{mensaje}</p>}
      {estado && (
        <div className="ds-tarjeta">
          <h2>Mi disponibilidad</h2>
          <label className="en-linea">
            <input type="checkbox" checked={estado.disponible}
              onChange={(e) => void hacer(() => cambiarDisponibilidad(token, e.target.checked),
                e.target.checked ? "Ahora recibes ofertas." : "Ya no recibes ofertas.")} />
            Disponible para rescates</label>
          <fieldset>
            <legend>Zona: {nombreComunas(estado.comunas)}</legend>
            <p className="ds-suave ayuda-zona">Marca las comunas donde puedes atender; sin marcar, recibes las de toda la ciudad.</p>
            <div className="comunas">
              {COMUNAS.map((n) => (
                <label key={n} className="comuna">
                  <input type="checkbox" checked={estado.comunas.includes(n)}
                    onChange={() => alternarComuna(n)} /> {n}</label>))}
            </div>
          </fieldset>
        </div>)}
      {actual ? <RescateActual token={token} rescate={actual} hacer={hacer} /> : (
        <div className="ds-tarjeta">
          <div className="fila-titulo">
            <h2>Ofertas de rescate</h2>
            <button onClick={() => void recargar()}>Actualizar</button>
          </div>
          {!estado?.disponible && <p className="ds-suave">Marca «Disponible» para ver ofertas.</p>}
          {estado?.disponible && lista.length === 0 && <p className="ds-vacio"><img src="/diseno/ilustraciones/sin-rescates.svg" alt="" width="160" height="120" /><strong>No hay ofertas ahora.</strong>
            Cuando el veterinario confirme un rescate crítico o alto de tu zona, aparecerá aquí.</p>}
          <ul className="ofertas">
            {lista.map((o) => (
              <li key={o.codigo} className={`oferta oferta--${o.prioridad}`}>
                <span className={`ds-insignia ds-insignia--${o.prioridad}`}>{NOMBRE_PRIORIDAD[o.prioridad]}</span>
                {" "}<code>{o.codigo}</code> · comuna {o.comuna ?? "sin dato"}
                {o.escalado && <b> · escalado a toda la ciudad</b>}
                <p>{o.descripcion}</p>
                <button className="principal" onClick={() => void hacer(
                  () => paso(token, o.codigo, "aceptar"), `Aceptaste ${o.codigo}. Ve en camino.`)}>
                  Aceptar rescate</button>
              </li>))}
          </ul>
        </div>)}
    </section>
  );
}

function RescateActual({ token, rescate, hacer }: {
  token: string; rescate: MiRescate;
  hacer: (accion: () => Promise<unknown>, exito: string) => Promise<void>;
}) {
  const [resultado, setResultado] = useState<Resultado>("trasladado");
  const u = rescate.ubicacion;
  // La dirección exacta solo la ve quien aceptó el rescate (el servidor la envía solo aquí).
  const donde = u.direccion ?? (u.latitud !== null ? `GPS ${u.latitud}, ${u.longitud}` : "sin dato");
  return (
    <div className={`ds-tarjeta oferta--${rescate.prioridad}`}>
      <h2>Mi rescate <code>{rescate.codigo}</code></h2>
      <p><span className={`ds-insignia ds-insignia--${rescate.prioridad}`}>{NOMBRE_PRIORIDAD[rescate.prioridad]}</span>
        {" "}<span className="ds-insignia ds-insignia--info">{rescate.estado === "en_camino" ? "En camino" : "En el sitio"}</span></p>
      <p>{rescate.descripcion}</p>
      <p>Ubicación: {donde}{u.comuna ? ` (comuna ${u.comuna})` : ""}</p>
      <Lugar u={u} />
      <div className="acciones">
        {rescate.estado === "en_camino" && (
          <button className="principal" onClick={() => void hacer(
            () => paso(token, rescate.codigo, "llegue"), "Llegada registrada.")}>Llegué al sitio</button>)}
        <button onClick={() => void hacer(() => paso(token, rescate.codigo, "liberar"),
          "Liberaste el rescate: vuelve a ofrecerse a otros rescatistas.")}>Liberar</button>
      </div>
      {rescate.estado === "en_sitio" && (
        <form className="ajuste" onSubmit={(e) => {
          e.preventDefault();
          void hacer(() => registrarResultado(token, rescate.codigo, resultado),
            `Resultado registrado: ${NOMBRE_RESULTADO[resultado].toLowerCase()}.`);
        }}>
          <label>Resultado
            <select value={resultado} onChange={(e) => setResultado(e.target.value as Resultado)}>
              {(Object.keys(NOMBRE_RESULTADO) as Resultado[]).map((r) => (
                <option key={r} value={r}>{NOMBRE_RESULTADO[r]}</option>))}
            </select></label>
          <button className="principal">Registrar resultado</button>
        </form>)}
    </div>
  );
}
