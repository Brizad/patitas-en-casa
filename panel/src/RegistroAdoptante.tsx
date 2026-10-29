import { useState } from "react";
import { problemaContrasena } from "./apiAdmin";
import { registrarAdoptante } from "./apiAdopcion";
import { textoError } from "./mensajes";

/** RF-08: quien quiere adoptar crea su propia cuenta desde la pantalla de inicio. */
export default function RegistroAdoptante({ alTerminar }: { alTerminar: (m: string) => void }) {
  const [correo, setCorreo] = useState("");
  const [nombre, setNombre] = useState("");
  const [clave, setClave] = useState("");
  const [autoriza, setAutoriza] = useState(false);
  const [error, setError] = useState("");

  async function crear(evento: React.FormEvent) {
    evento.preventDefault();
    const problema = problemaContrasena(clave);
    if (problema) return setError(problema);
    if (!autoriza) return setError("Debes autorizar el tratamiento de tus datos.");
    try {
      await registrarAdoptante(correo.trim(), nombre.trim(), clave, autoriza);
      alTerminar("Cuenta creada. Ya puedes entrar con tu correo y contraseña.");
    } catch (e) {
      setError(textoError(e));
    }
  }

  return (
    <form className="tarjeta inicio" onSubmit={crear}>
      <h2>Quiero adoptar</h2>
      <label>Correo<input type="email" required value={correo} autoComplete="email"
        onChange={(e) => setCorreo(e.target.value)} /></label>
      <label>Nombre<input required value={nombre} onChange={(e) => setNombre(e.target.value)} />
      </label>
      <label>Contraseña (12 caracteres o más)<input type="password" required value={clave}
        autoComplete="new-password" onChange={(e) => setClave(e.target.value)} /></label>
      <label className="en-linea"><input type="checkbox" checked={autoriza}
        onChange={(e) => setAutoriza(e.target.checked)} />
        Autorizo a Patitas en Casa a tratar mis datos solo para gestionar la adopción
        (Ley 1581 de 2012).</label>
      {error && <p className="error" role="alert">{error}</p>}
      <button className="principal">Crear cuenta</button>
    </form>
  );
}
