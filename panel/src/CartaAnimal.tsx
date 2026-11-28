// Carta de un animal en «Adoptar» (#508): grande en «¡Elige a tu compañero!» y mini en «La
// colección». Solo dibuja lo que trae la ficha (datosCarta.ts).
import type { ReactNode } from "react";
import "./adoptar-secciones.css";
import type { AnimalPublicado } from "./apiAdopcion";
import { barrasCarta, metaCarta, saludCarta, tipoCarta } from "./datosCarta";
import { ICONOS } from "./iconosAdopcion";
import { FotoAnimal, Icono } from "./Ilustraciones";

export default function CartaAnimal({ a, mini = false, estrella = false, numero, adoptado = false, children }: {
  a: AnimalPublicado; mini?: boolean; estrella?: boolean; numero?: string; adoptado?: boolean;
  children?: ReactNode;
}) {
  const tipo = tipoCarta(a);
  const salud = saludCarta(a);
  const habilidades = mini ? [] : a.habilidades ?? [];
  return (
    <article className={`carta${mini ? " carta--mini" : ""}${estrella ? " carta--estrella" : ""}${
      adoptado ? " carta--adoptada" : ""}`} aria-label={a.nombre}>
      {estrella && <span className="carta-corona h">★ Tu mejor match</span>}
      {numero && <span className="carta-num h">{numero}</span>}
      <div className="carta-cabeza">
        <h3 className="h carta-nombre">{a.nombre}</h3>
        {tipo && <span className="carta-tipo" style={{ backgroundColor: tipo[1] }}>{tipo[0]}</span>}
      </div>
      <FotoAnimal a={a} alt={`Foto de ${a.nombre}`} className="carta-foto" />
      {adoptado && <span className="carta-sello h">¡Encontró hogar!</span>}
      {!mini && <p className="carta-meta">{metaCarta(a)}</p>}
      {barrasCarta(a).length > 0 && (
        <ul className="carta-barras">
          {barrasCarta(a).map((b) => (
            <li key={b.nombre}><span>{b.nombre}</span>
              <span className="carta-barra" role="img" aria-label={`${b.valor} de 5`}>
                <i style={{ width: `${b.valor * 20}%`, backgroundColor: b.color }} /></span></li>))}
        </ul>)}
      {habilidades.length > 0 && (
        <ul className="carta-habilidades">{habilidades.map((h) => <li key={h}>★ {h}</li>)}</ul>)}
      {salud.length > 0 && (
        <ul className="carta-salud">
          {salud.map((s) => (
            <li key={s.largo} className={s.si ? "si" : "no"}>
              <Icono d={s.si ? ICONOS.visto : ICONOS.no} tam={13} grosor={2.6} />
              <abbr title={`${s.largo}: ${s.si ? "sí" : "no"}`}>{s.corto}</abbr>
              <span className="visualmente-oculto">{s.si ? ": sí" : ": no"}</span></li>))}
        </ul>)}
      {children}
    </article>
  );
}
