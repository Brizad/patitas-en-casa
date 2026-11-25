import { useCallback, useEffect, useState } from "react";
import {
  NuevaPublicacion, Pareja, SeguimientoRefugio, SolicitudRefugio, conEtiqueta, decidir, desdeCatalogo,
  editarPublicacion, paraEnviar, pedirVisita,
  propuestaJornada, publicar, registrarDevolucion, registrarSeguimiento, subirFoto, resumenPerfil, seguimientosRefugio, solicitudesRefugio,
} from "./apiAdopcionCoordinador";
import { AnimalPublicado, catalogo } from "./apiAdopcion";
import { FichaAnimal, animales } from "./apiRefugio";
import { faltaJustificacion, textoError } from "./mensajes";

const VACIA: NuevaPublicacion = { descripcion: "", tamano: "mediano", energia: "media",
  edad_meses: 12, apto_ninos: true, apto_otros_animales: true, necesita_patio: false,
  carino: null, energia_nivel: null, juego: null, calma: null, etiquetas: [], peso_kg: null,
  peso_adulto_kg: null };
type Nivel = "carino" | "energia_nivel" | "juego" | "calma";
const NIVELES: [Nivel, string][] = [["carino", "Cariño"], ["energia_nivel", "Energía"],
  ["juego", "Juego"], ["calma", "Calma"]];

