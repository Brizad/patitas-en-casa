// #170: el panel usa el sistema de diseño compartido y no las clases sueltas de antes.
import { describe, expect, it } from "vitest";
import html from "../index.html?raw";

const pantallas = import.meta.glob("./*.tsx", { query: "?raw", import: "default", eager: true });
const fuentes = Object.values(pantallas).join("\n");

describe("sistema de diseño en el panel", () => {
  it("carga la hoja compartida y marca el cuerpo", () => {
    expect(html).toContain('href="/diseno/sistema.css"');
    expect(html).toMatch(/<body class="ds"/);
  });

  it("las pantallas usan las piezas del sistema (ds-tarjeta, ds-msg, ds-vacio, ds-insignia)", () => {
    expect(fuentes).toContain("ds-tarjeta");
    expect(fuentes).toContain("ds-msg ds-msg--error");
    expect(fuentes).toContain("ds-vacio");
    expect(fuentes).toMatch(/ds-insignia ds-insignia--\$\{/);
    for (const viejo of ['className="tarjeta"', 'className="error"', 'className="vacio"',
      'className="tabla"', "`chip "]) {
      expect(fuentes, viejo).not.toContain(viejo);
    }
  });
});

describe("pantallas del coordinador (#174)", () => {
  it("cada lista vacía explica qué falta en lugar de quedar en blanco", () => {
    for (const texto of ["No hay solicitudes pendientes.", "No hay adopciones aprobadas.",
      "No hay seguimientos programados.", "No hay animales en el refugio."]) {
      expect(fuentes, texto).toContain(texto);
    }
  });
  it("los formularios largos usan la rejilla del sistema", () => {
    expect(fuentes).toContain("ds-tarjeta ds-form");
  });
});
