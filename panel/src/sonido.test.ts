import { afterEach, describe, expect, it, vi } from "vitest";
import {
  BAJO, Efecto, MELODIA, PREFERENCIAS_POR_DEFECTO, Sonido, guardarPreferencias, leerPreferencias,
  mtof, receta, sonidoDeEspecie, tonosDelPaso,
} from "./sonido";

describe("recetas de los efectos", () => {
  const efectos: Efecto[] = ["pop", "siguiente", "atras", "pasar", "elegir", "guau", "miau",
    "fanfarria"];
  it("cada efecto tiene notas audibles, cortas y a volumen moderado", () => {
    for (const e of efectos) {
      const tonos = receta(e);
      expect(tonos.length, e).toBeGreaterThan(0);
      for (const n of tonos) {
        expect(n.f, e).toBeGreaterThan(100);
        expect(n.d, e).toBeLessThanOrEqual(0.5);
        expect(n.vol, e).toBeLessThanOrEqual(0.3);
      }
    }
  });
  it("el guau son dos ladridos que bajan y el miau sube y baja", () => {
    const guau = receta("guau");
    expect(guau).toHaveLength(2);
    expect(guau[1].t).toBeGreaterThan(guau[0].t);
    expect(guau[0].fFin!).toBeLessThan(guau[0].f);
    const [miau] = receta("miau");
    expect(miau.fA!).toBeGreaterThan(miau.f);
    expect(miau.fFin!).toBeLessThan(miau.fA!);
  });
  it("la fanfarria es un arpegio que avanza en el tiempo", () => {
    const t = receta("fanfarria").map((n) => n.t);
    expect(t).toEqual([...t].sort((a, b) => a - b));
    expect(t.length).toBe(7);
  });
  it("perros ladran y gatos maúllan", () => {
    expect(sonidoDeEspecie("perro")).toBe("guau");
    expect(sonidoDeEspecie("gato")).toBe("miau");
  });
});

describe("música", () => {
  it("convierte notas MIDI a hercios", () => {
    expect(mtof(69)).toBe(440);
    expect(mtof(81)).toBeCloseTo(880);
    expect(mtof(60)).toBeCloseTo(261.63, 1);
  });
  it("la melodía da la vuelta cada 32 pasos y el bajo suena cada 4", () => {
    expect(MELODIA).toHaveLength(32);
    expect(BAJO).toHaveLength(8);
    expect(tonosDelPaso(32)).toEqual(tonosDelPaso(0));
    expect(tonosDelPaso(0).some((n) => n.d === 0.5)).toBe(true); // bajo
    expect(tonosDelPaso(1).some((n) => n.d === 0.5)).toBe(false);
  });
  it("los silencios de la melodía no suenan", () => {
    expect(MELODIA[7]).toBe(0);
    expect(tonosDelPaso(7).every((n) => n.tipo !== "triangle")).toBe(true);
  });
});

describe("preferencias", () => {
  const memoria = () => {
    const datos = new Map<string, string>();
    return { getItem: (k: string) => datos.get(k) ?? null,
             setItem: (k: string, v: string) => void datos.set(k, v) };
  };
  it("sin nada guardado: música, efectos y movimiento prendidos", () => {
    expect(leerPreferencias(memoria())).toEqual(PREFERENCIAS_POR_DEFECTO);
    expect(leerPreferencias(null)).toEqual(PREFERENCIAS_POR_DEFECTO);
  });
  it("recuerda lo que eligió la persona", () => {
    const almacen = memoria();
    guardarPreferencias({ musica: false, efectos: true, movimiento: false }, almacen);
    expect(leerPreferencias(almacen)).toEqual({ musica: false, efectos: true, movimiento: false });
  });
  it("si lo guardado está dañado o el navegador lo bloquea, no se rompe", () => {
    const danado = { getItem: () => "{no es json", setItem: () => {} };
    expect(leerPreferencias(danado)).toEqual(PREFERENCIAS_POR_DEFECTO);
    const bloqueado = { getItem: () => { throw new Error("bloqueado"); },
                        setItem: () => { throw new Error("bloqueado"); } };
    expect(leerPreferencias(bloqueado)).toEqual(PREFERENCIAS_POR_DEFECTO);
    expect(() => guardarPreferencias(PREFERENCIAS_POR_DEFECTO, bloqueado)).not.toThrow();
    expect(leerPreferencias({ getItem: () => '{"musica":"sí"}', setItem: () => {} }).musica)
      .toBe(true);
  });
});

/** Un AudioContext de mentira que cuenta cuántas notas se programan. */
function contextoFalso() {
  const param = () => ({ value: 0, setValueAtTime: vi.fn(), exponentialRampToValueAtTime: vi.fn(),
                         setTargetAtTime: vi.fn() });
  const ctx = {
    currentTime: 0, state: "running", destination: {}, notas: 0,
    resume: vi.fn(), close: vi.fn(),
    createGain: () => ({ gain: param(), connect: vi.fn() }),
    createOscillator: () => {
      ctx.notas++;
      return { type: "sine", frequency: param(), connect: vi.fn(), start: vi.fn(), stop: vi.fn() };
    },
  };
  return ctx;
}

describe("Sonido", () => {
  afterEach(() => vi.useRealTimers());

  it("los efectos suenan solo si están prendidos", () => {
    const ctx = contextoFalso();
    const s = new Sonido({ musica: false, efectos: false }, () => ctx as unknown as AudioContext);
    s.efecto("pop");
    expect(ctx.notas).toBe(0);
    s.efectos = true;
    s.efecto("fanfarria");
    expect(ctx.notas).toBe(7);
  });

  it("la música no arranca sola: espera el primer toque y se detiene al salir", () => {
    vi.useFakeTimers();
    const ctx = contextoFalso();
    const s = new Sonido({ musica: true, efectos: true }, () => ctx as unknown as AudioContext);
    vi.advanceTimersByTime(500);
    expect(s.sonando).toBe(false);
    expect(ctx.notas).toBe(0);
    s.despertar();
    expect(s.sonando).toBe(true);
    vi.advanceTimersByTime(100);
    expect(ctx.notas).toBeGreaterThan(0);
    s.detenerMusica();
    expect(s.sonando).toBe(false);
    const antes = ctx.notas;
    vi.advanceTimersByTime(500);
    expect(ctx.notas).toBe(antes);
    s.reanudar();
    expect(s.sonando).toBe(true);
    s.cerrar();
    expect(s.sonando).toBe(false);
    expect(ctx.close).toHaveBeenCalled();
  });

  it("con la música apagada, despertar no la prende y reanudar tampoco", () => {
    const ctx = contextoFalso();
    const s = new Sonido({ musica: false, efectos: true }, () => ctx as unknown as AudioContext);
    s.despertar();
    s.reanudar();
    expect(s.sonando).toBe(false);
    s.cambiarMusica(true);
    expect(s.sonando).toBe(true);
    s.cambiarMusica(false);
    expect(s.sonando).toBe(false);
  });

  it("sin Web Audio en el navegador no falla", () => {
    const s = new Sonido({ musica: true, efectos: true }, () => null);
    expect(() => { s.despertar(); s.efecto("guau"); s.cerrar(); }).not.toThrow();
    expect(s.sonando).toBe(false);
  });
});