/** Adopciones del refugio: publicar (RF-25), decidir (RF-27) y seguimientos (RF-10). */
export default function AdopcionesCoordinador({ token }: { token: string }) {
  const [presentes, setPresentes] = useState<FichaAnimal[]>([]);
  const [publicados, setPublicados] = useState<AnimalPublicado[]>([]);
  const [solicitudes, setSolicitudes] = useState<SolicitudRefugio[]>([]);
  const [seguimientos, setSeguimientos] = useState<SeguimientoRefugio[]>([]);
  const [mensaje, setMensaje] = useState("");
  const [jornada, setJornada] = useState<Pareja[] | null>(null);

  const recargar = useCallback(async () => {
    try {
      const [a, s, x, c] = await Promise.all([animales(token), solicitudesRefugio(token),
                                              seguimientosRefugio(token), catalogo()]);
      setPresentes(a.filter((f) => !f.egresado_en));
      setPublicados(c);
      setSolicitudes(s);
      setSeguimientos(x);
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
      setMensaje(textoError(e)); // p. ej. la restricción dura de RN-05, dicha por el servidor
    }
  }

  // «visita» sigue abierta: el refugio pidió visitar el hogar y aún no decide (RF-27).
  const pendientes = solicitudes.filter((s) => s.estado === "pendiente" || s.estado === "visita");
  const aprobadas = solicitudes.filter((s) => s.estado === "aprobada");
  return (
    <section className="pagina">
      {mensaje && <p className="ds-msg ds-msg--ok" role="status">{mensaje}</p>}
      <Publicar presentes={presentes} publicados={publicados} alPublicar={(id, p, editar) =>
        hacer(() => (editar ? editarPublicacion(token, id, p) : publicar(token, id, p)),
          editar ? "Publicación actualizada." : "Animal publicado en el catálogo.")} />
      <Foto presentes={presentes} alSubir={(id, archivo) =>
        hacer(() => subirFoto(token, id, archivo), "Foto guardada: ya se ve en el catálogo.")} />
      <div className="ds-tarjeta">
        <h2>Solicitudes pendientes ({pendientes.length})</h2>
        {pendientes.length === 0 && <p className="ds-vacio"><strong>No hay solicitudes pendientes.</strong>
          Cuando alguien pida adoptar, aparecerá aquí.</p>}
        <ul className="lista-simple">
          {pendientes.map((s) => (
            <Solicitud key={s.id} s={s} hacer={hacer} token={token} />))}
        </ul>
      </div>
      <div className="ds-tarjeta">
        <h2>Adopciones aprobadas ({aprobadas.length})</h2>
        <p className="ds-suave">Si la familia ya no puede cuidarlo, registra la devolución con el
          motivo: el animal vuelve al refugio y al catálogo.</p>
        {aprobadas.length === 0 && <p className="ds-vacio"><strong>No hay adopciones aprobadas.</strong>
          Aparecen aquí cuando apruebas una solicitud pendiente.</p>}
        <ul className="lista-simple">
          {aprobadas.map((s) => (
            <li key={s.id}><b>{s.animal}</b> · {s.adoptante}
              <TextoYBoton etiqueta="Motivo de la devolución" boton="Registrar devolución"
                alEnviar={(texto) => hacer(() => registrarDevolucion(token, s.id, texto),
                  `Devolución de ${s.animal} registrada: volvió al refugio.`)} /></li>))}
        </ul>
      </div>
      <div className="ds-tarjeta">
        <h2>Jornada de adopción</h2>
        <p className="ds-suave">Propone quién con qué animal para que la compatibilidad total sea la
          más alta. Es una sugerencia: cada solicitud se aprueba aparte.</p>
        <button onClick={() => void hacer(async () => setJornada(await propuestaJornada(token)),
          "Propuesta calculada.")}>Calcular propuesta</button>
        {jornada && (jornada.length === 0 ? <p className="ds-vacio">Sin parejas posibles.</p> : (
          <ul className="lista-simple">{jornada.map((p) => (
            <li key={p.adoptante}>{p.adoptante} → <b>{p.animal}</b> · {p.puntaje}/100
              {!p.solicito_este_animal && " · no lo pidió: conversarlo"}</li>))}</ul>))}
      </div>
      <div className="ds-tarjeta">
        <h2>Seguimientos (30, 90 y 180 días)</h2>
        {seguimientos.length === 0 && <p className="ds-vacio"><strong>No hay seguimientos programados.</strong>
          Los de 30, 90 y 180 días aparecen aquí después de aprobar una adopción.</p>}
        <ul className="lista-simple">
          {seguimientos.map((x) => (
            <li key={x.id}>{x.animal} · día {x.dia} · {x.programado_para.slice(0, 10)}
              {x.vencido && <> · <span className="ds-insignia ds-insignia--critica">vencido</span></>}
              {x.realizado_en ? <p>Hecho: {x.nota}</p> : (
                <NotaSeguimiento alGuardar={(nota) => hacer(
                  () => registrarSeguimiento(token, x.id, nota), "Seguimiento registrado.")} />)}
            </li>))}
        </ul>
      </div>
    </section>
  );
}

type Hacer = (accion: () => Promise<unknown>, exito: string) => Promise<void>;

function Solicitud({ s, token, hacer }: { s: SolicitudRefugio; token: string; hacer: Hacer }) {
  const [razon, setRazon] = useState("");
  return (
    <li>
      <b>{s.animal}</b> · {s.adoptante}<br /><small>{resumenPerfil(s.perfil)}</small>
      {s.compatibilidad && (
        <p className="ds-suave">Compatibilidad {s.compatibilidad.puntaje}/100
          {[...s.compatibilidad.restricciones, ...s.compatibilidad.alertas].length > 0 &&
            `: ${[...s.compatibilidad.restricciones, ...s.compatibilidad.alertas].join("; ")}`}
        </p>)}
      {s.mensaje && <p>«{s.mensaje}»</p>}
      {s.estado === "visita" && <p className="ds-suave">Visita pedida: {s.razon}</p>}
      <div className="acciones">
        <button className="principal" onClick={() => void hacer(() => decidir(token, s.id, true),
          `Adopción de ${s.animal} aprobada: egresó del refugio y se programaron los seguimientos.`)}>
          Aprobar</button>
        <input aria-label="Razón del rechazo" placeholder="Razón del rechazo" value={razon}
          onChange={(e) => setRazon(e.target.value)} />
        <button disabled={faltaJustificacion("critica", "alta", razon)}
          onClick={() => void hacer(() => decidir(token, s.id, false, razon.trim()),
            "Solicitud rechazada.")}>Rechazar</button>
      </div>
      {s.estado === "pendiente" && (
        <TextoYBoton etiqueta="Nota de la visita (cuándo y qué revisar)" boton="Pedir visita"
          alEnviar={(texto) => hacer(() => pedirVisita(token, s.id, texto),
            "Visita previa registrada: la solicitud sigue abierta.")} />)}
    </li>
  );
}

/** Un texto con la regla de las justificaciones (D-07) y su botón. */
function TextoYBoton({ etiqueta, boton, alEnviar }: {
  etiqueta: string; boton: string; alEnviar: (texto: string) => void;
}) {
  const [texto, setTexto] = useState("");
  return (
    <div className="acciones">
      <input aria-label={etiqueta} placeholder={etiqueta} value={texto}
        onChange={(e) => setTexto(e.target.value)} />
      <button disabled={faltaJustificacion("critica", "alta", texto)}
        onClick={() => { alEnviar(texto.trim()); setTexto(""); }}>{boton}</button>
    </div>
  );
}

function NotaSeguimiento({ alGuardar }: { alGuardar: (nota: string) => void }) {
  const [nota, setNota] = useState("");
  return (
    <form className="acciones" onSubmit={(e) => { e.preventDefault(); alGuardar(nota.trim()); }}>
      <input aria-label="Nota del seguimiento" placeholder="¿Cómo está el animal?" value={nota}
        onChange={(e) => setNota(e.target.value)} />
      <button>Registrar</button>
    </form>
  );
}

function Publicar({ presentes, publicados, alPublicar }: {
  presentes: FichaAnimal[]; publicados: AnimalPublicado[];
  alPublicar: (id: number, p: NuevaPublicacion, editar: boolean) => void;
}) {
  const [id, setId] = useState<number | "">("");
  const [p, setP] = useState(VACIA);
  const ya = publicados.find((a) => a.animal_id === id);
  const elegir = (nuevo: number | "") => {
    setId(nuevo);
    const publicado = publicados.find((a) => a.animal_id === nuevo);
    setP(publicado ? desdeCatalogo(publicado) : VACIA);
  };
  const marca = (campo: "apto_ninos" | "apto_otros_animales" | "necesita_patio", texto: string) => (
    <label className="en-linea"><input type="checkbox" checked={p[campo]}
      onChange={(e) => setP({ ...p, [campo]: e.target.checked })} /> {texto}</label>);
  const peso = (campo: "peso_kg" | "peso_adulto_kg", texto: string) => (
    <label>{texto}<input type="number" min={0.1} max={150} step={0.1} inputMode="decimal"
      value={p[campo] ?? ""} onChange={(e) => setP({ ...p,
        [campo]: e.target.value === "" ? null : Number(e.target.value) })} /></label>);
  const conFicha = NIVELES.some(([n]) => p[n] !== null);
  return (
    <form className="ds-tarjeta ds-form" onSubmit={(e) => {
      e.preventDefault();
      if (id !== "") alPublicar(id, paraEnviar(p), !!ya);
    }}>
      <h2>{ya ? `Editar la publicación de ${ya.nombre}` : "Publicar para adopción"}</h2>
      <label>Animal<select required value={id}
        onChange={(e) => elegir(e.target.value === "" ? "" : Number(e.target.value))}>
        <option value="">Elige un animal</option>
        {presentes.map((a) => <option key={a.id} value={a.id}>{a.nombre} ({a.especie})
          {publicados.some((x) => x.animal_id === a.id) ? " · publicado" : ""}</option>)}
      </select></label>
      <label className="ancho">Descripción (20 caracteres o más)<textarea rows={2} required minLength={20}
        value={p.descripcion} onChange={(e) => setP({ ...p, descripcion: e.target.value })} />
      </label>
      <label>Tamaño<select value={p.tamano}
        onChange={(e) => setP({ ...p, tamano: e.target.value as NuevaPublicacion["tamano"] })}>
        <option value="pequeno">Pequeño</option><option value="mediano">Mediano</option>
        <option value="grande">Grande</option></select></label>
      <label>Energía (para la compatibilidad)<select value={p.energia}
        onChange={(e) => setP({ ...p, energia: e.target.value as NuevaPublicacion["energia"] })}>
        <option value="baja">Baja</option><option value="media">Media</option>
        <option value="alta">Alta</option></select></label>
      <label>Edad (meses)<input type="number" min={0} max={360} value={p.edad_meses}
        onChange={(e) => setP({ ...p, edad_meses: Number(e.target.value) })} /></label>
      {marca("apto_ninos", "Convive con niños")}
      {marca("apto_otros_animales", "Convive con otros animales")}
      {marca("necesita_patio", "Necesita patio")}
      <fieldset className="ancho ficha-adopcion">
        <legend>Ficha para «Elige a tu compañero» (opcional)</legend>
        <label className="en-linea"><input type="checkbox" checked={conFicha} onChange={(e) =>
          setP({ ...p, ...Object.fromEntries(NIVELES.map(([n]) => [n, e.target.checked ? 50 : null])) })} />
          Mostrar las barras de cariño, energía, juego y calma</label>
        {conFicha && NIVELES.map(([n, texto]) => (
          <label key={n} className="deslizador">{texto}: <output>{p[n] ?? 0}</output>
            <input type="range" min={0} max={100} step={1} value={p[n] ?? 0}
              onChange={(e) => setP({ ...p, [n]: Number(e.target.value) })} /></label>))}
        {[0, 1, 2].map((i) => (
          <label key={i}>Etiqueta {i + 1}<input maxLength={20} value={p.etiquetas[i] ?? ""}
            placeholder={["Juguetón", "Cariñosa", "Vacunado"][i]}
            onChange={(e) => setP({ ...p, etiquetas: conEtiqueta(p.etiquetas, i, e.target.value) })} />
          </label>))}
        {peso("peso_kg", "Peso hoy (kg)")}
        {peso("peso_adulto_kg", "Peso de adulto, aproximado (kg)")}
      </fieldset>
      <p><button className="principal">{ya ? "Guardar cambios" : "Publicar"}</button></p>
    </form>
  );
}

/** RF-25: una foto por animal (reemplaza la anterior). */
function Foto({ presentes, alSubir }: {
  presentes: FichaAnimal[]; alSubir: (id: number, archivo: File) => void;
}) {
  const [id, setId] = useState<number | "">("");
  const [archivo, setArchivo] = useState<File | null>(null);
  return (
    <form className="ds-tarjeta ds-form" onSubmit={(e) => {
      e.preventDefault();
      if (id !== "" && archivo) alSubir(id, archivo);
    }}>
      <h2>Foto para el catálogo</h2>
      <label>Animal<select required value={id} onChange={(e) => setId(Number(e.target.value))}>
        <option value="">Elige un animal</option>
        {presentes.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}
      </select></label>
      <label>Foto (JPEG, PNG o WebP, máximo 300 KB)
        <input type="file" accept="image/jpeg,image/png,image/webp" required
          onChange={(e) => setArchivo(e.target.files?.[0] ?? null)} /></label>
      <button className="principal">Subir foto</button>
    </form>
  );
}
