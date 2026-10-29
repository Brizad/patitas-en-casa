import { afterEach, describe, expect, it, vi } from "vitest";
import { ESTADOS_VIDEO, analisisVideo } from "./apiVideo";

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

  it("otros errores sí se muestran", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("{}", { status: 401 })));
    await expect(analisisVideo("t", "ABCD1234")).rejects.toThrow();
  });
});
