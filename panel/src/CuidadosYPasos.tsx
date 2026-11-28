// «Cuidados por nuestro equipo veterinario» y «Así funciona tu adopción» (#508), con los textos
// del prototipo docs/prototipo/adoptar-renovado.html. Iconos decorativos (aria-hidden).
import { PREGUNTAS } from "./encuesta";
import { ICONOS } from "./iconosAdopcion";
import { Icono } from "./Ilustraciones";

type Item = [keyof typeof ICONOS, string, string, string]; // icono, color, título, texto
const CUIDADOS: Item[] = [
  ["jeringa", "#FBD9E3", "Vacunas al día", "Cada peludo recibe sus vacunas según su edad."],
  ["tijeras", "#E9E2FF", "Esterilización", "Para una vida más sana y evitar camadas sin hogar."],
  ["curita", "#FFF0B8", "Desparasitación", "Interna y externa, antes de ir a casa."],
  ["estetoscopio", "#D6E8F7", "Chequeo general", "Un veterinario revisa su salud y su comportamiento."],
];
const PASOS: Item[] = [
  ["lista", "#FFD23F", "Encuesta", `${PREGUNTAS.length} preguntas sobre tu hogar.`],
  ["lupa", "#E9E2FF", "Conócelo", "Elige a tu compañero ideal."],
  ["casa", "#FBD9E3", "Visita", "Revisamos que el hogar sea seguro."],
  ["estetoscopio", "#D6E8F7", "Chequeo veterinario", "Último control antes de salir."],
  ["corazon", "#D7F0DC", "¡A casa!", "Empieza su nueva vida contigo."],
];

export default function CuidadosYPasos() {
  return (
    <>
      <section className="seccion seccion--vet" aria-labelledby="titulo-cuidados">
        <p className="seccion-etiqueta">Antes de llegar a tu casa</p>
        <h2 id="titulo-cuidados" className="h seccion-titulo">Cuidados por nuestro equipo veterinario</h2>
        <p className="seccion-lead">Ningún peludo sale del refugio sin estar sano y listo para su nuevo hogar.</p>
        <ul className="cuidados">
          {CUIDADOS.map(([icono, color, titulo, texto]) => (
            <li key={titulo}>
              <span className="cuidado-circulo" style={{ backgroundColor: color }}><Icono d={ICONOS[icono]} tam={36} grosor={2.2} /></span>
              <h3 className="h">{titulo}</h3><p>{texto}</p></li>))}
        </ul>
      </section>
      <section className="seccion" aria-labelledby="titulo-pasos">
        <p className="seccion-etiqueta">Paso a paso</p>
        <h2 id="titulo-pasos" className="h seccion-titulo">Así funciona tu adopción</h2>
        <p className="seccion-lead">Un proceso sencillo y responsable, para ti y para tu nuevo compañero.</p>
        <ol className="pasos-adopcion">
          {PASOS.map(([icono, color, titulo, texto]) => (
            <li key={titulo}>
              <span className="paso-circulo" style={{ backgroundColor: color }}><Icono d={ICONOS[icono]} tam={34} grosor={2.2} /></span>
              <span><h3 className="h">{titulo}</h3><p>{texto}</p></span></li>))}
        </ol>
      </section>
    </>
  );
}
