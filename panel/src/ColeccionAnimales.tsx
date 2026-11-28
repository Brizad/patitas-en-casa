// «La colección» (#508): todos los publicados en cartas numeradas, filtros en el cliente y el
// contador real del servidor (GET /adopciones/coleccion). Los adoptados son solo los que tienen la
// adopción aprobada (máx. 8, los más recientes): en gris, con su sello y sin botón.
import { useState } from "react";
import type { AnimalPublicado, Coleccion } from "./apiAdopcion";
import CartaAnimal from "./CartaAnimal";
import { FiltroColeccion, coleccionNumerada, filtrarColeccion, filtrosColeccion } from "./datosCarta";

export default function ColeccionAnimales({ disponibles, coleccion, abribles, alVer }: {
  disponibles: AnimalPublicado[]; coleccion: Coleccion | null;
  /** Los que «Elige» puede abrir (con perfil, los compatibles; RN-05). */
  abribles: AnimalPublicado[]; alVer: (a: AnimalPublicado) => void;
}) {
  const [filtro, setFiltro] = useState<FiltroColeccion>("todos");
  const items = coleccionNumerada(disponibles, coleccion?.adoptados ?? []);
  const visibles = filtrarColeccion(items, filtro);
  const esperando = coleccion?.esperando ?? disponibles.length;
  return (
    <section className="seccion" aria-labelledby="titulo-coleccion">
      <p className="seccion-etiqueta">La colección</p>
      <h2 id="titulo-coleccion" className="h seccion-titulo">
        {esperando === 1 ? "Conoce al peludo que espera" : `Conoce a los ${esperando} peludos`}</h2>
      <p className="seccion-lead">Cada uno tiene su tipo, sus estadísticas y sus habilidades especiales.</p>
      <div className="filtros" role="group" aria-label="Filtrar la colección">
        {filtrosColeccion(items).map(([f, nombre]) => (
          <button key={f} className="filtro" aria-pressed={filtro === f} onClick={() => setFiltro(f)}>{nombre}</button>))}
      </div>
      {coleccion && (
        <p className="coleccion-contador">Ya encontraron hogar: <b>{coleccion.adoptados_total}</b> · Esperando: <b>{esperando}</b></p>)}
      <ul className="album">
        {visibles.map(({ a, numero, adoptado }) => (
          <li key={a.animal_id}>
            <CartaAnimal a={a} mini numero={numero} adoptado={adoptado}>
              {!adoptado && abribles.some((x) => x.animal_id === a.animal_id) && (
                <button className="carta-boton carta-boton--suave h" onClick={() => alVer(a)}>Conocer a {a.nombre}</button>)}
            </CartaAnimal>
          </li>))}
      </ul>
      {visibles.length === 0 && <p className="seccion-lead">Ningún peludo con este filtro por ahora.</p>}
    </section>
  );
}
