// Sonido de la adopción (#420), sintetizado con Web Audio: no hay archivos de audio.
// Las recetas (qué notas suena cada efecto) y la melodía son datos puros y se prueban sin
// navegador; la clase Sonido solo las toca. Los navegadores bloquean el sonido automático, así
// que la música arranca con el primer toque (despertar) y nunca antes.

export type Efecto = "pop" | "siguiente" | "atras" | "pasar" | "elegir" | "guau" | "miau"
  | "fanfarria";

/** Una nota: frecuencia (Hz), inicio relativo (s), duración (s), forma de onda y volumen. */
export interface Tono {
  f: number; t: number; d: number; tipo: OscillatorType; vol: number;
  /** La frecuencia sube o baja hasta aquí a mitad de la nota (y hasta fFin al terminar). */
  fA?: number; fFin?: number;
}

const arpegio = (notas: number[], paso: number, d: number, tipo: OscillatorType,
                 vol: number): Tono[] => notas.map((f, i) => ({ f, t: i * paso, d, tipo, vol }));

/** Lo que suena con cada acción, como en el prototipo. */
export function receta(efecto: Efecto): Tono[] {
  switch (efecto) {
    case "pop": return [{ f: 560, t: 0, d: 0.14, tipo: "sine", vol: 0.3, fA: 1100 }];
    case "siguiente": return arpegio([523, 784], 0.07, 0.15, "triangle", 0.22);
    case "atras": return arpegio([659, 440], 0.07, 0.15, "triangle", 0.2);
    case "pasar": return [{ f: 300, t: 0, d: 0.16, tipo: "sine", vol: 0.22, fA: 900 }];
    case "elegir": return arpegio([523, 659, 784, 1047], 0.06, 0.18, "triangle", 0.2);
    case "guau": return [
      { f: 430, t: 0, d: 0.13, tipo: "sawtooth", vol: 0.12, fA: 300, fFin: 180 },
      { f: 470, t: 0.17, d: 0.13, tipo: "sawtooth", vol: 0.12, fA: 320, fFin: 190 }];
    case "miau": return [{ f: 620, t: 0, d: 0.42, tipo: "sine", vol: 0.22, fA: 940, fFin: 520 }];
    case "fanfarria": return arpegio([523, 659, 784, 1047, 784, 1047, 1319], 0.1, 0.24,
                                     "triangle", 0.22);
  }
}

/** «Guau» para los perros y «miau» para los gatos. */
export const sonidoDeEspecie = (especie: string): Efecto => (especie === "gato" ? "miau" : "guau");

/** Nota MIDI a hercios (69 = La 440). */
export const mtof = (m: number) => 440 * 2 ** ((m - 69) / 12);

// Musiquita en bucle: 32 pasos de melodía (0 = silencio) y un bajo cada 4 pasos.
export const MELODIA = [72, 76, 79, 76, 77, 81, 79, 0, 76, 79, 84, 79, 81, 79, 76, 0,
  74, 77, 81, 77, 79, 76, 72, 0, 74, 76, 77, 74, 72, 0, 79, 0];
export const BAJO = [48, 53, 48, 55, 50, 55, 53, 48];
export const PASO_S = 0.19;
export const VOLUMEN_MUSICA = 0.07; // bajito: acompaña, no tapa los efectos
export const FUNDIDO_S = 1.5; // tarea 5: al arrancar sola, sube suave hasta VOLUMEN_MUSICA

/** Las notas de un paso de la música (melodía, bajo y un tic suave en los impares). */
export function tonosDelPaso(paso: number): Tono[] {
  const i = paso % MELODIA.length;
  const tonos: Tono[] = [];
  if (MELODIA[i]) tonos.push({ f: mtof(MELODIA[i]), t: 0, d: 0.24, tipo: "triangle", vol: 0.55 });
  if (i % 4 === 0) tonos.push({ f: mtof(BAJO[i / 4]), t: 0, d: 0.5, tipo: "sine", vol: 0.7 });
  if (i % 2 === 1) tonos.push({ f: 1800, t: 0, d: 0.03, tipo: "square", vol: 0.04 });
  return tonos;
}

// ---------- preferencias (se recuerdan en este navegador) ----------

