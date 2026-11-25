import { useState } from "react";
import { Cuenta, iniciarSesion, miCuenta } from "./api";
import Administracion from "./Administracion";
import AdopcionesCoordinador from "./AdopcionesCoordinador";
import Adoptante from "./Adoptante";
import Cola from "./Cola";
import Historial from "./Historial";
import Indicadores from "./Indicadores";
import { textoError } from "./mensajes";
import { NOMBRE_PANTALLA, Pantalla, pantallasDelRol } from "./navegacion";
import Refugio from "./Refugio";
import RegistroAdoptante from "./RegistroAdoptante";
import MisRescates from "./MisRescates";
import Piloto from "./Piloto";
import Rescatista from "./Rescatista";
import Despertando from "./Despertando";

/** Íconos del menú (trazos de 24×24, como los del prototipo). */
const ICONO_PANTALLA: Record<Pantalla, string> = {
  cola: "M4 6h16M4 12h16M4 18h10",
  historial: "M12 7v5l3 2M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18z",
  rescates: "M12 21s-7-6.5-7-12a7 7 0 0 1 14 0c0 5.5-7 12-7 12zM12 7a2 2 0 1 0 0 4a2 2 0 1 0 0-4z",
  mis_rescates: "M5 12l5 5 9-10",
  refugio: "M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z",
  adopcion: "M12 21s-7.5-4.6-9.6-9.2C.9 8.4 3 4.5 6.8 4.5c2.1 0 3.6 1.2 5.2 3 1.6-1.8 3.1-3 5.2-3 3.8 0 5.9 3.9 4.4 7.3C19.5 16.4 12 21 12 21z",
  adopciones: "M12 21s-7.5-4.6-9.6-9.2C.9 8.4 3 4.5 6.8 4.5c2.1 0 3.6 1.2 5.2 3 1.6-1.8 3.1-3 5.2-3 3.8 0 5.9 3.9 4.4 7.3C19.5 16.4 12 21 12 21z",
  indicadores: "M4 20V10M10 20V4M16 20v-7M22 20H2",
  piloto: "M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3",
  administracion: "M8 15a4 4 0 1 0 0-8a4 4 0 1 0 0 8zM12 11h9M18 11v3M21 11v3",
};

export default function App() {
  const [token, setToken] = useState<string | null>(null);
  const [cuenta, setCuenta] = useState<Cuenta | null>(null);
  const [pantalla, setPantalla] = useState<Pantalla | null>(null);
  if (!token || !cuenta) {
    return <InicioSesion alEntrar={(t, c) => {
      setToken(t); setCuenta(c); setPantalla(pantallasDelRol(c.rol)[0] ?? null);
    }} />;
  }
  const salir = () => { setToken(null); setCuenta(null); };
  // #420: el adoptante tiene su propia vista («Elige a tu compañero»), sin la barra del personal.
  if (cuenta.rol === "adoptante") return <Adoptante token={token} nombre={cuenta.nombre} alSalir={salir} />;
  const pantallas = pantallasDelRol(cuenta.rol);
  // #432: como el prototipo del personal, menú lateral oscuro en el computador y compacto en el
  // celular. Mismas pantallas, mismos permisos: solo cambia la forma.
  return (
    <main className="panel personal">
      {/* D-08: el primer Tab ofrece ir directo a la cola sin recorrer la barra. */}
      {pantalla === "cola" && <a className="ds-saltar" href="#cola">Saltar a la cola</a>}
      <Despertando />
      <aside className="lateral">
        <p className="lateral-marca"><img src="/app/icono.svg" alt="" width="28" height="28" />
          <span>Patitas en Casa</span></p>
        {pantallas.length > 1 && (
          <nav className="ds-pestanas" aria-label="Secciones">
            {pantallas.map((p) => (
              <button key={p} aria-current={p === pantalla ? "page" : undefined}
                onClick={() => setPantalla(p)}>
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d={ICONO_PANTALLA[p]} /></svg>
                {NOMBRE_PANTALLA[p]}</button>))}
          </nav>)}
        <div className="lateral-cuenta">
          <img className="icono-rol" src={`/diseno/roles/${cuenta.rol}.svg`} alt="" width="36" height="36" />
          <span className="quien"><strong>{cuenta.nombre}</strong><span className="rol">{cuenta.rol}</span></span>
          <button onClick={salir}>Salir</button>
        </div>
      </aside>
      <div className="contenido">
        <header className="encabezado">
          <p className="saludo">Buen turno</p>  {/* fijo: la captura e2e no cambia con la hora */}
          <h1>{pantalla ? NOMBRE_PANTALLA[pantalla] : "Panel"}</h1>
        </header>
      {pantalla === "cola" && <Cola token={token} cuenta={cuenta} />}
      {pantalla === "historial" && <Historial token={token} />}
      {pantalla === "rescates" && <Rescatista token={token} />}
      {pantalla === "mis_rescates" && <MisRescates token={token} />}
      {pantalla === "refugio" && <Refugio token={token} rol={cuenta.rol} />}
      {pantalla === "adopciones" && <AdopcionesCoordinador token={token} />}
      {pantalla === "indicadores" && <Indicadores token={token} rol={cuenta.rol} />}
      {pantalla === "piloto" && <Piloto token={token} />}
      {pantalla === "administracion" && <Administracion token={token} yo={cuenta.correo} />}
      {pantalla === null && <p className="ds-vacio">Tu rol no tiene pantallas en el panel.</p>}
      </div>
    </main>
  );
}

function InicioSesion({ alEntrar }: { alEntrar: (token: string, cuenta: Cuenta) => void }) {
  const [correo, setCorreo] = useState("");
  const [clave, setClave] = useState("");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);
  // El botón «Adoptar» de la página de inicio abre /panel/#registro (#145).
  const [registro, setRegistro] = useState(() => window.location.hash === "#registro");
  const [aviso, setAviso] = useState("");

  async function entrar(evento: React.FormEvent) {
    evento.preventDefault();
    setEnviando(true);
    setError("");
    try {
      const token = await iniciarSesion(correo.trim(), clave);
      alEntrar(token, await miCuenta(token));
    } catch (e) {
      setError(textoError(e));
    } finally {
      setEnviando(false);
    }
  }

  if (registro) {
    return (
      <main className="acceso">
        <RegistroAdoptante alTerminar={(m) => { setAviso(m); setRegistro(false); }} />
      </main>
    );
  }
  return (
    <main className="acceso">
      <Despertando />
      <form className="ds-tarjeta inicio" onSubmit={entrar}>
        <img src="/app/icono.svg" alt="" width="56" height="56" className="logo" />
        <h1>Patitas en Casa</h1>
        <p className="ds-suave">Panel del personal. Entra con tu cuenta.</p>
        {aviso && <p className="ds-msg ds-msg--ok" role="status">{aviso}</p>}
        <label>Correo<input type="email" value={correo} required autoComplete="username"
          onChange={(e) => setCorreo(e.target.value)} /></label>
        <label>Contraseña<input type="password" value={clave} required
          autoComplete="current-password" onChange={(e) => setClave(e.target.value)} /></label>
        {error && <p className="ds-msg ds-msg--error" role="alert">{error}</p>}
        <button className="principal" disabled={enviando}>{enviando ? "Entrando…" : "Entrar"}</button>
        <p><button type="button" className="enlace" onClick={() => setRegistro(true)}>
          ¿Quieres adoptar? Crea tu cuenta</button></p>
      </form>
    </main>
  );
}
