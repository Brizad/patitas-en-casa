// «Esperan un hogar» (#477), como Google Imágenes: la tarjeta solo trae la foto y el nombre. Al
// tocarla se abre debajo de su fila un detalle a todo el ancho (las filas siguientes bajan). Se
// cierra con la misma tarjeta, la X o Esc; tocar otra lleva el detalle a la fila de esa.
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { AnimalPublicado, Recomendado } from "./apiAdopcion";
import { Barra, HoyYAdulto } from "./AdoptantePantallas";
import { convivenciaIconos, estadisticas, finDeFila, insignias, resumenCorto } from "./flujoAdopcion";
import { Corazon, FotoAnimal, Huella, Icono } from "./Ilustraciones";
import { Sonido, leerPreferencias, sonidoDeEspecie } from "./sonido";

type Animal = AnimalPublicado | Recomendado;
const ICONO = { ninos: "M12 8a3 3 0 1 0 0-6a3 3 0 0 0 0 6zM6 13l6-3 6 3M12 10v6M9 22l3-6 3 6",
  patio: "M12 22v-5M6 17h12L12 3z" };
const MARCA = { si: "M5 12l5 5 9-10", no: "M6 6l12 12M18 6L6 18", ojo: "M12 5v9M12 19h.01" };
const quieto = () => window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;

export default function CatalogoEnFilas({ animales, alElegir, alVerEnElegir }: {
  animales: Animal[]; alElegir: (a: Animal) => void; alVerEnElegir: (a: Animal) => void;
}) {
  const [abierto, setAbierto] = useState<number | null>(null);
  const [columnas, setColumnas] = useState(1);
  const lista = useRef<HTMLUListElement>(null);
  const botones = useRef(new Map<number, HTMLButtonElement>());
  const sonido = useRef<Sonido | null>(null);

  // Cuántas columnas pinta la cuadrícula ahora (cambia con el ancho de la ventana).
  useLayoutEffect(() => {
    const medir = () => {
      const plantilla = lista.current ? getComputedStyle(lista.current).gridTemplateColumns : "";
      setColumnas(Math.max(1, plantilla.split(" ").filter(Boolean).length));
    };
    medir();
    window.addEventListener("resize", medir);
    return () => window.removeEventListener("resize", medir);
  }, []);

  const cerrar = (id: number) => { setAbierto(null); botones.current.get(id)?.focus(); };
  const tocar = (a: Animal) => {
    if (abierto === a.animal_id) return cerrar(a.animal_id);
    sonido.current ??= new Sonido({ musica: false, efectos: leerPreferencias().efectos });
    sonido.current.efecto(sonidoDeEspecie(a.especie));
    setAbierto(a.animal_id);
  };

  useEffect(() => {
    if (abierto === null) return;
    const alTeclear = (e: KeyboardEvent) => { if (e.key === "Escape") cerrar(abierto); };
    document.addEventListener("keydown", alTeclear);
    return () => document.removeEventListener("keydown", alTeclear);
  }, [abierto]);

  const i = animales.findIndex((a) => a.animal_id === abierto);
  const fin = i >= 0 ? finDeFila(i, columnas, animales.length) : -1;
  return (
    <ul className="acceso-lista" ref={lista}>
      {animales.map((a, k) => [
        <li key={a.animal_id}>
          <button ref={(b) => { if (b) botones.current.set(a.animal_id, b); }}
            className={`acceso-animal${abierto === a.animal_id ? " acceso-animal--activa" : ""}`}
            aria-expanded={abierto === a.animal_id} aria-controls="detalle-animal" onClick={() => tocar(a)}>
            <FotoAnimal a={a} className="acceso-foto" />
            <span className="h acceso-nombre">{a.nombre}</span>
          </button>
        </li>,
        k === fin && (
          <li key={`detalle-${Math.floor(i / columnas)}`} className="detalle-celda">
            <Detalle animal={animales[i]} alCerrar={() => cerrar(animales[i].animal_id)}
              alElegir={alElegir} alVerEnElegir={alVerEnElegir} />
          </li>)])}
    </ul>
  );
}

function Detalle({ animal, alCerrar, alElegir, alVerEnElegir }: {
  animal: Animal; alCerrar: () => void; alElegir: (a: Animal) => void; alVerEnElegir: (a: Animal) => void;
}) {
  const caja = useRef<HTMLElement>(null);
  // Al abrir (o cambiar de animal): el foco al título y, tras la animación, el panel a la vista.
  useEffect(() => {
    caja.current?.querySelector<HTMLElement>("h2")?.focus({ preventScroll: true });
    const reloj = setTimeout(() => caja.current?.scrollIntoView?.(
      { block: "nearest", behavior: quieto() ? "auto" : "smooth" }), quieto() ? 0 : 320);
    return () => clearTimeout(reloj);
  }, [animal.animal_id]);
  return (
    <section id="detalle-animal" className="detalle" ref={caja} aria-labelledby="detalle-titulo">
      <div className="detalle-dentro">
        <FotoAnimal a={animal} alt={`Foto de ${animal.nombre}`} className="detalle-foto" />
        <div className="detalle-info" key={animal.animal_id}>
          <h2 id="detalle-titulo" className="h detalle-nombre" tabIndex={-1}>{animal.nombre}</h2>
          <p className="detalle-resumen">{resumenCorto(animal)}</p>
          <div className="insignias">
            {insignias(animal).map((t, k) => <span key={t} className={`insignia insignia--${k}`}>{t}</span>)}
          </div>
          {animal.descripcion && <p className="elegir-desc">{animal.descripcion}</p>}
          {estadisticas(animal).length > 0 && (
            <ul className="stats">
              {estadisticas(animal).map((e) => (
                <li key={e.etiqueta} className="stat">
                  <span className="stat-nombre">{e.etiqueta}</span><span className="stat-valor">{e.texto}</span>
                  <Barra valor={e.valor} color={e.color} />
                </li>))}
            </ul>)}
          <HoyYAdulto a={animal} />
          <ul className="convive-iconos" aria-label="Convivencia">
            {convivenciaIconos(animal).map((c) => (
              <li key={c.clave} className={`convive-icono convive-icono--${c.marca}`} title={c.texto}>
                {c.clave === "animales" ? <Huella tam={20} /> : <Icono d={ICONO[c.clave]} tam={20} grosor={2} />}
                <span className="convive-marca" aria-hidden="true"><Icono d={MARCA[c.marca]} tam={11} grosor={3.2} /></span>
                <span className="visualmente-oculto">{c.texto}</span>
              </li>))}
          </ul>
          <div className="detalle-botones">
            <button className="adop-boton" onClick={() => alElegir(animal)}>
              <span className="h">{`¡Te elijo, ${animal.nombre}!`}</span>
              <span className="adop-boton-punta adop-boton-punta--rosa"><Corazon className="late" /></span></button>
            <button className="adop-boton adop-boton--claro" onClick={() => alVerEnElegir(animal)}>
              Ver en Elige a tu compañero</button>
          </div>
        </div>
        <button className="adop-redondo detalle-cerrar" aria-label="Cerrar" onClick={alCerrar}>
          <Icono d="M6 6l12 12M18 6L6 18" /></button>
      </div>
    </section>
  );
}
