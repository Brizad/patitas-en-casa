// Piezas dibujadas de la adopción (#420): foto del animal (o una ilustración con su inicial si no
// tiene o no carga: nunca una imagen rota), íconos, huellas y confeti. Solo SVG y CSS.
import { useEffect, useState } from "react";
import type { AnimalPublicado } from "./apiAdopcion";
import { fondoDe } from "./flujoAdopcion";

export function Icono({ d, tam = 20, grosor = 2.4 }: { d: string; tam?: number; grosor?: number }) {
  return (
    <svg width={tam} height={tam} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth={grosor} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={d} />
    </svg>
  );
}

export const FLECHA = { izq: "M15 6l-6 6 6 6", der: "M9 6l6 6-6 6", adelante: "M5 12h14M13 6l6 6-6 6" };

export function Huella({ tam = 24, color = "currentColor", className }: {
  tam?: number; color?: string; className?: string;
}) {
  return (
    <svg className={className} width={tam} height={tam} viewBox="0 0 24 24" fill={color} aria-hidden="true">
      <ellipse cx="12" cy="15.5" rx="5" ry="4.2" /><circle cx="6" cy="9.5" r="2.2" />
      <circle cx="10" cy="6" r="2.2" /><circle cx="14" cy="6" r="2.2" /><circle cx="18" cy="9.5" r="2.2" />
    </svg>
  );
}

export function Corazon({ tam = 20, className }: { tam?: number; className?: string }) {
  return (
    <svg className={className} width={tam} height={tam} viewBox="0 0 24 24" fill="#E8508A" aria-hidden="true">
      <path d="M12 21s-7.5-4.6-9.6-9.2C.9 8.4 3 4.5 6.8 4.5c2.1 0 3.6 1.2 5.2 3 1.6-1.8 3.1-3 5.2-3 3.8 0 5.9 3.9 4.4 7.3C19.5 16.4 12 21 12 21z" />
    </svg>
  );
}

/** Carita amable de perro o gato con la inicial del nombre, para quien aún no tiene foto. */
export function Silueta({ nombre, especie, alt }: { nombre: string; especie: string; alt: string }) {
  const gato = especie === "gato";
  const etiqueta = alt ? { role: "img", "aria-label": alt } : { "aria-hidden": true };
  return (
    <svg className="silueta" viewBox="0 0 100 100" {...etiqueta}>
      {gato
        ? <path d="M27 44 L30 13 L50 30 Z M73 44 L70 13 L50 30 Z" fill="#A4A7B8" stroke="#2B2340"
            strokeWidth="2.5" strokeLinejoin="round" />
        : <g fill="#C98A4B" stroke="#2B2340" strokeWidth="2.5">
            <ellipse cx="26" cy="44" rx="10" ry="19" transform="rotate(22 26 44)" />
            <ellipse cx="74" cy="44" rx="10" ry="19" transform="rotate(-22 74 44)" />
          </g>}
      <circle cx="50" cy="53" r="27" fill="#FFFFFF" stroke="#2B2340" strokeWidth="2.5" />
      <circle cx="40" cy="49" r="3.6" fill="#2B2340" /><circle cx="60" cy="49" r="3.6" fill="#2B2340" />
      <ellipse cx="50" cy="59" rx="5" ry="3.6" fill="#2B2340" />
      <path d="M44 65 q6 5 12 0" stroke="#2B2340" strokeWidth="2.2" fill="none" strokeLinecap="round" />
      <circle cx="79" cy="80" r="14" fill="#2B2340" />
      <text x="79" y="85.6" textAnchor="middle" fontSize="16" fontWeight="700" fill="#FFFFFF"
        className="h">{nombre.charAt(0).toUpperCase()}</text>
    </svg>
  );
}

/** La foto del catálogo; si no hay o falla al cargar, la ilustración. alt vacío = decorativa. */
export function FotoAnimal({ a, alt = "", className = "" }: {
  a: AnimalPublicado; alt?: string; className?: string;
}) {
  const [fallo, setFallo] = useState(false);
  useEffect(() => setFallo(false), [a.foto]);
  return (
    <span className={`foto-animal ${className}`} style={{ backgroundColor: fondoDe(a.animal_id) }}>
      {a.foto && !fallo
        ? <img src={a.foto} alt={alt} loading="lazy" onError={() => setFallo(true)} />
        : <Silueta nombre={a.nombre} especie={a.especie} alt={alt && `${alt}, aún sin foto`} />}
    </span>
  );
}

const COLORES_CONFETI = ["#E8508A", "#F2A93B", "#7A5AF8", "#3FA66B", "#FFE9A6", "#9B83FA", "#FBD9E3"];

/** Confeti que cae (solo con movimiento); posiciones fijas para que la captura sea estable. */
export function Confeti() {
  return (
    <div className="confeti" aria-hidden="true">
      {Array.from({ length: 26 }, (_, c) => (
        <i key={c} style={{
          left: `${(c * 37) % 100}%`, width: 8 + (c % 3) * 3, height: 12 + (c % 4) * 3,
          background: COLORES_CONFETI[c % COLORES_CONFETI.length],
          borderRadius: c % 3 === 0 ? 999 : 3, animationDelay: `${((c * 0.29) % 3).toFixed(2)}s`,
          animationDuration: `${(2.6 + (c % 5) * 0.35).toFixed(2)}s` }} />))}
    </div>
  );
}
