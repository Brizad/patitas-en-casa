import { useCallback, useEffect, useState } from "react";
import {
  NuevaPublicacion, Pareja, SeguimientoRefugio, SolicitudRefugio, decidir, pedirVisita,
  propuestaJornada, publicar, registrarDevolucion, registrarSeguimiento, subirFoto, resumenPerfil, seguimientosRefugio, solicitudesRefugio,
} from "./apiAdopcionCoordinador";
import { FichaAnimal, animales } from "./apiRefugio";
import { faltaJustificacion, textoError } from "./mensajes";

const VACIA: NuevaPublicacion = { descripcion: "", tamano: "mediano", energia: "media",
  edad_meses: 12, apto_ninos: true, apto_otros_animales: true, necesita_patio: false };

/** Adopciones del refugio: publicar (RF-25), decidir (RF-27) y seguimientos (RF-10). */
export default function AdopcionesCoordinador({ token }: { token: string }) {
  const [presentes, setPresentes] = useState<FichaAnimal[]>([]);
  const [solicitudes, setSolicitudes] = useState<SolicitudRefugio[]>([]);
  const [seguimientos, setSeguimientos] = useState<SeguimientoRefugio[]>([]);
  const [mensaje, setMensaje] = useState("");
  const [jornada, setJornada] = useState<Pareja[] | null>(null);

  const recargar = useCallback(async () => {
    try {
      const [a, s, x] = await Promise.all([animales(token), solicitudesRefugio(token),
                                           seguimientosRefugio(token)]);
      setPresentes(a.filter((f) => !f.egresado_en));
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
      {mensaje && <p className="resultado" role="status">{mensaje}</p>}
      <Publicar presentes={presentes} alPublicar={(id, p) =>
        hacer(() => publicar(token, id, p), "Animal publicado en el catálogo.")} />
      <Foto presentes={presentes} alSubir={(id, archivo) =>
        hacer(() => subirFoto(token, id, archivo), "Foto guardada: ya se ve en el catálogo.")} />
      <div className="tarjeta">
        <h2>Solicitudes pendientes ({pendientes.length})</h2>
        <ul className="lista-simple">
          {pendientes.map((s) => (
            <Solicitud key={s.id} s={s} hacer={hacer} token={token} />))}
        </ul>
      </div>
      <div className="tarjeta">
        <h2>Adopciones aprobadas ({aprobadas.length})</h2>
        <p className="nota">Si la familia ya no puede cuidarlo, registra la devolución con el
          motivo: el animal vuelve al refugio y al catálogo (RF-10, RN-13).</p>
        <ul className="lista-simple">
          {aprobadas.map((s) => (
            <li key={s.id}><b>{s.animal}</b> · {s.adoptante}
              <TextoYBoton etiqueta="Motivo de la devolución" boton="Registrar devolución"
                alEnviar={(texto) => hacer(() => registrarDevolucion(token, s.id, texto),
                  `Devolución de ${s.animal} registrada: volvió al refugio.`)} /></li>))}
        </ul>
      </div>
      <div className="tarjeta">
        <h2>Jornada de adopción</h2>
        <p className="nota">Propone quién con qué animal para que la compatibilidad total sea la
          más alta (RF-28). Es una sugerencia: cada solicitud se aprueba aparte.</p>
        <button onClick={() => void hacer(async () => setJornada(await propuestaJornada(token)),
          "Propuesta calculada.")}>Calcular propuesta</button>
        {jornada && (jornada.length === 0 ? <p className="vacio">Sin parejas posibles.</p> : (
          <ul className="lista-simple">{jornada.map((p) => (
            <li key={p.adoptante}>{p.adoptante} → <b>{p.animal}</b> · {p.puntaje}/100
              {!p.solicito_este_animal && " · no lo pidió: conversarlo"}</li>))}</ul>))}
      </div>
      <div className="tarjeta">
        <h2>Seguimientos (30, 90 y 180 días)</h2>
        <ul className="lista-simple">
          {seguimientos.map((x) => (
            <li key={x.id}>{x.animal} · día {x.dia} · {x.programado_para.slice(0, 10)}
              {x.vencido && <b className="error"> · vencido</b>}
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
        <p className="nota">Compatibilidad {s.compatibilidad.puntaje}/100
          {[...s.compatibilidad.restricciones, ...s.compatibilidad.alertas].length > 0 &&
            `: ${[...s.compatibilidad.restricciones, ...s.compatibilidad.alertas].join("; ")}`}
        </p>)}
      {s.mensaje && <p>«{s.mensaje}»</p>}
      {s.estado === "visita" && <p className="nota">Visita pedida: {s.razon}</p>}
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

function Publicar({ presentes, alPublicar }: {
  presentes: FichaAnimal[]; alPublicar: (id: number, p: NuevaPublicacion) => void;
}) {
  const [id, setId] = useState<number | "">("");
  const [p, setP] = useState(VACIA);
  const marca = (campo: "apto_ninos" | "apto_otros_animales" | "necesita_patio", texto: string) => (
    <label className="en-linea"><input type="checkbox" checked={p[campo]}
      onChange={(e) => setP({ ...p, [campo]: e.target.checked })} /> {texto}</label>);
  return (
    <form className="tarjeta" onSubmit={(e) => {
      e.preventDefault();
      if (id !== "") alPublicar(id, { ...p, descripcion: p.descripcion.trim() });
    }}>
      <h2>Publicar para adopción</h2>
      <label>Animal<select required value={id} onChange={(e) => setId(Number(e.target.value))}>
        <option value="">Elige un animal</option>
        {presentes.map((a) => <option key={a.id} value={a.id}>{a.nombre} ({a.especie})</option>)}
      </select></label>
      <label>Descripción (20 caracteres o más)<textarea rows={2} required minLength={20}
        value={p.descripcion} onChange={(e) => setP({ ...p, descripcion: e.target.value })} />
      </label>
      <label>Tamaño<select value={p.tamano}
        onChange={(e) => setP({ ...p, tamano: e.target.value as NuevaPublicacion["tamano"] })}>
        <option value="pequeno">Pequeño</option><option value="mediano">Mediano</option>
        <option value="grande">Grande</option></select></label>
      <label>Energía<select value={p.energia}
        onChange={(e) => setP({ ...p, energia: e.target.value as NuevaPublicacion["energia"] })}>
        <option value="baja">Baja</option><option value="media">Media</option>
        <option value="alta">Alta</option></select></label>
      <label>Edad (meses)<input type="number" min={0} max={360} value={p.edad_meses}
        onChange={(e) => setP({ ...p, edad_meses: Number(e.target.value) })} /></label>
      {marca("apto_ninos", "Convive con niños")}
      {marca("apto_otros_animales", "Convive con otros animales")}
      {marca("necesita_patio", "Necesita patio")}
      <p><button className="principal">Publicar</button></p>
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
    <form className="tarjeta" onSubmit={(e) => {
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
