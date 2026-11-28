import { useCallback, useEffect, useState } from "react";
import { NOMBRE_PRIORIDAD, haceCuanto, textoError } from "./mensajes";
import { Lugar } from "./MiniMapa";
import MapaCasos from "./MapaCasos";
import {
  NOMBRE_NIVEL, Punto, SIN_DATO, distanciaA, fechaExacta, ordenarPorCercania, textoDistancia,
  textoEspecie, textoZona,
} from "./bandejas";
import {
  EstadoRescatista, MiRescate, Oferta, cambiarDisponibilidad,
  cambiarZona, esCuentaDemo, miEstado, miRescate, nombreComunas, ofertas, paso, simularRecorrido,
} from "./apiRescatista";
import CompartirUbicacion from "./CompartirUbicacion";
import InformeRescatista from "./InformeRescatista";

const LLEGADA_M = 100; // #504: «Parece que ya llegaste»

const COMUNAS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
type Pestana = "disponibles" | "mio" | "atrasados";
// #496: el permiso de ubicación se pide una sola vez; la respuesta queda en este navegador.
const CLAVE_UBICACION = "patitas.rescatista.ubicacion";

function leerDecision(): string | null {
  try { return localStorage.getItem(CLAVE_UBICACION); } catch { return null; }
}
function guardarDecision(valor: "si" | "no") {
  try { localStorage.setItem(CLAVE_UBICACION, valor); } catch { /* sin almacenamiento */ }
}

/** HU-06 en el panel (RF-15, RF-21, RF-22): disponibilidad y zona, ofertas y mi rescate. #496:
 *  pestañas, tarjetas con nivel, tiempo y distancia, y el mapa de los casos. */
