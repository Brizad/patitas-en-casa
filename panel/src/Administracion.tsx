import { useCallback, useEffect, useState } from "react";
import {
  CuentaAdmin, CuentaNueva, ROLES, RefugioAdmin, cambiarActivo, crearCuenta, crearRefugio,
  cuentas, problemaContrasena, refugios, vincular,
} from "./apiAdmin";
import { textoError } from "./mensajes";

const NUEVA: CuentaNueva = { correo: "", nombre: "", rol: "veterinario", contrasena: "" };

/** Administración (RF-13, RF-14, RF-16): refugios, cuentas, vínculo y suspensión. */
export default function Administracion({ token, yo }: { token: string; yo: string }) {
  const [lista, setLista] = useState<CuentaAdmin[]>([]);
  const [sedes, setSedes] = useState<RefugioAdmin[]>([]);
  const [mensaje, setMensaje] = useState("");
  const [error, setError] = useState("");

  const recargar = useCallback(async () => {
    try {
      const [c, r] = await Promise.all([cuentas(token), refugios(token)]);
      setLista(c);
      setSedes(r);
    } catch (e) {
      setError(textoError(e));
    }
  }, [token]);

  useEffect(() => { void recargar(); }, [recargar]);

  async function hacer(accion: () => Promise<unknown>, exito: string) {
    setError("");
    try {
      await accion();
      setMensaje(exito);
      await recargar();
      return true;
    } catch (e) {
      setMensaje("");
      setError(textoError(e));
      return false;
    }
  }

  return (
    <section className="pagina">
      {error && <p className="error" role="alert">{error}</p>}
      {mensaje && <p className="resultado" role="status">{mensaje}</p>}
      <div className="tarjeta">
        <h2>Cuentas del personal</h2>
        <table className="tabla">
          <thead><tr><th>Cuenta</th><th>Rol</th><th>Refugio</th><th>Estado</th></tr></thead>
          <tbody>
            {lista.map((c) => (
              <tr key={c.correo}>
                <td>{c.nombre}<br /><small>{c.correo}</small></td>
                <td>{c.rol}</td>
                <td>
                  <select aria-label={`Refugio de ${c.correo}`} value={c.refugio_id ?? ""}
                    onChange={(e) => {
                      const id = e.target.value ? Number(e.target.value) : null;
                      void hacer(() => vincular(token, c.correo, id), `Refugio de ${c.correo} actualizado.`);
                    }}>
                    <option value="">Sin refugio</option>
                    {sedes.map((s) => <option key={s.id} value={s.id}>{s.nombre}</option>)}
                  </select>
                </td>
                <td>
                  {c.activo ? "Activa" : "Suspendida"}{" "}
                  {c.correo !== yo && (
                    <button onClick={() => void hacer(() => cambiarActivo(token, c.correo, !c.activo),
                      `${c.correo} ${c.activo ? "suspendida: pierde el acceso de inmediato" : "reactivada"}.`)}>
                      {c.activo ? "Suspender" : "Reactivar"}</button>)}
                </td>
              </tr>))}
          </tbody>
        </table>
      </div>
      <NuevaCuenta hacer={hacer} token={token} />
      <div className="tarjeta">
        <h2>Refugios</h2>
        <ul className="lista-simple">
          {sedes.map((s) => <li key={s.id}>{s.nombre}{s.direccion && ` (${s.direccion})`}:{" "}
            {s.ocupados}/{s.capacidad} cupos</li>)}
        </ul>
        <NuevoRefugio hacer={hacer} token={token} />
      </div>
    </section>
  );
}

type Hacer = (accion: () => Promise<unknown>, exito: string) => Promise<boolean>;

function NuevaCuenta({ token, hacer }: { token: string; hacer: Hacer }) {
  const [c, setC] = useState<CuentaNueva>(NUEVA);
  const [aviso, setAviso] = useState("");
  return (
    <form className="tarjeta" onSubmit={async (e) => {
      e.preventDefault();
      const problema = problemaContrasena(c.contrasena);
      setAviso(problema ?? "");
      if (!problema && await hacer(() => crearCuenta(token, c), `Cuenta ${c.correo} creada.`)) {
        setC(NUEVA); // la contraseña no se queda en pantalla
      }
    }}>
      <h2>Crear cuenta</h2>
      <label>Correo<input type="email" required value={c.correo}
        onChange={(e) => setC({ ...c, correo: e.target.value })} /></label>
      <label>Nombre<input required value={c.nombre}
        onChange={(e) => setC({ ...c, nombre: e.target.value })} /></label>
      <label>Rol<select value={c.rol} onChange={(e) => setC({ ...c, rol: e.target.value })}>
        {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}</select></label>
      <label>Contraseña inicial (12 caracteres o más)<input type="password" required
        autoComplete="new-password" value={c.contrasena}
        onChange={(e) => setC({ ...c, contrasena: e.target.value })} /></label>
      {aviso && <p className="error" role="alert">{aviso}</p>}
      <button className="principal">Crear cuenta</button>
    </form>
  );
}

function NuevoRefugio({ token, hacer }: { token: string; hacer: Hacer }) {
  const [nombre, setNombre] = useState("");
  const [capacidad, setCapacidad] = useState(20);
  const [direccion, setDireccion] = useState("");
  return (
    <form className="ajuste" onSubmit={async (e) => {
      e.preventDefault();
      if (await hacer(() => crearRefugio(token, nombre.trim(), capacidad, direccion.trim()),
                      `Refugio ${nombre.trim()} registrado.`)) setNombre("");
    }}>
      <label>Nombre del refugio<input required value={nombre}
        onChange={(e) => setNombre(e.target.value)} /></label>
      <label>Dirección<input value={direccion}
        onChange={(e) => setDireccion(e.target.value)} /></label>
      <label>Capacidad (cupos)<input type="number" min={1} required value={capacidad}
        onChange={(e) => setCapacidad(Number(e.target.value))} /></label>
      <button className="principal">Registrar refugio</button>
    </form>
  );
}
