import { describe, expect, it } from "vitest";
import { vistaDesdeHash } from "./AccesoAdoptante";
import { ErrorApi } from "./api";
import { esOtroPortal, textoError } from "./mensajes";

const pantallas = import.meta.glob("./*.tsx", { query: "?raw", import: "default", eager: true });

describe("entrada del adoptante (arreglos, parte B)", () => {
  it("#adoptar abre la pantalla amable con sus 3 caminos; los enlaces de antes siguen sirviendo", () => {
    expect(vistaDesdeHash("#adoptar")).toBe("inicio");
    expect(vistaDesdeHash("#adoptar/entrar")).toBe("entrar");
    expect(vistaDesdeHash("#adoptar/crear")).toBe("crear");
    expect(vistaDesdeHash("#adoptar/animales")).toBe("animales");
    expect(vistaDesdeHash("#registro")).toBe("crear");
  });

  it("el personal entra por su propia pantalla (sin hash o #personal)", () => {
    expect(vistaDesdeHash("")).toBeNull();
    expect(vistaDesdeHash("#personal")).toBeNull();
  });

  it("la entrada del adoptante nunca se llama «personal» y la del personal se nombra como tal", () => {
    const acceso = pantallas["./AccesoAdoptante.tsx"] as string;
    expect(acceso).toContain("Entrar como adoptante");
    expect(acceso).toContain("Ya tengo cuenta");
    expect(acceso).toContain("Soy nuevo");
    expect(acceso).toContain("Ver los animales sin cuenta");
    expect(acceso).not.toMatch(/Panel del personal|Entrar como personal/);
    expect(pantallas["./App.tsx"]).toContain("Entrar como personal del refugio");
  });

  it("al crear la cuenta entra directo (inicia sesión con lo que escribió)", () => {
    const acceso = pantallas["./AccesoAdoptante.tsx"] as string;
    const crear = acceso.slice(acceso.indexOf("function Crear("));
    expect(crear.indexOf("registrarAdoptante(")).toBeLessThan(crear.indexOf("iniciarSesion("));
    expect(crear).toContain("alEntrar(token, await miCuenta(token))");
  });
});

describe("cada puerta deja entrar solo a su rol (#486)", () => {
  it("la entrada del adoptante pide portal adoptante y la del personal, portal personal", () => {
    const acceso = pantallas["./AccesoAdoptante.tsx"] as string;
    const app = pantallas["./App.tsx"] as string;
    expect(acceso.match(/iniciarSesion\(correo\.trim\(\), clave[^)]*\)/g)).toEqual([
      'iniciarSesion(correo.trim(), clave, "adoptante")', 'iniciarSesion(correo.trim(), clave, "adoptante")']);
    expect(app).toContain('iniciarSesion(correo.trim(), clave, "personal")');
  });

  it("con la cuenta en la puerta equivocada, enlaza a la correcta", () => {
    expect(pantallas["./AccesoAdoptante.tsx"]).toContain("Ir a «¿Trabajas en el refugio?»");
    expect(pantallas["./App.tsx"]).toContain("Ir a «Adoptar»");
  });

  it("solo el 403 del inicio de sesión es «otra puerta»; el 401 sigue siendo el genérico", () => {
    expect(esOtroPortal(new ErrorApi(403, "Esta cuenta es de adoptante."))).toBe(true);
    expect(esOtroPortal(new ErrorApi(401, "x"))).toBe(false);
    expect(esOtroPortal(new Error("sin red"))).toBe(false);
    expect(textoError(new ErrorApi(401, "x"))).toBe("Correo o contraseña incorrectos.");
  });
});

describe("encuesta y Mi hogar (arreglos, parte C)", () => {
  const vista = pantallas["./AdoptantePantallas.tsx"] as string;
  it("la burbuja usa solo animales con foto y no hay etiqueta «Tu respuesta»", () => {
    expect(vista).toContain("catalogo.filter((a) => a.foto)");
    expect(vista).not.toContain("Tu respuesta");
  });
  it("«Mi hogar» resume lo guardado y ofrece «Cambiar mis respuestas»; la bienvenida, ver los compañeros", () => {
    expect(vista).toContain("Cambiar mis respuestas");
    expect(vista).toContain("Ver mis compañeros con mis respuestas guardadas");
    expect(pantallas["./Adoptante.tsx"]).toContain('["hogar", "Mi hogar", miHogar]');
  });
});

describe("«Mi hogar» en el teléfono", () => {
  it("la bienvenida tiene su enlace (el menú superior es solo de computador)", () => {
    const vista = pantallas["./AdoptantePantallas.tsx"] as string;
    expect(vista).toMatch(/solo-movil" onClick=\{alMiHogar\}>Mi hogar/);
    expect(pantallas["./Adoptante.tsx"]).toContain("alMiHogar={miHogar}");
  });
});

describe("bienvenida en computador (tarea 4)", () => {
  it("«Te están esperando», 6 tarjetas que abren al animal y el bloque de 4 pasos con Mi hogar y Mis solicitudes", () => {
    const vista = pantallas["./AdoptantePantallas.tsx"] as string;
    expect(vista).toContain("Te están esperando");
    expect(vista).toContain("Conoce a algunos de los ${catalogo.length}");
    expect(vista).toContain("onClick={() => alVer(a)}");
    expect(vista).toContain("paraLaBienvenida(destacados)");  // solo los que «Elige» puede abrir
    expect(pantallas["./Adoptante.tsx"]).toContain("destacados={fuente}");
    expect(vista).toContain("Así funciona tu adopción");
    for (const paso of ["Responde", "Elige", "Solicita", "¡A casa!"]) expect(vista).toContain(`["${paso}"`);
    expect(vista).toContain("onClick={alMiHogar}>Ir a Mi hogar");
    expect(vista).toContain("onClick={alVerSolicitudes}>Ver mis solicitudes");
  });
});