export default function Rescatista({ token, correo = "" }: { token: string; correo?: string }) {
  const [estado, setEstado] = useState<EstadoRescatista | null>(null);
  const [lista, setLista] = useState<Oferta[]>([]);
  const [actual, setActual] = useState<MiRescate | null>(null);
  const [mensaje, setMensaje] = useState("");
  const [error, setError] = useState("");
  const [pestana, setPestana] = useState<Pestana | null>(null);
  const [elegido, setElegido] = useState<string | null>(null);
  const [yo, setYo] = useState<Punto | null>(null);
  const [decision, setDecision] = useState<string | null>(leerDecision);
  const [mapaAbierto, setMapaAbierto] = useState(false);
  const [simulando, setSimulando] = useState(false);

  const recargar = useCallback(async () => {
    try {
      const [e, mio] = await Promise.all([miEstado(token), miRescate(token)]);
      setEstado(e);
      setActual(mio);
      setLista(e.disponible ? await ofertas(token) : []);
      setPestana((p) => p ?? (mio ? "mio" : "disponibles"));
      setError("");
    } catch (err) {
      setError(textoError(err));
    }
  }, [token]);

  useEffect(() => { void recargar(); }, [recargar]);

  // #498: mientras corre el recorrido de demostración, se relee el rescate para ver el cambio de
  // estado (llegada y atendido) sin tocar nada.
  useEffect(() => {
    if (!simulando) return;
    const reloj = setInterval(() => { void recargar(); }, 5000);
    return () => clearInterval(reloj);
  }, [simulando, recargar]);
  // #504: la simulación termina al llegar («En el sitio»): desde ahí el informe es a mano.
  useEffect(() => { if (!actual || actual.estado !== "en_camino") setSimulando(false); }, [actual]);

  // Solo con permiso: la ubicación se usa aquí para medir la distancia y no se envía.
  useEffect(() => {
    if (decision !== "si" || !("geolocation" in navigator)) return;
    navigator.geolocation.getCurrentPosition(
      (p) => setYo({ latitud: p.coords.latitude, longitud: p.coords.longitude }),
      () => setYo(null), { enableHighAccuracy: false, maximumAge: 60_000, timeout: 15_000 });
  }, [decision]);

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

  const elegir = useCallback((codigo: string) => setElegido(codigo), []);
  const disponibles = ordenarPorCercania(lista.filter((o) => !o.atrasado), yo);
  const atrasados = ordenarPorCercania(lista.filter((o) => o.atrasado), yo);
  const visibles = pestana === "atrasados" ? atrasados : disponibles;

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
      <div className="ds-tarjeta bandeja-rescatista">
        <div className="fila-titulo">
          <h2>Ofertas de rescate</h2>
          <button onClick={() => void recargar()}>Actualizar</button>
        </div>
        <div className="pestanas-bandeja" role="tablist" aria-label="Bandeja del rescatista">
          {([["disponibles", "Disponibles", disponibles.length], ["mio", "Mis rescates", actual ? 1 : 0],
            ["atrasados", "Atrasados", atrasados.length]] as [Pestana, string, number][]).map(([id, nombre, n]) => (
            <button key={id} role="tab" aria-selected={pestana === id} onClick={() => setPestana(id)}>
              {nombre}<span className={`contador${id === "atrasados" && n > 0 ? " contador--rojo" : ""}`}>{n}</span>
            </button>))}
        </div>
        {pestana === "mio" ? (actual ? <RescateActual token={token} rescate={actual} hacer={hacer}
          demo={esCuentaDemo(correo)} simulando={simulando}
          alSimular={() => void hacer(async () => { await simularRecorrido(token, actual.codigo); setSimulando(true); },
            `Recorrido de demostración en marcha (unos 90 s). Abre la consulta del ciudadano con el código ${actual.codigo} para verlo moverse.`)} />
          : <p className="ds-vacio"><strong>No tienes un rescate en curso.</strong> Acepta uno en «Disponibles».</p>) : (
          <>
            {decision === null && "geolocation" in navigator && (
              <div className="permiso-ubicacion">
                <p><b>¿A qué distancia estás de cada caso?</b> Usamos tu ubicación solo en este navegador
                  para medirla y ordenar por cercanía; no se guarda ni se envía.</p>
                <div className="acciones">
                  <button className="principal" onClick={() => { guardarDecision("si"); setDecision("si"); }}>
                    Usar mi ubicación</button>
                  <button onClick={() => { guardarDecision("no"); setDecision("no"); }}>Ahora no</button>
                </div>
              </div>)}
            {!estado?.disponible && <p className="ds-suave">Marca «Disponible» para ver ofertas.</p>}
            {actual && <p className="ds-suave">Ya tienes un rescate en curso: termínalo para aceptar otro.</p>}
            {pestana === "atrasados" && atrasados.length > 0 && (
              <p className="ds-msg aviso-atrasados">Estos casos llevan más de 3 días esperando rescatista.</p>)}
            {estado?.disponible && visibles.length === 0 && (pestana === "disponibles" ? (
              <p className="ds-vacio"><img src="/diseno/ilustraciones/sin-rescates.svg" alt="" width="160" height="120" /><strong>No hay ofertas ahora.</strong>
                Cuando el veterinario confirme un rescate crítico o alto de tu zona, aparecerá aquí.</p>)
              : <p className="ds-vacio"><strong>No hay casos atrasados.</strong></p>)}
            {visibles.length > 0 && (
              <button className="ver-en-mapa" aria-expanded={mapaAbierto}
                onClick={() => setMapaAbierto(!mapaAbierto)}>{mapaAbierto ? "Ocultar mapa" : "Ver en mapa"}</button>)}
            <div className={`bandeja-cuerpo${mapaAbierto ? " bandeja-cuerpo--mapa" : ""}`}>
              <ul className="ofertas">
                {visibles.map((o) => (
                  <TarjetaOferta key={o.codigo} o={o} yo={yo} elegida={o.codigo === elegido}
                    puedeAceptar={!actual} alElegir={elegir}
                    alAceptar={() => void hacer(() => paso(token, o.codigo, "aceptar"),
                      `Aceptaste ${o.codigo}. Ve en camino.`).then(() => setPestana("mio"))} />))}
              </ul>
              {visibles.length > 0 && (
                <div className="bandeja-mapa">
                  <MapaCasos casos={visibles} elegido={elegido} yo={yo} alElegir={elegir} />
                </div>)}
            </div>
          </>)}
      </div>
    </section>
  );
}

