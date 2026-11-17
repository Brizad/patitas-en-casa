import { afterEach, describe, expect, it, vi } from "vitest";
import {
  AnalisisVideo, ESTADOS_VIDEO, EstadoNodo, analisisVideo, estadoNodo, haceCuanto, notaDeVista,
  notaDelNodo, sigueAnalizando, urlVista,
} from "./apiVideo";

afterEach(() => vi.unstubAllGlobals());

describe("análisis de video (#125)", () => {
  it("tiene un texto para cada estado de la API", () => {
    expect(Object.keys(ESTADOS_VIDEO)).toEqual(
      ["pendiente", "enviado", "terminado", "no_concluyente", "fallido"]);
  });

  it("un reporte sin video (404) devuelve null y no un error", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(
      JSON.stringify({ detail: "Este reporte no tiene video." }), { status: 404 })));
    expect(await analisisVideo("t", "ABCD1234")).toBeNull();
  });

  it("la vista previa se pide con la sesión y se muestra desde un blob local", async () => {
    const pedido = vi.fn(async () => new Response(new Blob(["mp4"], { type: "video/mp4" })));
    vi.stubGlobal("fetch", pedido);
    vi.stubGlobal("URL", { createObjectURL: () => "blob:vista" });
    expect(await urlVista("t", "ABCD1234")).toBe("blob:vista");
    expect(pedido).toHaveBeenCalledWith("/reportes/ABCD1234/video/vista.mp4",
      { headers: { Authorization: "Bearer t" } });
  });

  it("otros errores sí se muestran", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("{}", { status: 401 })));
    await expect(analisisVideo("t", "ABCD1234")).rejects.toThrow();
  });
});

const BASE: AnalisisVideo = {
  estado: "no_concluyente", prioridad: null, confianza: 0, evidencias: [], medidas: {},
  discrepancia: false, motivo: null, version_modelo: null, tiene_tira: false, tiene_vista: true,
};

describe("vista previa en el panel (#231)", () => {
  it("con vista cargada no hay nada que avisar, también si no es concluyente", () => {
    expect(notaDeVista(BASE, false)).toBeNull();
  });

  it("si la vista existe pero no carga, se dice en vez de quedar en blanco", () => {
    expect(notaDeVista(BASE, true)).toMatch(/No se pudo cargar la vista previa/);
  });

  it("un análisis cerrado sin vista lo dice", () => {
    expect(notaDeVista({ ...BASE, tiene_vista: false }, false)).toMatch(/no trae vista previa/);
    expect(notaDeVista({ ...BASE, estado: "terminado", tiene_vista: false }, false))
      .toMatch(/no trae vista previa/);
  });

  it("mientras se analiza no se avisa nada y el panel vuelve a preguntar", () => {
    expect(notaDeVista({ ...BASE, estado: "enviado", tiene_vista: false }, false)).toBeNull();
    expect(sigueAnalizando("pendiente")).toBe(true);
    expect(sigueAnalizando("enviado")).toBe(true);
    expect(sigueAnalizando("no_concluyente")).toBe(false);
    expect(sigueAnalizando("terminado")).toBe(false);
  });
});

describe("el equipo que analiza los videos, visible en el panel (#231)", () => {
  const NODO: EstadoNodo = {
    activado: true, version_minima: "1.3.0", ultimo_contacto: "2026-11-16T20:00:00+00:00",
    segundos_sin_contacto: 8, version: "1.3.0", analizando: false, en_linea: true, al_dia: true,
  };
  const EN_ESPERA: AnalisisVideo = { ...BASE, estado: "pendiente", tiene_vista: false };

  it("un análisis sin vista dice el motivo que mandó el equipo de análisis", () => {
    const sinFfmpeg = { ...BASE, tiene_vista: false,
      medidas: { sin_vista: "ffmpeg no está instalado (sudo apt install ffmpeg)" } };
    expect(notaDeVista(sinFfmpeg, false)).toMatch(/no trae vista previa: ffmpeg no está instalado/);
  });

  it("un análisis sin vista y sin versión viene de un equipo sin actualizar", () => {
    expect(notaDeVista({ ...BASE, tiene_vista: false }, false)).toMatch(/versión antigua/);
    expect(notaDeVista({ ...BASE, tiene_vista: false, medidas: { version_nodo: "1.3.0" } }, false))
      .not.toMatch(/versión antigua/);
  });

  it("con el equipo encendido y al día no hay nada que avisar", () => {
    expect(notaDelNodo(NODO, EN_ESPERA)).toBeNull();
  });

  it("si el equipo está apagado, el veterinario sabe que el análisis no va a llegar pronto", () => {
    const apagado = { ...NODO, en_linea: false, segundos_sin_contacto: 3700 };
    expect(notaDelNodo(apagado, EN_ESPERA)).toMatch(/apagado.*hace 1 h/);
    expect(notaDelNodo({ ...apagado, ultimo_contacto: null, segundos_sin_contacto: null },
      EN_ESPERA)).toMatch(/apagado/);
  });

  it("si el equipo corre una versión antigua, se pide actualizarlo", () => {
    expect(notaDelNodo({ ...NODO, al_dia: false, version: null }, EN_ESPERA))
      .toMatch(/versión antigua/);
  });

  it("con el análisis ya cerrado el estado del equipo no importa", () => {
    expect(notaDelNodo({ ...NODO, en_linea: false }, BASE)).toBeNull();
    expect(notaDelNodo(null, EN_ESPERA)).toBeNull();
  });

  it("el estado del equipo se pide con la sesión; si falla, no rompe la pantalla", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(NODO))));
    expect((await estadoNodo("t"))?.en_linea).toBe(true);
    vi.stubGlobal("fetch", vi.fn(async () => new Response("{}", { status: 404 })));
    expect(await estadoNodo("t")).toBeNull();  // una API anterior que no conoce la ruta
  });

  it("los ratos se dicen en palabras", () => {
    expect([40, 150, 7300].map(haceCuanto)).toEqual(["hace menos de 1 min", "hace 2 min", "hace 2 h"]);
  });
});
