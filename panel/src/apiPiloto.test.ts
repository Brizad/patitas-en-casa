import { afterEach, describe, expect, it, vi } from "vitest";
import { csvPiloto, resumenPiloto } from "./apiPiloto";

afterEach(() => vi.unstubAllGlobals());

describe("resumen del piloto (RNF-06, #258)", () => {
  it("sin participantes no hay resumen", () => {
    expect(resumenPiloto([])).toBeNull();
  });

  it("usa las metas del ERS: 80 % en 90 s o menos y SUS de 70", () => {
    const filas = [
      { participante: "P01", segundos: 90, sus: 85 },
      { participante: "P02", segundos: 62, sus: 70 },
      { participante: "P03", segundos: 91, sus: 40 },
      { participante: "P04", segundos: 30, sus: 75 },
      { participante: "P05", segundos: 45, sus: 80 },
    ];
    expect(resumenPiloto(filas)).toEqual(
      { cumplen: 4, porcentaje: 80, sus: 70, cumpleTiempo: true, cumpleSus: true });
    expect(resumenPiloto(filas.slice(2, 3))).toMatchObject({ cumpleTiempo: false, cumpleSus: false });
  });

  it("el CSV se pide con la sesión", async () => {
    const pedido = vi.fn(async () => new Response("participante,segundos\n"));
    vi.stubGlobal("fetch", pedido);
    expect(await (await csvPiloto("t")).text()).toContain("participante");
    expect(pedido).toHaveBeenCalledWith("/admin/piloto/resultados.csv",
      { headers: { Authorization: "Bearer t" } });
  });
});
