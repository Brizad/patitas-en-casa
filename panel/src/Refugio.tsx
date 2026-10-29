import { useCallback, useEffect, useState } from "react";
import { ErrorApi } from "./api";
import { Ingreso, Ocupacion, nivelOcupacion, ocupacion, registrarIngreso } from "./apiRefugio";
import Fichas from "./Fichas";
import { textoError } from "./mensajes";

const VACIO: Ingreso = { nombre: "", especie: "perro", estado_salud: "", vacunado: false,
                         esterilizado: false };

/** Pantalla del refugio: ocupación para el personal; ingresos solo el coordinador (P-06). */
export default function Refugio({ token, rol }: { token: string; rol: string }) {
  const [datos, setDatos] = useState<Ocupacion | null>(null);
  const [error, setError] = useState("");

  const recargar = useCallback(async () => {
    try {
      setDatos(await ocupacion(token));
      setError("");
    } catch (e) {
      setError(textoError(e));
    }
  }, [token]);

  useEffect(() => { void recargar(); }, [recargar]);
  const nivel = datos ? nivelOcupacion(datos.porcentaje) : "normal";

  return (
    <section className="pagina">
      <div className="tarjeta">
        <div className="fila-titulo">
          <h2>Ocupación del refugio</h2>
          <button onClick={() => void recargar()}>Actualizar</button>
        </div>
        {error && <p className="error" role="alert">{error}</p>}
        {datos && (
          <>
            <p><b>{datos.ocupacion}</b> cupos ocupados ({datos.porcentaje} %)</p>
            <div className={`barra-ocupacion ${nivel}`} role="meter" aria-valuemin={0}
              aria-valuemax={100} aria-valuenow={datos.porcentaje} aria-label="Ocupación">
              <span style={{ width: `${Math.min(datos.porcentaje, 100)}%` }} />
            </div>
            {nivel === "alerta" && <p className="error">Ocupación en nivel de alerta
              (90 % o más, RN-04).</p>}
            {nivel === "lleno" && <p className="error">Sin cupos: los ingresos se rechazan.</p>}
          </>)}
      </div>
      {rol === "coordinador" ? <FormularioIngreso token={token} alGuardar={recargar} /> : (
        <p className="nota">Solo coordinación registra ingresos (pantalla P-06).</p>)}
      {/* La ocupación cambia con cada ingreso o egreso: la lista se vuelve a pedir. */}
      <Fichas version={datos?.ocupacion} token={token} rol={rol}
        alCambiarCupo={() => void recargar()} />
    </section>
  );
}

function FormularioIngreso({ token, alGuardar }: { token: string; alGuardar: () => void }) {
  const [ingreso, setIngreso] = useState<Ingreso>(VACIO);
  const [mensaje, setMensaje] = useState("");
  const [error, setError] = useState("");
  const cambiar = <K extends keyof Ingreso>(campo: K, valor: Ingreso[K]) =>
    setIngreso({ ...ingreso, [campo]: valor });

  async function guardar(evento: React.FormEvent) {
    evento.preventDefault();
    setError("");
    try {
      const r = await registrarIngreso(token, { ...ingreso, nombre: ingreso.nombre.trim(),
                                                estado_salud: ingreso.estado_salud.trim() });
      setMensaje(`Ingreso de ${ingreso.nombre.trim()} registrado. Ocupación: ${r.ocupacion}.`);
      setIngreso(VACIO);
      alGuardar();
    } catch (e) {
      setMensaje("");
      setError(e instanceof ErrorApi && e.estado === 409
        ? "El refugio no tiene cupos: el ingreso no se registró (RN-04)." : textoError(e));
    }
  }

  return (
    <form className="tarjeta" onSubmit={guardar}>
      <h2>Registrar ingreso</h2>
      <label>Nombre<input value={ingreso.nombre} required maxLength={80}
        onChange={(e) => cambiar("nombre", e.target.value)} /></label>
      <label>Especie
        <select value={ingreso.especie}
          onChange={(e) => cambiar("especie", e.target.value as Ingreso["especie"])}>
          <option value="perro">Perro</option><option value="gato">Gato</option>
        </select></label>
      <label>Estado de salud<textarea value={ingreso.estado_salud} required rows={2}
        onChange={(e) => cambiar("estado_salud", e.target.value)} /></label>
      <label className="en-linea"><input type="checkbox" checked={ingreso.vacunado}
        onChange={(e) => cambiar("vacunado", e.target.checked)} /> Vacunado</label>
      <label className="en-linea"><input type="checkbox" checked={ingreso.esterilizado}
        onChange={(e) => cambiar("esterilizado", e.target.checked)} /> Esterilizado</label>
      {error && <p className="error" role="alert">{error}</p>}
      {mensaje && <p className="resultado" role="status">{mensaje}</p>}
      <div className="acciones"><button className="principal">Registrar ingreso</button></div>
    </form>
  );
}
