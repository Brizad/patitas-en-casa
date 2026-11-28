import { describe, expect, it } from "vitest";
import {
  colorEspera, distanciaMetros, esDeHoy, ordenarPorCercania, textoDistancia, textoEspecie, textoZona,
} from "./bandejas";
import { haceCuanto } from "./mensajes";

const AHORA = Date.parse("2026-11-27T20:00:00Z");
const hace = (horas: number) => new Date(AHORA - horas * 3_600_000).toISOString();

describe("bandejas (#496)", () => {
  it("espera: verde < 1 h, amarillo de 1 a 6 h, rojo > 6 h", () => {
    expect(colorEspera(hace(0.5), AHORA)).toBe("verde");
    expect(colorEspera(hace(3), AHORA)).toBe("amarillo");
    expect(colorEspera(hace(7), AHORA)).toBe("rojo");
  });

  it("tiempo relativo en minutos, horas y días", () => {
    expect(haceCuanto(hace(0.2), AHORA)).toBe("hace 12 min");
    expect(haceCuanto(hace(3), AHORA)).toBe("hace 3 h");
    expect(haceCuanto(hace(24 * 25), AHORA)).toBe("hace 25 días");
    expect(haceCuanto(hace(30), AHORA)).toBe("hace 1 día");
  });

  it("distancia con haversine, redondeada y «—» sin ubicación", () => {
    const cucuta = { latitud: 7.8939, longitud: -72.5078 };
    const m = distanciaMetros(cucuta, { latitud: 7.9155, longitud: -72.5078 });
    expect(Math.round(m / 100)).toBe(24); // 0,0216° de latitud ≈ 2,4 km
    expect(textoDistancia(m)).toBe("2,4 km");
    expect(textoDistancia(847)).toBe("850 m");
    expect(textoDistancia(null)).toBe("—");
  });

  it("sin dato del reporte, «—»", () => {
    expect(textoEspecie(null)).toBe("—");
    expect(textoEspecie("perro")).toBe("Perro");
    expect(textoZona(null)).toBe("—");
    expect(textoZona(5)).toBe("Comuna 5");
  });

  it("con ubicación ordena por nivel y luego cercanía; sin ella deja el orden del servidor", () => {
    const yo = { latitud: 7.89, longitud: -72.5 };
    const lejos = { codigo: "A", nivel: "urgente" as const, latitud: 7.95, longitud: -72.5 };
    const cerca = { codigo: "B", nivel: "urgente" as const, latitud: 7.891, longitud: -72.5 };
    const alta = { codigo: "C", nivel: "alta" as const, latitud: 7.89, longitud: -72.5 };
    expect(ordenarPorCercania([lejos, alta, cerca], yo).map((c) => c.codigo)).toEqual(["B", "A", "C"]);
    expect(ordenarPorCercania([lejos, alta, cerca], null).map((c) => c.codigo)).toEqual(["A", "C", "B"]);
  });

  it("«hoy» es el día de Colombia, no el de UTC", () => {
    // 27 nov 23:00 en Bogotá = 28 nov 04:00 UTC: sigue siendo «hoy» para quien está en Bogotá.
    expect(esDeHoy("2026-11-28T04:00:00Z", Date.parse("2026-11-27T22:00:00Z"))).toBe(true);
    expect(esDeHoy("2026-11-27T04:00:00Z", Date.parse("2026-11-27T22:00:00Z"))).toBe(false);
  });
});

describe("ubicación del rescatista en camino (#498)", async () => {
  const { esCuentaDemo, tocaEnviar, INTERVALO_UBICACION_MS } = await import("./apiRescatista");
  it("se envía una posición cada 12 s, no cada lectura del GPS", () => {
    expect(INTERVALO_UBICACION_MS).toBe(12_000);
    expect(tocaEnviar(null, 1000)).toBe(true);
    expect(tocaEnviar(1000, 1000 + 11_999)).toBe(false);
    expect(tocaEnviar(1000, 1000 + 12_000)).toBe(true);
  });
  it("«Simular recorrido» solo para las cuentas de demostración", () => {
    expect(esCuentaDemo("rescatista@demo.patitas.co")).toBe(true);
    expect(esCuentaDemo("ana@rescate.co")).toBe(false);
    expect(esCuentaDemo("demo.patitas.co@otro.co")).toBe(false);
  });
});

describe("informe de rescate (#504)", async () => {
  const { faltaEnInforme } = await import("./apiRescatista");
  const { medidaReducida } = await import("./fotos");
  const base = { encontrado: "si" as const, estados: [], accion: "trasladado" as const, motivo: "", nota: "" };
  it("las fotos se reducen a 1280 px sin agrandarse", () => {
    expect(medidaReducida(4000, 3000)).toEqual([1280, 960]);
    expect(medidaReducida(800, 600)).toEqual([800, 600]);
  });
  it("las mismas reglas que el servidor", () => {
    expect(faltaEnInforme(base, 1)).toBeNull();
    expect(faltaEnInforme(base, 0)).toBe("Adjunta al menos una foto de evidencia.");
    expect(faltaEnInforme({ ...base, encontrado: "no_estaba", accion: null }, 0)).toBeNull();
    expect(faltaEnInforme({ ...base, accion: null }, 1)).toBe("Elige qué se hizo con el animal.");
    expect(faltaEnInforme({ ...base, accion: "no_rescatado" }, 1)).toMatch(/por qué no se pudo/);
    expect(faltaEnInforme({ ...base, accion: "no_rescatado", motivo: "Se escapó al caño" }, 1)).toBeNull();
    expect(faltaEnInforme({ ...base, nota: "x".repeat(501) }, 1)).toMatch(/500/);
  });
});
