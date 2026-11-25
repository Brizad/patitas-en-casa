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
    // #420: el puntaje del servidor se ve con su barra; el estado de la solicitud, como insignia.
    expect(pantallas["./AdoptantePantallas.tsx"]).toContain("{a.puntaje}%");
    expect(pantallas["./AdoptantePantallas.tsx"]).toContain("estado estado--${s.estado}");
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

describe("adoptante «Elige a tu compañero» (#306, #420)", () => {
  const vista = pantallas["./AdoptantePantallas.tsx"] as string;
  it("un animal sin foto (o con la foto rota) se ve como ilustración con su inicial", () => {
    expect(pantallas["./Ilustraciones.tsx"]).toContain("onError={() => setFallo(true)}");
    expect(pantallas["./Ilustraciones.tsx"]).toContain("nombre.charAt(0).toUpperCase()");
    expect(vista).not.toMatch(/<img /);
  });
  it("las alertas y restricciones del servidor se muestran tal cual", () => {
    expect(vista).toContain("a.alertas.join(");
    expect(vista).toContain("animal.alertas.join(");
    expect(vista).toContain("animal.restricciones.join(");
  });
  it("las estadísticas no inventan datos (sin cariño ni juego)", () => {
    expect(vista).toContain("estadisticas(animal)");
    expect(vista.toLowerCase()).not.toMatch(/cariño|«juego»/);
  });
  it("los botones de solo ícono llevan nombre para el lector de pantalla", () => {
    for (const nombre of ['aria-label="Atrás"', 'aria-label="Anterior"', 'aria-label="Siguiente"',
      "aria-label={`Ver a ${a.nombre}`}"]) {
      expect(vista, nombre).toContain(nombre);
    }
    for (const nombre of ['aria-label="Música"', 'aria-label="Sonidos al tocar"', 'aria-label="Movimiento"']) {
      expect(pantallas["./Adoptante.tsx"], nombre).toContain(nombre);
    }
  });
});

describe("administrador y modo piloto (#307)", () => {
  it("las cifras del piloto van en tarjetas y cada meta muestra cumple / no cumple como insignia", () => {
    expect(pantallas["./Piloto.tsx"]).toContain('className="kpis"');
    expect(pantallas["./Piloto.tsx"]).toContain("ds-insignia--${resumen.cumpleTiempo");
    expect(pantallas["./Piloto.tsx"]).toContain("ds-insignia--${resumen.cumpleSus");
  });
});

describe("cargas y estados vacíos (#400)", () => {
  it("cada lista que pide datos dice que está cargando", () => {
    for (const que of ["la cola", "el historial", "tus rescates", "la ocupación",
      "los indicadores"]) {
      expect(fuentes, que).toContain(`<Cargando que="${que}" />`);
    }
  });
  it("los vacíos principales dicen qué falta y qué hacer", () => {
    for (const vacio of ["No hay reportes por confirmar.", "Aún no has confirmado ni descartado",
      "Aún no has aceptado rescates.", "No hay ofertas ahora.", "Aún no has hecho solicitudes.",
      "No hay adopciones aprobadas.", "No hay seguimientos programados."]) {
      expect(fuentes, vacio).toContain(`<strong>${vacio}`);
    }
  });
});

describe("textos para personas, no para el documento de requisitos (#400)", () => {
  it("ningún texto visible lleva códigos como (RF-31), (RNF-06) o «pantalla P-06»", () => {
    const sinComentarios = fuentes.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
    expect(sinComentarios).not.toMatch(/\((?:RF|RNF|RN)-\d+|RN-\d+\)|pantalla P-\d+/);
  });
  it("en el celular la cola no deja la tarjeta «Elige un reporte» al final", () => {
    expect(fuentes).toContain('" detalle--vacio"');
  });
  it("una barra en 0 no se dibuja (antes quedaba una rayita)", () => {
    expect(fuentes).toContain("{v > 0 && <span");
  });
});