export interface Preferencias { musica: boolean; efectos: boolean; movimiento: boolean }
export const PREFERENCIAS_POR_DEFECTO: Preferencias = { musica: true, efectos: true, movimiento: true };
const CLAVE = "patitas.adopcion.preferencias";

type Almacen = Pick<Storage, "getItem" | "setItem">;
function almacenDelNavegador(): Almacen | null {
  try { return globalThis.localStorage ?? null; } catch { return null; }
}

/** Lo guardado, o lo de por defecto si no hay nada, está dañado o el navegador lo bloquea. */
export function leerPreferencias(almacen: Almacen | null = almacenDelNavegador()): Preferencias {
  try {
    const guardado = JSON.parse(almacen?.getItem(CLAVE) ?? "null");
    if (guardado && typeof guardado === "object") {
      const p = { ...PREFERENCIAS_POR_DEFECTO };
      for (const k of Object.keys(p) as (keyof Preferencias)[]) {
        if (typeof guardado[k] === "boolean") p[k] = guardado[k];
      }
      return p;
    }
  } catch { /* JSON dañado o almacenamiento bloqueado: se usa lo de por defecto */ }
  return { ...PREFERENCIAS_POR_DEFECTO };
}

export function guardarPreferencias(p: Preferencias,
                                    almacen: Almacen | null = almacenDelNavegador()): void {
  try { almacen?.setItem(CLAVE, JSON.stringify(p)); } catch { /* ventana privada: no pasa nada */ }
}

// ---------- reproducción (solo en el navegador) ----------

