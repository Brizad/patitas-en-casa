import { useEffect, useState } from "react";
import { ErrorApi } from "./api";
import {
  ESTADISTICAS, PerfilAdopcion as Perfil, SALUD, TIPOS, aEstadistica, aSalud, deSalud,
  guardarPerfilAdopcion, guardarSaludAdopcion, perfilAdopcion,
} from "./apiPerfilAdopcion";
import { textoError } from "./mensajes";

/** «Perfil de adopción» en la ficha del animal (#508), para coordinador y veterinario. Lo que
 *  se deja vacío queda «sin dato» y la página de Adoptar no lo dibuja. La salud solo la edita
 *  el veterinario; el tipo lo calcula el servidor con la regla fija. */
export default function PerfilAdopcion({ token, rol, animalId }: {
  token: string; rol: string; animalId: number;
}) {
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [sinPublicar, setSinPublicar] = useState(false);
  const [mensaje, setMensaje] = useState("");
  const veterinario = rol === "veterinario";

  useEffect(() => {
    setPerfil(null);
    setSinPublicar(false);
    setMensaje("");
    perfilAdopcion(token, animalId).then(setPerfil).catch((e) => {
      if (e instanceof ErrorApi && e.estado === 404) setSinPublicar(true);
      else setMensaje(textoError(e));
    });
  }, [token, animalId]);

  if (sinPublicar) {
    return <p className="ds-vacio">Perfil de adopción: publica primero este animal en Adopciones.</p>;
  }
  if (!perfil) return mensaje ? <p role="alert">{mensaje}</p> : null;

  async function guardar(accion: () => Promise<Perfil>, exito: string) {
    try {
      const nuevo = await accion();
      setPerfil((p) => ({ ...nuevo, catalogo_habilidades: p?.catalogo_habilidades }));
      setMensaje(exito);
    } catch (e) {
      setMensaje(textoError(e));
    }
  }

  const p = perfil;
  const marcar = (h: string, si: boolean) => setPerfil({ ...p, habilidades: si
    ? [...p.habilidades, h] : p.habilidades.filter((x) => x !== h) });
  return (
    <section aria-labelledby="titulo-perfil-adopcion">
      <h4 id="titulo-perfil-adopcion">Perfil de adopción</h4>
      <p>Tipo: <b>{p.tipo ? TIPOS[p.tipo][0] : "sin tipo (faltan estadísticas o ninguna regla aplica)"}</b></p>
      {mensaje && <p role="status">{mensaje}</p>}
      <form onSubmit={(e) => {
        e.preventDefault();
        void guardar(() => guardarPerfilAdopcion(token, animalId, p.estadisticas, p.habilidades),
          "Perfil de adopción guardado.");
      }}>
        {ESTADISTICAS.map(([clave, nombre]) => (
          <label key={clave}>{nombre} (1 a 5)
            <select value={p.estadisticas[clave] ?? ""} onChange={(e) => setPerfil({ ...p,
              estadisticas: { ...p.estadisticas, [clave]: aEstadistica(e.target.value) } })}>
              <option value="">Sin dato</option>
              {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}
            </select></label>))}
        <fieldset>
          <legend>Habilidades</legend>
          {(p.catalogo_habilidades ?? []).map((h) => (
            <label key={h} className="en-linea"><input type="checkbox" checked={p.habilidades.includes(h)}
              onChange={(e) => marcar(h, e.target.checked)} /> {h}</label>))}
        </fieldset>
        <button>Guardar perfil de adopción</button>
      </form>
      <form onSubmit={(e) => {
        e.preventDefault();
        void guardar(() => guardarSaludAdopcion(token, animalId, p.salud), "Salud guardada.");
      }}>
        <fieldset disabled={!veterinario}>
          <legend>Salud {!veterinario && "(solo la edita el veterinario)"}</legend>
          {SALUD.map(([clave, nombre]) => (
            <label key={clave}>{nombre}
              <select value={deSalud(p.salud[clave])} onChange={(e) => setPerfil({ ...p,
                salud: { ...p.salud, [clave]: aSalud(e.target.value) } })}>
                <option value="">Sin dato</option><option value="si">Sí</option><option value="no">No</option>
              </select></label>))}
          {veterinario && <button>Guardar salud</button>}
        </fieldset>
      </form>
    </section>
  );
}
