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

describe("indicadores legibles (#176)", () => {
  it("muestra cifras clave en tarjetas y no claves técnicas", () => {
    expect(fuentes).toContain("kpi");
    expect(fuentes).toContain("nombreIndicador(");
  });
});

describe("administrador y adoptante (#178)", () => {
  it("el estado de cuentas y solicitudes se ve como insignia", () => {
    expect(fuentes).toContain("ds-insignia ds-insignia--baja\">Activa");
    expect(fuentes).toContain("Compatibilidad");
    expect(fuentes).toMatch(/ds-insignia[^"]*">\{a\.puntaje\}/);
  });
});

describe("detalle del reporte para el veterinario (#180)", () => {
  it("muestra qué pasó, dónde y cuándo, y explica la sugerencia en lenguaje sencillo", () => {
    for (const pieza of ["detalle.descripcion", "Abrir en Google Maps", "haceCuanto(",
      "explicarSugerencia(", "evidenciaLegible(", "nombreModelo("]) {
      expect(fuentes, pieza).toContain(pieza);
    }
    expect(fuentes).not.toContain("Sugerida por {detalle.version_modelo}");
  });
  it("no pide el análisis de video si el reporte no trae video", () => {
    expect(fuentes).toContain("detalle.video_segundos !== null");
  });
});

describe("sin textos técnicos a la vista (#182)", () => {
  it("el acuerdo por versión del modelo se nombra por lo que hace", () => {
    expect(fuentes).toContain("nombreModelo(v)");
  });
});

describe("estructura del panel con el sistema visual nuevo (#300)", () => {
  it("carga las fuentes locales antes de la hoja compartida", () => {
    expect(html).toContain('href="/diseno/fuentes.css"');
    expect(html.indexOf("/diseno/fuentes.css")).toBeLessThan(html.indexOf("/diseno/sistema.css"));
  });

  it("toda tabla del panel se vuelve tarjetas en el celular, con la etiqueta de cada dato", () => {
    for (const [archivo, codigo] of Object.entries(pantallas)) {
      const tablas = (codigo as string).match(/<table className="[^"]*"/g) ?? [];
      for (const tabla of tablas) expect(tabla, archivo).toContain("ds-tabla--tarjetas");
      if (tablas.length) expect(codigo as string, archivo).toContain("data-etiqueta=");
    }
  });
});

describe("panel del veterinario (#302)", () => {
  it("cada fila de la cola lleva su prioridad como clase (barra de distinto grosor, no solo color)", () => {
    expect(pantallas["./Cola.tsx"]).toContain("item--${r.prioridad}");
  });
  it("descartar se ve como acción de peligro, separada de confirmar", () => {
    expect(pantallas["./Descartar.tsx"]).toContain('className="ds-btn--peligro"');
  });
});

describe("panel del rescatista (#303)", () => {
  it("ofertas y rescate en curso llevan la prioridad como clase (barra de distinto grosor)", () => {
    expect(pantallas["./Rescatista.tsx"]).toContain("oferta--${o.prioridad}");
    expect(pantallas["./Rescatista.tsx"]).toContain("oferta--${rescate.prioridad}");
  });
});

describe("adoptante (#306)", () => {
  it("el catálogo es una rejilla de tarjetas y el nombre de cada animal es un encabezado", () => {
    expect(pantallas["./Adoptante.tsx"]).toContain('className="catalogo"');
    expect(pantallas["./Adoptante.tsx"]).toContain("<h3>{a.nombre}</h3>");
  });
});

describe("administrador y modo piloto (#307)", () => {
  it("las cifras del piloto van en tarjetas y cada meta muestra cumple / no cumple como insignia", () => {
    expect(pantallas["./Piloto.tsx"]).toContain('className="kpis"');
    expect(pantallas["./Piloto.tsx"]).toContain("ds-insignia--${resumen.cumpleTiempo");
    expect(pantallas["./Piloto.tsx"]).toContain("ds-insignia--${resumen.cumpleSus");
  });
});
