import { describe, expect, it } from "vitest";
import { pantallasDelRol } from "./navegacion";
import { nombreComunas, NOMBRE_RESULTADO } from "./apiRescatista";

describe("pantallasDelRol", () => {
  it("cada rol empieza en su pantalla principal", () => {
    expect(pantallasDelRol("veterinario")[0]).toBe("cola");
    expect(pantallasDelRol("coordinador")[0]).toBe("refugio");
    expect(pantallasDelRol("rescatista")).toEqual(["rescates", "mis_rescates"]);
    expect(pantallasDelRol("administrador")).toEqual(["administracion", "indicadores"]);
    expect(pantallasDelRol("adoptante")).toEqual(["adopcion"]);
    expect(pantallasDelRol("alcaldia")).toEqual(["indicadores"]);
  });
  it("el veterinario tiene la pestaña Historial y el coordinador no", () => {
    expect(pantallasDelRol("veterinario")).toEqual(["cola", "historial", "refugio"]);
    expect(pantallasDelRol("coordinador")).not.toContain("historial");
  });
  it("un rol desconocido no ve ninguna pantalla", () => {
    expect(pantallasDelRol("ciudadano")).toEqual([]);
  });
});

describe("textos del rescatista", () => {
  it("zona vacía es toda la ciudad (#46)", () => {
    expect(nombreComunas([])).toBe("Toda la ciudad");
    expect(nombreComunas([6, 2])).toBe("Comunas 2, 6");
  });
  it("cada resultado del rescate tiene un nombre legible", () => {
    expect(Object.keys(NOMBRE_RESULTADO)).toEqual(
      ["trasladado", "atendido_en_sitio", "no_encontrado", "fallecido"]);
  });
});
