// «¡Elige a tu compañero!» en la portada del adoptante (#508). Con la encuesta respondida (y el
// seguimiento aceptado), sus 3 mejores matches reales: el mismo cálculo de «Combinan» (RF-09 y
// mejores()). Sin encuesta, 3 cartas boca abajo que invitan a responderla.
import type { MiSolicitud, Recomendado } from "./apiAdopcion";
import CartaAnimal from "./CartaAnimal";
import { trio } from "./datosCarta";
import { abierta, solicitudDe } from "./flujoAdopcion";
import { Huella } from "./Ilustraciones";

export default function EligeCompanero({ mejores, mias, enviando, alElegir, alVerSolicitud, alEmpezar }: {
  /** null: sin encuesta (o sin seguimiento aceptado). */
  mejores: Recomendado[] | null; mias: MiSolicitud[]; enviando: boolean;
  alElegir: (a: Recomendado) => void; alVerSolicitud: (a: Recomendado) => void; alEmpezar: () => void;
}) {
  const conMatches = mejores !== null && mejores.length > 0;
  return (
    <section className="seccion seccion--elige" aria-labelledby="titulo-elige">
      <p className="seccion-etiqueta">{conMatches ? "Según tu encuesta" : "Tus matches"}</p>
      <h2 id="titulo-elige" className="h seccion-titulo">¡Elige a tu compañero!</h2>
      <p className="seccion-lead">{conMatches
        ? `Estos son tus ${mejores.length === 1 ? "mejor match" : `${mejores.length} mejores matches`}. `
          + "Mira sus estadísticas y elige con quién quieres empezar tu aventura."
        : "Responde la encuesta y te mostramos los 3 que mejor combinan con tu hogar."}</p>
      {conMatches ? (
        <div className="trio">
          {trio(mejores).map((a) => {
            const suya = solicitudDe(mias, a.animal_id);
            return (
              <CartaAnimal key={a.animal_id} a={a} estrella={a === mejores[0]}>
                {abierta(suya)
                  ? <button className="carta-boton h" onClick={() => alVerSolicitud(a)}>Ver mi solicitud</button>
                  : <button className="carta-boton h" disabled={enviando} onClick={() => alElegir(a)}>
                      Elegir a {a.nombre}</button>}
              </CartaAnimal>);
          })}
        </div>
      ) : (
        <>
          <div className="trio trio--boca-abajo" aria-hidden="true">
            {[0, 1, 2].map((i) => (
              <div key={i} className={`carta carta--boca-abajo${i === 1 ? " carta--estrella" : ""}`}>
                <Huella tam={64} color="#C9BDF5" /><span className="h">?</span></div>))}
          </div>
          <button className="adop-boton seccion-boton" onClick={alEmpezar}>
            <span className="h">Responde la encuesta y descúbrelos</span></button>
        </>
      )}
    </section>
  );
}