function TarjetaOferta({ o, yo, elegida, puedeAceptar, alElegir, alAceptar }: {
  o: Oferta; yo: Punto | null; elegida: boolean; puedeAceptar: boolean;
  alElegir: (codigo: string) => void; alAceptar: () => void;
}) {
  const [abierta, setAbierta] = useState(false);
  const distancia = distanciaA(yo, o);
  return (
    <li className={`oferta oferta--${o.prioridad}${elegida ? " oferta--elegida" : ""}`}
      onClick={() => alElegir(o.codigo)}>
      <p className="oferta-cabeza">
        <span className={`nivel nivel--${o.nivel}`}>{NOMBRE_NIVEL[o.nivel]}</span>
        <b>{textoEspecie(o.especie)}{o.estado_animal ? ` · ${o.estado_animal}` : ""}</b>
        <code>{o.codigo}</code>
        {o.escalado && <span className="ds-insignia ds-insignia--info">escalado a toda la ciudad</span>}
      </p>
      <p className="oferta-datos">
        <span>{textoZona(o.comuna)}</span>
        <span title={fechaExacta(o.esperando_desde)}>Reportado {haceCuanto(o.esperando_desde)}</span>
        <span className="distancia">{distancia === null ? `Distancia: ${SIN_DATO}` : `A ${textoDistancia(distancia)}`}</span>
      </p>
      {abierta && <p className="oferta-detalle">{o.descripcion}</p>}
      <div className="acciones">
        <button className="principal" disabled={!puedeAceptar} onClick={alAceptar}>Aceptar rescate</button>
        <button aria-expanded={abierta} onClick={() => setAbierta(!abierta)}>
          {abierta ? "Ocultar detalle" : "Ver detalle"}</button>
      </div>
    </li>
  );
}

function RescateActual({ token, rescate, hacer, demo, simulando, alSimular }: {
  token: string; rescate: MiRescate;
  hacer: (accion: () => Promise<unknown>, exito: string) => Promise<void>;
  demo: boolean; simulando: boolean; alSimular: () => void;
}) {
  const [cerca, setCerca] = useState(false);
  const u = rescate.ubicacion;
  // La dirección exacta solo la ve quien aceptó el rescate (el servidor la envía solo aquí).
  const donde = u.direccion ?? (u.latitud !== null ? `GPS ${u.latitud}, ${u.longitud}` : "sin dato");
  // #504: con la ubicación compartida, a menos de 100 m se sugiere marcar la llegada (no cambia
  // de estado solo: el rescatista decide).
  const alMoverse = useCallback((yo: Punto) => {
    const metros = distanciaA(yo, u);
    setCerca(metros !== null && metros < LLEGADA_M);
  }, [u]);
  return (
    <div className={`mi-rescate oferta--${rescate.prioridad}`}>
      <h2>Mi rescate <code>{rescate.codigo}</code></h2>
      <p><span className={`ds-insignia ds-insignia--${rescate.prioridad}`}>{NOMBRE_PRIORIDAD[rescate.prioridad]}</span>
        {" "}<span className="ds-insignia ds-insignia--info">{rescate.estado === "en_camino" ? "En camino" : "En el sitio"}</span></p>
      <p>{rescate.descripcion}</p>
      <p>Ubicación: {donde}{u.comuna ? ` (comuna ${u.comuna})` : ""}</p>
      <Lugar u={u} />
      {/* #498: solo mientras va en camino; al llegar se desmonta y deja de compartir. */}
      {rescate.estado === "en_camino" && !simulando && (
        <CompartirUbicacion token={token} codigo={rescate.codigo} alMoverse={alMoverse} />)}
      {rescate.estado === "en_camino" && demo && (
        <div className="simulacion">
          <p className="ds-suave">Solo en las cuentas de demostración: el servidor mueve tu posición
            desde 1,5 km hasta el animal en unos 90 s y marca la llegada. Desde ahí, el informe es el mismo.</p>
          <button onClick={alSimular} disabled={simulando}>
            {simulando ? "Recorrido en marcha…" : "Simular recorrido"}</button>
        </div>)}
      {rescate.estado === "en_camino" && cerca && (
        <p className="ds-msg aviso-llegaste">Parece que ya llegaste. Si estás con el animal, toca «Ya estoy en el sitio».</p>)}
      <div className="acciones">
        {/* #504: siempre disponible en «En camino»; al tocarlo deja de compartir y se borra la posición. */}
        {rescate.estado === "en_camino" && (
          <button className={`principal${cerca ? " resaltado" : ""}`} onClick={() => void hacer(
            () => paso(token, rescate.codigo, "llegue"), "Llegada registrada.")}>Ya estoy en el sitio</button>)}
        <button onClick={() => void hacer(() => paso(token, rescate.codigo, "liberar"),
          "Liberaste el rescate: vuelve a ofrecerse a otros rescatistas.")}>Liberar</button>
      </div>
      {rescate.estado === "en_sitio" && (
        <InformeRescatista token={token} codigo={rescate.codigo}
          alEnviar={(texto) => void hacer(async () => undefined, texto)} />)}
    </div>
  );
}
