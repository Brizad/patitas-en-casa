// «Adoptar es para siempre» (#516, docs/prototipo/mi-hogar-renovado.html, vista «Encuesta:
// respondió Ahora no»). Sin el seguimiento aceptado no hay matches ni solicitudes (RN-10; el
// servidor lo exige con 403). Aquí se explica por qué y se ofrece aceptarlo.
import "./acompanar.css";
import perro from "./img/adopcion/ilustracion-perro.jpg";
import { FLECHA, Icono } from "./Ilustraciones";

const DIAS: [number, string][] = [[30, "#FFF0B8"], [90, "#FBD9E3"], [180, "#D7F0DC"]];

export default function Acompanar({ aceptando, alAceptar, alVerSinSolicitar, alInicio }: {
  aceptando: boolean; alAceptar: () => void; alVerSinSolicitar: () => void; alInicio: () => void;
}) {
  return (
    <section className="acompanar" aria-labelledby="titulo-acompanar">
      <img className="acompanar-foto" src={perro} alt="" width={389} height={615} />
      <div>
        <p className="acompanar-etiqueta">Adoptar es para siempre</p>
        <h1 id="titulo-acompanar" className="h acompanar-titulo" tabIndex={-1} data-titulo>
          Ellos nos necesitan también después de llegar a casa 💛</h1>
        <p className="acompanar-texto">En Patitas en Casa acompañamos a cada peludito en su nuevo hogar. Una visita o
          una llamada nos ayuda a saber que está sano, feliz y bien cuidado.</p>
        <p className="acompanar-texto">Por eso, para mostrarte compañeros y enviar solicitudes, necesitamos que aceptes
          este acompañamiento.</p>
        <ul className="acompanar-dias">
          {DIAS.map(([dias, color]) => (
            <li key={dias} style={{ backgroundColor: color }}><b className="h">{dias}</b><span>días</span></li>))}
        </ul>
        <button className="adop-boton adop-boton--grande" disabled={aceptando} onClick={alAceptar}>
          <span className="h">{aceptando ? "Guardando…" : "Sí, acepto acompañarlos"}</span>
          <span className="adop-boton-punta"><Icono d={FLECHA.adelante} /></span></button>
        <p className="acompanar-enlaces">
          <button className="adop-enlace" onClick={alVerSinSolicitar}>Ver a los peludos sin solicitar</button>
          <button className="adop-enlace" onClick={alInicio}>Volver al inicio</button></p>
      </div>
    </section>
  );
}
