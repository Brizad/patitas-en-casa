import { afterEach, describe, expect, it, vi } from "vitest";
import {
  AnalisisVideo, ESTADOS_VIDEO, analisisVideo, notaDeVista, sigueAnalizando, urlVista,
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
