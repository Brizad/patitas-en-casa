import { afterEach, describe, expect, it, vi } from "vitest";
import { ErrorApi, MENSAJE_SERVIDOR, pedir } from "./api";

// #396: cuando Render o la base fallan, la culpa no es de lo que escribió la persona. Un
// 500/502/503 o una página HTML no deben mostrarse como «Datos no válidos».
function responder(cuerpo: string, estado: number, tipo = "application/json") {
  vi.stubGlobal("fetch", vi.fn(async () =>
    new Response(cuerpo, { status: estado, headers: { "Content-Type": tipo } })));
}

async function errorDe(promesa: Promise<unknown>): Promise<ErrorApi> {
  try {
    await promesa;
  } catch (error) {
    return error as ErrorApi;
  }
  throw new Error("se esperaba un error");
}

describe("errores del servidor en el panel", () => {
  afterEach(() => vi.unstubAllGlobals());

  it.each([500, 502, 503, 504])("un %i dice que el servidor tuvo un problema", async (estado) => {
    responder("<html><body>Bad Gateway</body></html>", estado, "text/html");
    const error = await errorDe(pedir("/cola"));
    expect(error.estado).toBe(estado);
    expect(error.message).toBe(MENSAJE_SERVIDOR);
  });

  it("un 500 de la API con JSON tampoco es «Datos no válidos»", async () => {
    responder(JSON.stringify({ detail: "Internal Server Error" }), 500);
    expect((await errorDe(pedir("/cola"))).message).toBe(MENSAJE_SERVIDOR);
  });

  it("una respuesta de error sin JSON dice que el servidor tuvo un problema", async () => {
    responder("Request Entity Too Large", 413, "text/plain");
    expect((await errorDe(pedir("/cola"))).message).toBe(MENSAJE_SERVIDOR);
  });

  it("el mensaje es el que pidió el autor", () => {
    expect(MENSAJE_SERVIDOR).toBe("El servidor tuvo un problema, intenta de nuevo en un momento.");
  });

  it("un 4xx de la API con detalle sigue mostrando ese detalle", async () => {
    responder(JSON.stringify({ detail: "Ese reporte ya fue confirmado." }), 409);
    expect((await errorDe(pedir("/cola"))).message).toBe("Ese reporte ya fue confirmado.");
  });

  it("un 422 de validación (detalle en lista) sigue siendo «Datos no válidos.»", async () => {
    responder(JSON.stringify({ detail: [{ loc: ["body"], msg: "x" }] }), 422);
    expect((await errorDe(pedir("/cola"))).message).toBe("Datos no válidos.");
  });

  it("una respuesta correcta sin cuerpo sigue funcionando", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 204 })));
    expect(await pedir("/algo")).toEqual({});
  });
});
