import { useState } from "react";
import { Cuenta, iniciarSesion, miCuenta } from "./api";
import Administracion from "./Administracion";
import Cola from "./Cola";
import { textoError } from "./mensajes";
import { NOMBRE_PANTALLA, Pantalla, pantallasDelRol } from "./navegacion";
import Refugio from "./Refugio";
import Rescatista from "./Rescatista";

export default function App() {
  const [token, setToken] = useState<string | null>(null);
  const [cuenta, setCuenta] = useState<Cuenta | null>(null);
  const [pantalla, setPantalla] = useState<Pantalla | null>(null);
  if (!token || !cuenta) {
    return <InicioSesion alEntrar={(t, c) => {
      setToken(t); setCuenta(c); setPantalla(pantallasDelRol(c.rol)[0] ?? null);
    }} />;
  }
  const pantallas = pantallasDelRol(cuenta.rol);
  return (
    <main className="panel">
      <header className="barra">
        <b>Patitas en Casa · Panel</b>
        <span>{cuenta.nombre} · {cuenta.rol}</span>
        <button onClick={() => { setToken(null); setCuenta(null); }}>Salir</button>
      </header>
      {pantallas.length > 1 && (
        <nav className="pestanas" aria-label="Secciones">
          {pantallas.map((p) => (
            <button key={p} aria-current={p === pantalla ? "page" : undefined}
              onClick={() => setPantalla(p)}>{NOMBRE_PANTALLA[p]}</button>))}
        </nav>)}
      {pantalla === "cola" && <Cola token={token} cuenta={cuenta} />}
      {pantalla === "rescates" && <Rescatista token={token} />}
      {pantalla === "refugio" && <Refugio token={token} rol={cuenta.rol} />}
      {pantalla === "administracion" && <Administracion token={token} yo={cuenta.correo} />}
      {pantalla === null && <p className="vacio">Tu rol no tiene pantallas en el panel.</p>}
    </main>
  );
}

function InicioSesion({ alEntrar }: { alEntrar: (token: string, cuenta: Cuenta) => void }) {
  const [correo, setCorreo] = useState("");
  const [clave, setClave] = useState("");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

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

  return (
    <form className="tarjeta inicio" onSubmit={entrar}>
      <h1>Panel del personal</h1>
      <label>Correo<input type="email" value={correo} required autoComplete="username"
        onChange={(e) => setCorreo(e.target.value)} /></label>
      <label>Contraseña<input type="password" value={clave} required
        autoComplete="current-password" onChange={(e) => setClave(e.target.value)} /></label>
      {error && <p className="error" role="alert">{error}</p>}
      <button className="principal" disabled={enviando}>{enviando ? "Entrando…" : "Entrar"}</button>
    </form>
  );
}
