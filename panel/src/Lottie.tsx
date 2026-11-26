// Animaciones Lottie decorativas del panel (#467). Los JSON viven en /diseno/lottie/ (los mismos
// de la portada y la app) y el reproductor es lottie-web light (sin eval: la CSP no cambia). Se
// cargan solo cuando el contenedor está por verse y se pausan fuera de la pantalla. Siempre
// aria-hidden: son decoración. Con «reducir movimiento» (del sistema o el botón «Movimiento» del
// adoptante, .adop--quieto) se muestra el dibujo de siempre o un cuadro quieto.
import { ReactNode, useEffect, useRef, useState } from "react";
import "./lottie.css";

export type ModoQuieto = "respaldo" | "cuadro";
export type Estado = "respaldo" | "animar" | "cuadro";

/** Qué mostrar. Puro, para probarlo sin navegador. */
export function decidir(reducido: boolean, quieto: ModoQuieto): Estado {
  if (!reducido) return "animar";
  return quieto === "cuadro" ? "cuadro" : "respaldo";
}

type Animacion = { play(): void; pause(): void; destroy(): void; goToAndStop(v: number, f?: boolean): void;
  totalFrames: number };

const cache = new Map<string, Promise<unknown>>();
function datos(nombre: string): Promise<unknown> {
  if (!cache.has(nombre)) {
    cache.set(nombre, fetch(`/diseno/lottie/${encodeURIComponent(nombre)}.json`)
      .then((r) => { if (!r.ok) throw new Error(String(r.status)); return r.json(); }));
  }
  return cache.get(nombre)!;
}

const reducidoDelSistema = () =>
  typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true;

export default function Lottie({ nombre, className = "", respaldo = null, quieto = "respaldo", cuadro = 0.5 }: {
  nombre: string; className?: string; respaldo?: ReactNode;
  /** Con movimiento reducido: el respaldo (dibujo de siempre) o un cuadro quieto de la animación. */
  quieto?: ModoQuieto;
  /** En qué parte (0 a 1) se detiene el cuadro quieto. */
  cuadro?: number;
}) {
  const caja = useRef<HTMLSpanElement>(null);
  const lienzo = useRef<HTMLSpanElement>(null);
  const [lista, setLista] = useState(false);

  useEffect(() => {
    const el = caja.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    const estado = decidir(reducidoDelSistema() || !!el.closest(".adop--quieto"), quieto);
    if (estado === "respaldo") return;
    let anim: Animacion | null = null;
    let cancelado = false;
    const vigia = new IntersectionObserver(async ([entrada]) => {
      if (!entrada.isIntersecting) { anim?.pause(); return; }
      if (anim) { if (estado === "animar") anim.play(); return; }
      try {
        const [{ default: lottie }, animacion] = await Promise.all([
          import("lottie-web/build/player/lottie_light"), datos(nombre)]);
        if (cancelado || !lienzo.current || anim) return;
        anim = lottie.loadAnimation({
          container: lienzo.current, renderer: "svg", loop: true, autoplay: estado === "animar",
          animationData: structuredClone(animacion), rendererSettings: { preserveAspectRatio: "xMidYMid meet" },
        }) as unknown as Animacion;
        if (estado === "cuadro") anim.goToAndStop(Math.floor(anim.totalFrames * cuadro), true);
        setLista(true);
      } catch { /* sin animación: se queda el respaldo */ }
    }, { rootMargin: "120px" });
    vigia.observe(el);
    // El botón «Movimiento» del adoptante puede cambiar con la vista abierta: se pausa y vuelve.
    const adop = el.closest(".adop");
    const alCambiarMovimiento = new MutationObserver(() => {
      if (!anim || estado !== "animar") return;
      if (adop?.classList.contains("adop--quieto")) anim.pause(); else anim.play();
    });
    if (adop) alCambiarMovimiento.observe(adop, { attributes: true, attributeFilter: ["class"] });
    return () => { cancelado = true; vigia.disconnect(); alCambiarMovimiento.disconnect(); anim?.destroy(); };
  }, [nombre, quieto, cuadro]);

  return (
    <span ref={caja} className={`lottie ${lista ? "lottie-activa" : ""} ${className}`} aria-hidden="true">
      {respaldo && <span className="lottie-respaldo">{respaldo}</span>}
      <span ref={lienzo} className="lottie-lienzo" />
    </span>
  );
}
