import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ESPERA_LENTA_MS, alCambiarEspera, conAvisoDeEspera, pedir } from "./api";

// Render gratis se duerme: la primera petición puede tardar hasta un minuto. El panel debe
// decirlo en vez de parecer colgado, y quitar el aviso apenas el servidor responde.
describe("aviso de «despertando el servidor»", () => {
  let vistas: number[];
  let dejarDeOir: () => void;

  beforeEach(() => {
    vi.useFakeTimers();
    vistas = [];
    dejarDeOir = alCambiarEspera((lentas) => vistas.push(lentas));
  });
  afterEach(() => {
    dejarDeOir();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("una respuesta rápida no avisa nada", async () => {
    await conAvisoDeEspera(Promise.resolve("ok"));
    await vi.advanceTimersByTimeAsync(ESPERA_LENTA_MS * 2);
    expect(vistas).toEqual([]);
  });

  it("si pasan 4 segundos avisa, y deja de avisar cuando llega la respuesta", async () => {
    let responder: (valor: string) => void = () => {};
    const lenta = conAvisoDeEspera(new Promise<string>((listo) => { responder = listo; }));
    await vi.advanceTimersByTimeAsync(ESPERA_LENTA_MS - 1);
    expect(vistas).toEqual([]);
    await vi.advanceTimersByTimeAsync(1);
    expect(vistas).toEqual([1]);
    responder("despierto");
    expect(await lenta).toBe("despierto");
    expect(vistas).toEqual([1, 0]);
  });

  it("si la petición falla el aviso también se quita", async () => {
    let fallar: (error: Error) => void = () => {};
    const lenta = conAvisoDeEspera(new Promise<string>((_, no) => { fallar = no; }));
    const resultado = lenta.catch((e: Error) => e.message);
    await vi.advanceTimersByTimeAsync(ESPERA_LENTA_MS);
    fallar(new Error("sin conexión"));
    expect(await resultado).toBe("sin conexión");
    expect(vistas).toEqual([1, 0]);
  });

  it("toda petición a la API pasa por el aviso", async () => {
    let responder: (r: Response) => void = () => {};
    vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>((listo) => { responder = listo; })));
    const cola = pedir<string[]>("/cola", {}, "t");
    await vi.advanceTimersByTimeAsync(ESPERA_LENTA_MS);
    expect(vistas).toEqual([1]);
    responder(new Response("[]"));
    expect(await cola).toEqual([]);
    expect(vistas).toEqual([1, 0]);
  });

  it("quien deja de oír no recibe más avisos", async () => {
    dejarDeOir();
    conAvisoDeEspera(new Promise(() => {}));
    await vi.advanceTimersByTimeAsync(ESPERA_LENTA_MS);
    expect(vistas).toEqual([]);
  });
});
