// Entrada del adoptante (arreglos, parte B): una pantalla amable con el estilo de «Elige a tu
// compañero» y dos opciones grandes (ya tengo cuenta / soy nuevo) más el catálogo sin cuenta.
// Nunca se ve ni se llama «personal»: el personal entra por /panel/#personal.
import { useEffect, useState } from "react";
import { Cuenta, iniciarSesion, miCuenta } from "./api";
import { problemaContrasena } from "./apiAdmin";
import { AnimalPublicado, catalogo, registrarAdoptante } from "./apiAdopcion";
import Cargando from "./Cargando";
import CatalogoEnFilas from "./CatalogoEnFilas";
import { FLECHA, Huella, Icono } from "./Ilustraciones";
import { textoError } from "./mensajes";
import PaisajeEntrada from "./PaisajeEntrada";

export type VistaAcceso = "inicio" | "entrar" | "crear" | "animales";

/** #adoptar, #adoptar/entrar, #adoptar/crear, #adoptar/animales (y el #registro de antes). */
export function vistaDesdeHash(hash: string): VistaAcceso | null {
  if (hash === "#registro" || hash === "#adoptar/crear") return "crear";
  if (hash === "#adoptar/entrar") return "entrar";
  if (hash === "#adoptar/animales") return "animales";
  if (hash === "#adoptar") return "inicio";
  return null;
}

type AlEntrar = (token: string, cuenta: Cuenta) => void;

export default function AccesoAdoptante({ vista, alCambiar, alEntrar }: {
  vista: VistaAcceso; alCambiar: (v: VistaAcceso | "personal") => void; alEntrar: AlEntrar;
}) {
  return (
    <div className={`adop adop--mov acceso-adop${vista === "inicio" ? " acceso-adop--paisaje" : ""}`}>
      <div className="adop-fondo" aria-hidden="true">
        <span className="mancha mancha--rosa" /><span className="mancha mancha--lila" />
        <span className="mancha mancha--menta" /><span className="mancha mancha--amarillo" />
      </div>
      <header className="adop-barra">
        <a className="adop-marca" href="/"><Huella tam={28} color="#E8508A" />
          <span className="h adop-marca-texto acceso-marca">Patitas en Casa</span></a>
        <button className="adop-enlace adop-enlace--suave" onClick={() => alCambiar("personal")}>
          ¿Trabajas en el refugio?</button>
      </header>
      <main className="adop-contenido entrada-adop">
        {vista === "inicio" && <Opciones alCambiar={alCambiar} />}
        {vista === "entrar" && <Entrar alCambiar={alCambiar} alEntrar={alEntrar} />}
        {vista === "crear" && <Crear alCambiar={alCambiar} alEntrar={alEntrar} />}
        {vista === "animales" && <SinCuenta alCambiar={alCambiar} />}
      </main>
      {vista === "inicio" && <PaisajeEntrada />}
    </div>
  );
}

function Opciones({ alCambiar }: { alCambiar: (v: VistaAcceso) => void }) {
  return (
    <section className="acceso-caja">
      <span className="adop-cinta aparece">Adopción responsable en Cúcuta</span>
      <h1 className="h acceso-titulo aparece d1" tabIndex={-1} data-titulo>¡Vamos a encontrar a tu compañero!</h1>
      <p className="adop-sub aparece d2">Con tu cuenta guardas tu hogar, ves quién combina contigo y sigues tu solicitud.</p>
      <div className="acceso-opciones">
        <button className="opcion acceso-opcion aparece d2" onClick={() => alCambiar("entrar")}>
          <span className="opcion-icono"><Icono d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4M10 17l5-5-5-5M15 12H3" tam={26} grosor={2} /></span>
          <span className="opcion-texto"><span className="h opcion-titulo">Ya tengo cuenta</span>
            <span className="opcion-sub">Iniciar sesión</span></span>
        </button>
        <button className="opcion acceso-opcion acceso-opcion--rosa aparece d3" onClick={() => alCambiar("crear")}>
          <span className="opcion-icono"><Icono d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8a4 4 0 0 0 0 8zM19 8v6M22 11h-6" tam={26} grosor={2} /></span>
          <span className="opcion-texto"><span className="h opcion-titulo">Soy nuevo</span>
            <span className="opcion-sub">Crear cuenta</span></span>
        </button>
      </div>
      <button className="adop-enlace" onClick={() => alCambiar("animales")}>Ver los animales sin cuenta</button>
    </section>
  );
}

function Entrar({ alCambiar, alEntrar }: { alCambiar: (v: VistaAcceso) => void; alEntrar: AlEntrar }) {
  const [correo, setCorreo] = useState("");
  const [clave, setClave] = useState("");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);
  async function entrar(e: React.FormEvent) {
    e.preventDefault();
    setEnviando(true);
    setError("");
    try {
      const token = await iniciarSesion(correo.trim(), clave);
      alEntrar(token, await miCuenta(token));
    } catch (err) {
      setError(textoError(err));
    } finally {
      setEnviando(false);
    }
  }
  return (
    <form className="acceso-caja acceso-form" onSubmit={entrar}>
      <h1 className="h acceso-titulo" tabIndex={-1} data-titulo>Entrar como adoptante</h1>
      <p className="adop-sub">Qué bueno verte otra vez.</p>
      <label className="acceso-campo">Correo<input type="email" required autoComplete="username" value={correo}
        onChange={(e) => setCorreo(e.target.value)} /></label>
      <label className="acceso-campo">Contraseña<input type="password" required autoComplete="current-password"
        value={clave} onChange={(e) => setClave(e.target.value)} /></label>
      {error && <p className="adop-mensaje adop-mensaje--error" role="alert">{error}</p>}
      <button className="adop-boton" disabled={enviando}><span className="h">{enviando ? "Entrando…" : "Entrar"}</span>
        <span className="adop-boton-punta"><Icono d={FLECHA.adelante} /></span></button>
      <p className="acceso-pie"><button type="button" className="adop-enlace" onClick={() => alCambiar("crear")}>
        Soy nuevo: crear cuenta</button>
        <button type="button" className="adop-enlace adop-enlace--suave" onClick={() => alCambiar("inicio")}>Volver</button></p>
    </form>
  );
}

