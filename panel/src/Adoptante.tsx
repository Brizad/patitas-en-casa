import { useCallback, useEffect, useState } from "react";
import {
  AnimalPublicado, MiSolicitud, PERFIL_VACIO, Perfil, Recomendado, catalogo,
  descargarCompromiso, guardarPerfil, miPerfil, misSolicitudes, recomendaciones, resumenAnimal,
  solicitar,
} from "./apiAdopcion";
import { textoError } from "./mensajes";

/** Pantalla del adoptante: perfil (RF-08), catálogo y solicitudes (RF-27), compromiso (RF-29). */
export default function Adoptante({ token }: { token: string }) {
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [animales, setAnimales] = useState<(AnimalPublicado | Recomendado)[]>([]);
  const [mias, setMias] = useState<MiSolicitud[]>([]);
  const [mensaje, setMensaje] = useState("");

  const recargar = useCallback(async () => {
    try {
      const [p, s] = await Promise.all([miPerfil(token), misSolicitudes(token)]);
      setPerfil(p);
      // Con perfil, el catálogo llega ordenado por compatibilidad (RF-09).
      setAnimales(p ? await recomendaciones(token) : await catalogo());
      setMias(s);
    } catch (e) {
      setMensaje(textoError(e));
    }
  }, [token]);

  useEffect(() => { void recargar(); }, [recargar]);

  async function hacer(accion: () => Promise<unknown>, exito: string) {
    try {
      await accion();
      setMensaje(exito);
      await recargar();
    } catch (e) {
      setMensaje(textoError(e));
    }
  }

  const nombre = (id: number) => animales.find((a) => a.animal_id === id)?.nombre ?? `#${id}`;
  return (
    <section className="pagina">
      {mensaje && <p className="resultado" role="status">{mensaje}</p>}
      <FormularioPerfil inicial={perfil ?? PERFIL_VACIO} nuevo={perfil === null}
        alGuardar={(p) => hacer(() => guardarPerfil(token, p), "Perfil guardado.")} />
      <div className="tarjeta">
        <h2>{perfil ? "Recomendados para tu hogar" : "Animales en adopción"}</h2>
        {animales.length === 0 && <p className="vacio">No hay animales publicados ahora.</p>}
        <ul className="lista-simple">
          {animales.map((a) => (
            <li key={a.animal_id}>
              <b>{a.nombre}</b> · {resumenAnimal(a)}<p>{a.descripcion}</p>
              {"puntaje" in a && (
                <p className="nota">Compatibilidad {a.puntaje}/100: {a.razones.join("; ")}.
                  {a.alertas.length > 0 && <> Para conversar: {a.alertas.join("; ")}.</>}</p>)}
              <button className="principal" onClick={() => void hacer(
                () => solicitar(token, a.animal_id, ""),
                `Solicitud enviada por ${a.nombre}. El refugio la revisará.`)}>
                Quiero adoptarlo</button>
            </li>))}
        </ul>
      </div>
      <div className="tarjeta">
        <h2>Mis solicitudes</h2>
        {mias.length === 0 && <p className="vacio">Aún no has hecho solicitudes.</p>}
        <ul className="lista-simple">
          {mias.map((s) => (
            <li key={s.id}>Solicitud {s.id} · {nombre(s.animal_id)} · <b>{s.estado}</b>
              {s.estado === "aprobada" && (
                <> {" "}<button onClick={() => void hacer(() => descargarCompromiso(token, s.id),
                  "Compromiso descargado: imprímelo y fírmalo en el refugio.")}>
                  Descargar compromiso (PDF)</button></>)}
            </li>))}
        </ul>
      </div>
    </section>
  );
}

function FormularioPerfil({ inicial, nuevo, alGuardar }: {
  inicial: Perfil; nuevo: boolean; alGuardar: (p: Perfil) => void;
}) {
  const [p, setP] = useState(inicial);
  useEffect(() => setP(inicial), [inicial]);
  const marca = (campo: keyof Perfil, texto: string) => (
    <label className="en-linea"><input type="checkbox" checked={p[campo] as boolean}
      onChange={(e) => setP({ ...p, [campo]: e.target.checked })} /> {texto}</label>);
  return (
    <form className="tarjeta" onSubmit={(e) => { e.preventDefault(); alGuardar(p); }}>
      <h2>Mi perfil {nuevo && <small>(llénalo para poder solicitar)</small>}</h2>
      <label>Vivienda<select value={p.vivienda}
        onChange={(e) => setP({ ...p, vivienda: e.target.value as Perfil["vivienda"] })}>
        <option value="casa">Casa</option><option value="apartamento">Apartamento</option>
        <option value="finca">Finca</option></select></label>
      <label>Horas que pasaría solo al día<input type="number" min={0} max={24}
        value={p.horas_solo_al_dia}
        onChange={(e) => setP({ ...p, horas_solo_al_dia: Number(e.target.value) })} /></label>
      {marca("tiene_patio", "Tengo patio")}
      {marca("hay_ninos", "En casa hay niños")}
      {marca("otros_animales", "Tengo otros animales")}
      {marca("experiencia", "Ya he cuidado perros o gatos")}
      <p>{marca("acepta_seguimiento",
        "Acepto los seguimientos del refugio a los 30, 90 y 180 días (obligatorio)")}</p>
      <button className="principal">Guardar perfil</button>
    </form>
  );
}
