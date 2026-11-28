// «Mi hogar» renovado (#516, docs/prototipo/mi-hogar-renovado.html): las respuestas REALES
// guardadas en el perfil, cada una con «Cambiar» que abre la encuesta en esa pregunta. Si no
// aceptó el seguimiento, se avisa: sin él no hay matches ni solicitudes (RN-10).
import "./mi-hogar.css";
import type { Perfil } from "./apiAdopcion";
import { Clave, ICONO, PREGUNTAS, resumenHogar } from "./encuesta";
import gatitos from "./img/adopcion/hogar-gatitos.jpg";
import { FLECHA, Icono } from "./Ilustraciones";

const ESTILO: Partial<Record<Clave, [string, string]>> = { // icono y color del cuadro
  vivienda: [ICONO.casa, "#FFF0B8"], tiene_patio: [ICONO.sol, "#D7F0DC"], hay_ninos: [ICONO.ninos, "#FBD9E3"],
  otros_animales: [ICONO.mascotas, "#E9E2FF"], horas_solo_al_dia: [ICONO.reloj, "#D6E8F7"],
  experiencia: [ICONO.corazon, "#FBD9E3"], acepta_seguimiento: [ICONO.calendario, "#D7F0DC"],
};
const AVISO = "M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18zM12 7v6M12 16.5v.5";
const REPETIR = "M4 12a8 8 0 0 1 14-5.3M20 12a8 8 0 0 1-14 5.3M18 3v4h-4M6 21v-4h4";

export default function MiHogar({ perfil, alCambiar, alEmpezar, alVerCompaneros, alAtras }: {
  perfil: Perfil | null; alCambiar: (paso: number) => void; alEmpezar: () => void; alVerCompaneros: () => void;
  alAtras: () => void;
}) {
  const respuestas = resumenHogar(perfil);
  const sinSeguimiento = perfil !== null && !perfil.acepta_seguimiento;
  const pasoSeguimiento = PREGUNTAS.findIndex((q) => q.clave === "acepta_seguimiento");
  return (
    <div className="mihogar">
      {/* En el celular no hay menú arriba: se vuelve al inicio desde aquí. */}
      <button className="adop-redondo solo-movil mihogar-atras" aria-label="Atrás" onClick={alAtras}>
        <Icono d={FLECHA.izq} /></button>
      <header className="mihogar-cabeza">
        <div>
          <p className="mihogar-etiqueta">Tu perfil de adoptante</p>
          <h1 className="h mihogar-titulo" tabIndex={-1} data-titulo>Así es tu hogar</h1>
          <p className="mihogar-texto">Con esto elegimos a los peludos que mejor combinan contigo. Puedes cambiarlo
            cuando quieras.</p>
          {perfil && (
            <span className={`mihogar-estado mihogar-estado--${sinSeguimiento ? "no" : "si"}`}>
              <Icono d={sinSeguimiento ? AVISO : "M4 12l5 5L20 6"} tam={18} grosor={2.2} />
              {sinSeguimiento ? "Falta aceptar el seguimiento" : "Listo para adoptar"}</span>)}
        </div>
        <img className="mihogar-foto" src={gatitos} alt="" width={1308} height={736} />
      </header>
      {sinSeguimiento && (
        <div className="mihogar-aviso" role="note">
          <Icono d={AVISO} tam={34} grosor={2.2} />
          <p><b className="h">Te falta un paso para poder adoptar</b>
            <span>Para enviar solicitudes necesitas aceptar el seguimiento a los 30, 90 y 180 días.</span></p>
          <button className="mihogar-aviso-boton h" onClick={() => alCambiar(pasoSeguimiento)}>Cambiar esta respuesta</button>
        </div>)}
      {!perfil ? (
        <div className="mihogar-vacio">
          <p>Aún no nos has contado cómo es tu hogar. Son {PREGUNTAS.length} preguntas rápidas.</p>
          <button className="adop-boton" onClick={alEmpezar}><span className="h">¡Empezar!</span>
            <span className="adop-boton-punta"><Icono d={FLECHA.adelante} /></span></button>
        </div>
      ) : (<>
        <h2 className="h mihogar-h2">Tus respuestas
          <button className="mihogar-todas h" onClick={() => alCambiar(0)}>✎ Cambiar todas</button></h2>
        <ul className="mihogar-respuestas">
          {respuestas.map((r) => {
            const [icono, color] = ESTILO[r.clave] ?? [ICONO.estrella, "#FFFFFF"];
            const seguimiento = r.clave === "acepta_seguimiento";
            return (
              <li key={r.clave} className={`${seguimiento ? "ancha" : ""}${seguimiento && sinSeguimiento ? " alerta" : ""}`}>
                <span className="mihogar-icono" style={{ backgroundColor: color }}><Icono d={icono} tam={26} grosor={2.2} /></span>
                <span className="mihogar-pregunta">{r.pregunta}</span>
                <span className="mihogar-respuesta h">{r.respuesta}</span>
                <button className="mihogar-cambiar" onClick={() => alCambiar(r.paso)}
                  aria-label={`Cambiar: ${r.pregunta}`}>Cambiar</button>
              </li>);
          })}
        </ul>
        <div className="mihogar-pie">
          <button className="adop-boton" onClick={alVerCompaneros}><span className="h">Ver mis compañeros</span>
            <span className="adop-boton-punta"><Icono d={FLECHA.adelante} /></span></button>
          <button className="adop-boton adop-boton--claro mihogar-repetir" onClick={alEmpezar}>
            <span className="h">Responder de nuevo la encuesta</span>
            <span className="adop-boton-punta"><Icono d={REPETIR} /></span></button>
        </div>
        <p className="mihogar-privacidad">Tus respuestas solo las ve el equipo del refugio para evaluar tu solicitud.</p>
      </>)}
    </div>
  );
}