function Crear({ alCambiar, alEntrar }: { alCambiar: (v: VistaAcceso) => void; alEntrar: AlEntrar }) {
  const [correo, setCorreo] = useState("");
  const [nombre, setNombre] = useState("");
  const [clave, setClave] = useState("");
  const [autoriza, setAutoriza] = useState(false);
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);
  async function crear(e: React.FormEvent) {
    e.preventDefault();
    const problema = problemaContrasena(clave);
    if (problema) return setError(problema);
    if (!autoriza) return setError("Debes autorizar el tratamiento de tus datos.");
    setEnviando(true);
    setError("");
    try {
      await registrarAdoptante(correo.trim(), nombre.trim(), clave, autoriza);
      // Entra directo a su bienvenida. DT-09: si el correo ya tenía cuenta, el servidor responde
      // igual; entonces solo funciona su contraseña de siempre y se le dice sin revelar nada.
      try {
        const token = await iniciarSesion(correo.trim(), clave);
        alEntrar(token, await miCuenta(token));
      } catch {
        setError("Si este correo ya tenía cuenta, entra con tu contraseña de siempre en «Ya tengo cuenta».");
      }
    } catch (err) {
      setError(textoError(err));
    } finally {
      setEnviando(false);
    }
  }
  return (
    <form className="acceso-caja acceso-form" onSubmit={crear}>
      <h1 className="h acceso-titulo" tabIndex={-1} data-titulo>Crear mi cuenta de adoptante</h1>
      <p className="adop-sub">Un minuto y empiezas a conocer a los peludos.</p>
      <label className="acceso-campo">Correo<input type="email" required autoComplete="email" value={correo}
        onChange={(e) => setCorreo(e.target.value)} /></label>
      <label className="acceso-campo">Nombre<input required autoComplete="name" value={nombre}
        onChange={(e) => setNombre(e.target.value)} /></label>
      <label className="acceso-campo">Contraseña (12 caracteres o más)<input type="password" required
        autoComplete="new-password" value={clave} onChange={(e) => setClave(e.target.value)} /></label>
      <label className="acceso-casilla"><input type="checkbox" checked={autoriza}
        onChange={(e) => setAutoriza(e.target.checked)} />
        <span>Autorizo a Patitas en Casa a tratar mis datos solo para gestionar la adopción (Ley 1581 de 2012).</span></label>
      {error && <p className="adop-mensaje adop-mensaje--error" role="alert">{error}</p>}
      <button className="adop-boton" disabled={enviando}><span className="h">{enviando ? "Creando…" : "Crear cuenta y entrar"}</span>
        <span className="adop-boton-punta"><Icono d={FLECHA.adelante} /></span></button>
      <p className="acceso-pie"><button type="button" className="adop-enlace" onClick={() => alCambiar("entrar")}>
        Ya tengo cuenta: iniciar sesión</button>
        <button type="button" className="adop-enlace adop-enlace--suave" onClick={() => alCambiar("inicio")}>Volver</button></p>
    </form>
  );
}

/** Catálogo público (sin cuenta): se puede mirar; para solicitar hace falta la cuenta (#477: tarjetas
 *  de foto y nombre con el detalle debajo de la fila). */
function SinCuenta({ alCambiar }: { alCambiar: (v: VistaAcceso) => void }) {
  const [animales, setAnimales] = useState<AnimalPublicado[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { catalogo().then(setAnimales).catch((e) => setError(textoError(e))); }, []);
  return (
    <section className="acceso-catalogo">
      <div className="elegir-cabeza">
        <button className="adop-redondo" aria-label="Volver" onClick={() => alCambiar("inicio")}><Icono d={FLECHA.izq} /></button>
        <h1 className="h elegir-titulo" tabIndex={-1} data-titulo>Esperan un hogar</h1>
        <span className="adop-contador">{animales ? animales.length : ""}</span>
      </div>
      {error && <p className="adop-mensaje adop-mensaje--error" role="alert">{error}</p>}
      {!animales && !error && <Cargando que="los animales" />}
      {animales && animales.length === 0 && <p className="adop-vacio">No hay animales publicados ahora. Vuelve pronto.</p>}
      {/* #477: sin cuenta, elegir o ver en «Elige a tu compañero» pasa primero por la cuenta. */}
      {animales && animales.length > 0 && (
        <CatalogoEnFilas animales={animales} alElegir={() => alCambiar("crear")} alVerEnElegir={() => alCambiar("entrar")} />)}
      <div className="acceso-llamado">
        <p className="adop-sub">¿Te enamoraste de alguno? Crea tu cuenta para ver quién combina con tu hogar y solicitarlo.</p>
        <button className="adop-boton acceso-boton" onClick={() => alCambiar("crear")}>
          <span className="h">Crear mi cuenta</span><span className="adop-boton-punta"><Icono d={FLECHA.adelante} /></span></button>
      </div>
    </section>
  );
}