type CrearContexto = () => AudioContext | null;
const contextoDelNavegador: CrearContexto = () => {
  const AC = globalThis.AudioContext
    ?? (globalThis as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  return AC ? new AC() : null;
};

export class Sonido {
  efectos: boolean;
  private musicaActiva: boolean;
  private despierto = false;
  private ctx: AudioContext | null = null;
  private maestro: GainNode | null = null;
  private volMusica: GainNode | null = null;
  private reloj: ReturnType<typeof setInterval> | null = null;
  private paso = 0;
  private proxima = 0;

  constructor(prefs: Pick<Preferencias, "musica" | "efectos">,
              private crear: CrearContexto = contextoDelNavegador) {
    this.efectos = prefs.efectos;
    this.musicaActiva = prefs.musica;
  }

  get sonando(): boolean { return this.reloj !== null; }

  private audio(): AudioContext | null {
    if (!this.ctx) {
      try { this.ctx = this.crear(); } catch { this.ctx = null; }
      if (!this.ctx) return null;
      this.maestro = this.ctx.createGain();
      this.maestro.gain.value = 0.9;
      this.maestro.connect(this.ctx.destination);
    }
    if (this.ctx.state === "suspended") void this.ctx.resume();
    return this.ctx;
  }

  private tocarTono(t0: number, n: Tono, destino: AudioNode): void {
    const c = this.ctx!;
    const o = c.createOscillator();
    const g = c.createGain();
    const t = t0 + n.t;
    o.type = n.tipo;
    o.frequency.setValueAtTime(n.f, t);
    if (n.fA) o.frequency.exponentialRampToValueAtTime(n.fA, t + n.d * 0.45);
    if (n.fFin) o.frequency.exponentialRampToValueAtTime(n.fFin, t + n.d);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(n.vol, t + 0.015);
    g.gain.exponentialRampToValueAtTime(0.0001, t + n.d);
    o.connect(g);
    g.connect(destino);
    o.start(t);
    o.stop(t + n.d + 0.05);
  }

  /** El primer toque del usuario: desde aquí el navegador deja sonar la música. Con
   *  `fundido`, la música entra subiendo en FUNDIDO_S (tarea 5: cuando arranca sola). */
  despertar(fundido = false): void {
    if (this.despierto) return;
    this.despierto = true;
    if (this.musicaActiva) this.iniciarMusica(fundido);
  }

  efecto(e: Efecto): void {
    if (!this.efectos) return;
    const c = this.audio();
    if (!c || !this.maestro) return;
    const t = c.currentTime + 0.01;
    for (const n of receta(e)) this.tocarTono(t, n, this.maestro);
  }

  /** Prende o apaga la música y recuerda la elección. */
  cambiarMusica(activa: boolean): void {
    this.musicaActiva = activa;
    if (activa) { this.despierto = true; this.iniciarMusica(); } else this.detenerMusica();
  }

  /** Al volver a la pestaña o a la vista: retoma la música si estaba prendida. */
  reanudar(): void {
    if (this.despierto && this.musicaActiva) this.iniciarMusica();
  }

  private iniciarMusica(fundido = false): void {
    if (this.reloj) return;
    const c = this.audio();
    if (!c || !this.maestro) return;
    this.volMusica = c.createGain();
    if (fundido) {
      this.volMusica.gain.setValueAtTime(0.0001, c.currentTime);
      this.volMusica.gain.exponentialRampToValueAtTime(VOLUMEN_MUSICA, c.currentTime + FUNDIDO_S);
    } else {
      this.volMusica.gain.value = VOLUMEN_MUSICA;
    }
    this.volMusica.connect(this.maestro);
    this.paso = 0;
    this.proxima = c.currentTime + 0.08;
    // Se programa un poco por delante (0,3 s) para que el reloj de JS no haga saltar el ritmo.
    this.reloj = setInterval(() => {
      if (!this.volMusica) return;
      while (this.proxima < c.currentTime + 0.3) {
        for (const n of tonosDelPaso(this.paso)) this.tocarTono(this.proxima, n, this.volMusica);
        this.proxima += PASO_S;
        this.paso++;
      }
    }, 80);
  }

  /** Detiene la música (al apagarla, al salir de la vista o al ocultar la pestaña). */
  detenerMusica(): void {
    if (this.reloj) { clearInterval(this.reloj); this.reloj = null; }
    if (this.volMusica && this.ctx) {
      try { this.volMusica.gain.setTargetAtTime(0.0001, this.ctx.currentTime, 0.08); } catch { /* ya cerrado */ }
    }
    this.volMusica = null;
  }

  cerrar(): void {
    this.detenerMusica();
    try { void this.ctx?.close(); } catch { /* ya cerrado */ }
    this.ctx = null;
    this.maestro = null;
  }
}

/** Lo mínimo de Sonido que necesita arrancarSola (para probarla sin audio). */
export interface Despertable { despertar(fundido?: boolean): void }

/** Tarea 5: la música del adoptante arranca SOLA al entrar a su vista.
 *  - Con la música apagada por la persona (preferencia guardada), nunca arranca sola.
 *  - Si el documento ya tiene activación del usuario (navigator.userActivation.hasBeenActive:
 *    por ejemplo, viene de tocar «Entrar» o «Crear cuenta»), arranca ya, con fundido.
 *  - Si no (abrió /panel/ con la sesión ya iniciada), arranca con el PRIMER pointerdown o
 *    keydown en cualquier parte (los navegadores no dejan sonar audio antes).
 *  Devuelve la función que quita los escuchas (al salir de la vista). */
export function arrancarSola(sonido: Despertable, opciones: {
  musica: boolean; activado: boolean; destino: Pick<EventTarget, "addEventListener" | "removeEventListener">;
  alArrancar?: () => void;
}): () => void {
  const { musica, activado, destino, alArrancar } = opciones;
  if (!musica) return () => {};
  const arrancar = () => { sonido.despertar(true); alArrancar?.(); };
  if (activado) { arrancar(); return () => {}; }
  const quitar = () => {
    destino.removeEventListener("pointerdown", alPrimerToque);
    destino.removeEventListener("keydown", alPrimerToque);
  };
  function alPrimerToque() { quitar(); arrancar(); }
  destino.addEventListener("pointerdown", alPrimerToque, { once: true });
  destino.addEventListener("keydown", alPrimerToque, { once: true });
  return quitar;
}

/** ¿El documento ya tuvo un gesto del usuario? (Chrome, Edge, Safari 16.4+, Firefox 120+). */
export const documentoActivado = (): boolean =>
  (globalThis.navigator as Navigator & { userActivation?: { hasBeenActive: boolean } } | undefined)
    ?.userActivation?.hasBeenActive ?? false;
