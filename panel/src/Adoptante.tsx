import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import "./adoptante.css";
import {
  AnimalPublicado, Coleccion, MiSolicitud, Perfil, Recomendado, catalogo, coleccion, descargarCompromiso,
  guardarPerfil, miPerfil, misSolicitudes, recomendaciones, solicitar,
} from "./apiAdopcion";
import {
  Bienvenida, Combinan, Elegir, Encuesta, Listo, MisSolicitudes,
} from "./AdoptantePantallas";
import Acompanar from "./Acompanar";
import ColeccionAnimales from "./ColeccionAnimales";
import CuidadosYPasos from "./CuidadosYPasos";
import Despertando from "./Despertando";
import EligeCompanero from "./EligeCompanero";
import MiHogar from "./MiHogar";
import { PREGUNTAS, perfilDesdeRespuestas } from "./encuesta";
import {
  INICIAL, PantallaAdopcion, actual, contar, filtrar, flujo, mejores, solicitudDe,
} from "./flujoAdopcion";
import { Huella, Icono } from "./Ilustraciones";
import { textoError } from "./mensajes";
import {
  Efecto, Preferencias, Sonido, arrancarSola, documentoActivado, guardarPreferencias, leerPreferencias,
  sonidoDeEspecie,
} from "./sonido";

type Animal = AnimalPublicado | Recomendado;
interface Datos {
  perfil: Perfil | null; catalogo: AnimalPublicado[]; recomendados: Recomendado[] | null;
  mias: MiSolicitud[]; cargando: boolean; coleccion: Coleccion | null;
}

/** Adoptante (#420): «Elige a tu compañero». Perfil por encuesta (RF-08), recomendaciones con el
 *  puntaje del servidor (RF-09), solicitud (RF-27) y compromiso en PDF (RF-29). */
export default function Adoptante({ token, nombre, alSalir }: {
  token: string; nombre: string; alSalir: () => void;
}) {
  const [s, despachar] = useReducer(flujo, INICIAL);
  const [datos, setDatos] = useState<Datos>({ perfil: null, catalogo: [], recomendados: null,
    mias: [], cargando: true, coleccion: null });
  const [mensaje, setMensaje] = useState<{ texto: string; error: boolean } | null>(null);
  const [enviando, setEnviando] = useState(false);
  const { prefs, sonando, toque, cambiar } = useSonido();

  const cargar = useCallback(async () => {
    // #508: si la colección falla, la página sigue sin el contador ni los adoptados (nada inventado).
    const [perfil, mias, cat, col] = await Promise.all([miPerfil(token), misSolicitudes(token), catalogo(),
      coleccion().catch(() => null)]);
    // Con perfil, el servidor ordena por compatibilidad y deja fuera las restricciones duras.
    // #516: sin el seguimiento aceptado (RN-10) no hay matches: el servidor respondería 403.
    const recomendados = perfil?.acepta_seguimiento ? await recomendaciones(token) : null;
    setDatos({ perfil, mias, catalogo: cat, recomendados, cargando: false, coleccion: col });
  }, [token]);

  const fallo = (e: unknown) => setMensaje({ texto: textoError(e), error: true });
  useEffect(() => {
    cargar().catch((e) => { fallo(e); setDatos((d) => ({ ...d, cargando: false })); });
  }, [cargar]);

  // Al terminar la encuesta se guarda el perfil real y se piden las recomendaciones de nuevo.
  useEffect(() => {
    if (!s.guardar) return;
    const perfil = perfilDesdeRespuestas(s.respuestas);
    if (!perfil) { despachar({ tipo: "guardado" }); return; }
    setDatos((d) => ({ ...d, cargando: true }));
    guardarPerfil(token, perfil).then(cargar)
      .then(() => setMensaje({ texto: "Guardamos tus respuestas en tu perfil.", error: false }))
      .catch((e) => { fallo(e); setDatos((d) => ({ ...d, cargando: false })); })
      .finally(() => despachar({ tipo: "guardado" }));
  }, [s.guardar, s.respuestas, token, cargar]);

  // Al cambiar de pantalla: arriba del todo y el foco en el título (teclado y lector de pantalla).
  const primera = useRef(true);
  useEffect(() => {
    if (primera.current) { primera.current = false; return; }
    window.scrollTo?.(0, 0);
    document.querySelector<HTMLElement>(".adop [data-titulo]")?.focus();
  }, [s.pantalla, s.paso]);

  const ir = (efecto: Efecto, accion: Parameters<typeof despachar>[0]) => {
    toque(efecto);
    setMensaje(null);
    despachar(accion);
  };

  // Lo que se ve en «Elige»: con perfil, los recomendados; sin perfil, todo el catálogo.
  const conPerfil = datos.perfil !== null;
  const fuente: Animal[] = datos.recomendados ?? datos.catalogo;
  const ocultos = conPerfil && datos.recomendados ? Math.max(0, datos.catalogo.length - datos.recomendados.length) : 0;
  const visibles = filtrar(fuente, s.filtro);
  const idActual = actual(visibles.map((a) => a.animal_id), s.elegido);
  const animal = visibles.find((a) => a.animal_id === idActual) ?? null;
  // Un animal ya adoptado sale del catálogo: su nombre y especie vienen con la solicitud.
  const animalDe = (id: number): AnimalPublicado => {
    const s = datos.mias.find((x) => x.animal_id === id);
    return fuente.find((a) => a.animal_id === id) ?? datos.catalogo.find((a) => a.animal_id === id)
      ?? { animal_id: id, nombre: s?.nombre ?? `Animal ${id}`, especie: s?.especie ?? "",
           descripcion: "", tamano: "", energia: "", edad_meses: 0, apto_ninos: false,
           apto_otros_animales: false, necesita_patio: false };
  };

  // Arreglos, parte C: «¡Empezar!» arranca sin marcar; «Cambiar mis respuestas» precarga.
  const empezar = () => ir("siguiente", { tipo: "empezar", perfil: datos.perfil });
  const cambiarRespuestas = () => ir("siguiente", { tipo: "empezar", perfil: datos.perfil, precargar: true });
  // #516: sin el seguimiento aceptado no hay matches ni solicitudes (RN-10): se explica por qué.
  const sinSeguimiento = datos.perfil !== null && !datos.perfil.acepta_seguimiento;
  const verCompaneros = () => ir("siguiente", { tipo: "irA", pantalla: sinSeguimiento ? "acompanar" : "combinan" });
  const [aceptando, setAceptando] = useState(false);
  async function aceptarSeguimiento() {
    if (!datos.perfil) return;
    toque("elegir");
    setAceptando(true);
    try {
      await guardarPerfil(token, { ...datos.perfil, acepta_seguimiento: true }); // «Sí, acepto»
      await cargar();
      despachar({ tipo: "irA", pantalla: "combinan" });
    } catch (e) {
      fallo(e);
    } finally {
      setAceptando(false);
    }
  }
  const miHogar = () => ir("pop", { tipo: "irA", pantalla: "hogar" });

  async function elegir(a: Animal) {
    if (sinSeguimiento) { ir("pop", { tipo: "irA", pantalla: "acompanar" }); return; }
    if (!conPerfil) {
      ir("siguiente", { tipo: "empezar", perfil: null });
      setMensaje({ texto: "Antes de solicitar, cuéntanos de tu hogar.", error: false });
      return;
    }
    toque("elegir");
    setEnviando(true);
    setMensaje(null);
    try {
      await solicitar(token, a.animal_id, "");
      const mias = await misSolicitudes(token);
      setDatos((d) => ({ ...d, mias }));
      toque("fanfarria");
      despachar({ tipo: "solicitado", animal: a.animal_id, recien: true });
    } catch (e) {
      fallo(e);
    } finally {
      setEnviando(false);
    }
  }

  async function descargar(id: number) {
    toque("pop");
    try {
      await descargarCompromiso(token, id);
      setMensaje({ texto: "Compromiso descargado: imprímelo y fírmalo en el refugio.", error: false });
    } catch (e) {
      fallo(e);
    }
  }

  // #508: los 3 mejores matches reales (el mismo cálculo de «Combinan»); sin encuesta o sin el
  // seguimiento aceptado (RN-10: no podría solicitar), las cartas van boca abajo.
  const tresMejores = datos.perfil?.acepta_seguimiento && datos.recomendados
    ? mejores(datos.recomendados, s.respuestas).lista : null;

  const nav: [PantallaAdopcion, string, () => void][] = [
    ["inicio", "Adoptar", () => ir("pop", { tipo: "irA", pantalla: "inicio" })],
    ["hogar", "Mi hogar", miHogar],
    ["solicitudes", "Mis solicitudes", () => ir("pop", { tipo: "irA", pantalla: "solicitudes" })],
  ];
  return (
    <div className={`adop${prefs.movimiento ? " adop--mov" : " adop--quieto"}`}>
      <Fondo />
      <header className="adop-barra">
        <span className="adop-marca">
          <Huella tam={28} color="#E8508A" className="bambolea" />
          <span className="h adop-marca-texto">Patitas en Casa</span>
        </span>
        <nav className="adop-nav solo-pc" aria-label="Adopción">
          {nav.map(([p, texto, accion]) => (
            <button key={p} className="adop-nav-boton" onClick={accion}
              aria-current={s.pantalla === p ? "page" : undefined}>{texto}</button>))}
        </nav>
        <div className="adop-controles">
          <button className="adop-control" aria-label="Música" aria-pressed={prefs.musica && sonando}
            title={prefs.musica && sonando ? "Apagar la música" : "Prender la música"}
            onClick={() => cambiar("musica")}>
            <Icono d="M9 18V5l12-2v13M6 15a3 3 0 1 0 0 6a3 3 0 1 0 0-6zM18 13a3 3 0 1 0 0 6a3 3 0 1 0 0-6z" tam={18} grosor={2.2} />
            {prefs.musica && sonando
              ? <span className="ecualizador" aria-hidden="true"><i /><i /><i /></span>
              : <span className="solo-pc adop-control-texto">Música</span>}
          </button>
          <button className="adop-control" aria-label="Sonidos al tocar" aria-pressed={prefs.efectos}
            title="Sonidos al tocar" onClick={() => cambiar("efectos")}>
            <Icono d={prefs.efectos ? "M11 5L6 9H2v6h4l5 4zM15.5 8.5a5 5 0 0 1 0 7M19 5a10 10 0 0 1 0 14"
              : "M11 5L6 9H2v6h4l5 4zM16 9l6 6M22 9l-6 6"} tam={18} grosor={2.2} />
          </button>
          <button className="adop-control" aria-label="Movimiento" aria-pressed={prefs.movimiento}
            title="Animaciones" onClick={() => cambiar("movimiento")}>
            <Icono d={prefs.movimiento ? "M3 9c2-3 4-3 6 0s4 3 6 0 4-3 6 0M3 15c2-3 4-3 6 0s4 3 6 0 4-3 6 0"
              : "M3 9h18M3 15h18"} tam={18} grosor={2.2} />
          </button>
          <button className="adop-control adop-salir" onClick={alSalir} title={`Salir (${nombre})`}>
            <Icono d="M15 4h4v16h-4M10 8l-4 4 4 4M6 12h10" tam={18} grosor={2.2} />
            <span className="adop-salir-texto">Salir</span>
          </button>
        </div>
      </header>
      <Despertando />
      <main className={`adop-contenido adop-contenido--${s.pantalla}`}>
        {mensaje && (
          <p className={`adop-mensaje${mensaje.error ? " adop-mensaje--error" : ""}`}
            role={mensaje.error ? "alert" : "status"}>{mensaje.texto}</p>)}
        {s.pantalla === "inicio" && (
          <Bienvenida catalogo={datos.catalogo} cargando={datos.cargando} mias={datos.mias}
            conPerfil={conPerfil} alVerCompaneros={verCompaneros} alMiHogar={miHogar}
            alEmpezar={empezar} alVerTodos={() => ir("siguiente", { tipo: "verTodos" })}
            alVerSolicitudes={() => ir("pop", { tipo: "irA", pantalla: "solicitudes" })}
            secciones={!datos.cargando && (<>
              <EligeCompanero mejores={tresMejores} mias={datos.mias} enviando={enviando} alEmpezar={empezar}
                alElegir={(a) => void elegir(a)}
                alVerSolicitud={(a) => ir("pop", { tipo: "solicitado", animal: a.animal_id, recien: false })} />
              <ColeccionAnimales disponibles={datos.catalogo} coleccion={datos.coleccion} abribles={fuente}
                alVer={(a) => ir(sonidoDeEspecie(a.especie), { tipo: "ver", animal: a.animal_id })} />
              <CuidadosYPasos />
            </>)} />)}
        {s.pantalla === "encuesta" && (
          <Encuesta paso={s.paso} respuestas={s.respuestas} catalogo={datos.catalogo}
            alAtras={() => ir("atras", { tipo: "atras" })}
            alResponder={(i) => {
              const valor = PREGUNTAS[s.paso].opciones[i].valor;
              const efecto: Efecto = valor === "perro" ? "guau" : valor === "gato" ? "miau"
                : s.paso < PREGUNTAS.length - 1 ? "siguiente" : "elegir";
              ir(efecto, { tipo: "responder", opcion: i });
            }} />)}
        {s.pantalla === "combinan" && (
          <Combinan recomendados={datos.recomendados} respuestas={s.respuestas}
            cargando={datos.cargando || s.guardar} ocultos={ocultos} total={fuente.length}
            alVer={(a) => ir(sonidoDeEspecie(a.especie), { tipo: "ver", animal: a.animal_id })}
            alVerTodos={() => ir("siguiente", { tipo: "verTodos" })} alRepetir={cambiarRespuestas} />)}
        {s.pantalla === "elegir" && (
          <Elegir lista={visibles} animal={animal} filtro={s.filtro} conteo={contar(fuente)}
            ocultos={ocultos} cargando={datos.cargando} conPerfil={conPerfil}
            aceptaSeguimiento={datos.perfil?.acepta_seguimiento ?? false} mias={datos.mias}
            enviando={enviando}
            alFiltrar={(f) => ir("pop", { tipo: "filtrar", filtro: f })}
            alMover={(paso) => ir("pasar", { tipo: "mover", ids: visibles.map((a) => a.animal_id), paso })}
            alVer={(a) => ir(sonidoDeEspecie(a.especie), { tipo: "ver", animal: a.animal_id })}
            alElegir={(a) => void elegir(a)}
            alVerSolicitud={(a) => ir("pop", { tipo: "solicitado", animal: a.animal_id, recien: false })}
            alRevisar={cambiarRespuestas} alAtras={() => ir("atras", { tipo: "atras" })} />)}
        {s.pantalla === "listo" && s.elegido !== null && (
          <Listo animal={animalDe(s.elegido)} solicitud={solicitudDe(datos.mias, s.elegido)}
            recien={s.recien} alDescargar={(id) => void descargar(id)}
            alInicio={() => ir("atras", { tipo: "irA", pantalla: "inicio" })}
            alSolicitudes={() => ir("pop", { tipo: "irA", pantalla: "solicitudes" })} />)}
        {s.pantalla === "acompanar" && (
          <Acompanar aceptando={aceptando || datos.cargando || s.guardar} alAceptar={() => void aceptarSeguimiento()}
            alVerSinSolicitar={() => ir("siguiente", { tipo: "verTodos" })}
            alInicio={() => ir("atras", { tipo: "irA", pantalla: "inicio" })} />)}
        {s.pantalla === "hogar" && (
          <MiHogar perfil={datos.perfil} alEmpezar={empezar} alVerCompaneros={verCompaneros}
            alCambiar={(paso) => ir("siguiente", { tipo: "empezar", perfil: datos.perfil, precargar: true, paso })}
            alAtras={() => ir("atras", { tipo: "atras" })} />)}
        {s.pantalla === "solicitudes" && (
          <MisSolicitudes mias={datos.mias} animalDe={animalDe}
            alVer={(x) => ir("pop", { tipo: "solicitado", animal: x.animal_id, recien: false })}
            alDescargar={(id) => void descargar(id)} alAtras={() => ir("atras", { tipo: "atras" })}
            alVerTodos={() => ir("siguiente", { tipo: "verTodos" })} />)}
      </main>
    </div>
  );
}

/** Manchas pastel y huellas que flotan detrás de todo (decorativo). */
function Fondo() {
  return (
    <div className="adop-fondo" aria-hidden="true">
      <span className="mancha mancha--rosa" /><span className="mancha mancha--lila" />
      <span className="mancha mancha--menta" /><span className="mancha mancha--amarillo" />
      <Huella tam={26} color="#F2B8CB" className="huella-flota huella-1" />
      <Huella tam={20} color="#C9BDF5" className="huella-flota huella-2" />
      <Huella tam={22} color="#F7D77A" className="huella-flota huella-3" />
      <Huella tam={18} color="#A9DDB6" className="huella-flota huella-4" />
    </div>
  );
}

/** Sonido y preferencias: la música arranca sola al entrar (tarea 5: ya, si el documento tuvo un
 *  gesto; si no, con el primer toque o tecla en cualquier parte) salvo que la persona la haya
 *  apagado, y se detiene al salir de la vista o al ocultar la pestaña; las preferencias se
 *  recuerdan en este navegador. */
function useSonido() {
  const [prefs, setPrefs] = useState<Preferencias>(() => leerPreferencias());
  const sonido = useRef<Sonido | null>(null);
  if (!sonido.current) sonido.current = new Sonido(prefs);
  const [sonando, setSonando] = useState(false);

  useEffect(() => {
    const so = sonido.current!;
    const alCambiarVisibilidad = () => {
      if (document.hidden) so.detenerMusica(); else so.reanudar();
      setSonando(so.sonando);
    };
    document.addEventListener("visibilitychange", alCambiarVisibilidad);
    // Tarea 5: la música arranca sola (ya, si hubo un gesto; si no, con el primer toque o tecla).
    const quitarArranque = arrancarSola(so, {
      musica: prefs.musica, activado: documentoActivado(), destino: window,
      alArrancar: () => setSonando(so.sonando),
    });
    return () => {
      quitarArranque();
      document.removeEventListener("visibilitychange", alCambiarVisibilidad);
      so.cerrar(); // salir de la vista (por ejemplo, «Salir»): se calla y suelta el audio
    };
  }, []);

  const toque = useCallback((efecto?: Efecto) => {
    const so = sonido.current!;
    so.despertar();
    if (efecto) so.efecto(efecto);
    setSonando(so.sonando);
  }, []);

  const cambiar = (clave: keyof Preferencias) => {
    const so = sonido.current!;
    let nuevas = { ...prefs, [clave]: !prefs[clave] };
    // Con la música elegida pero aún callada (no ha habido un toque), el botón la prende.
    if (clave === "musica" && prefs.musica && !so.sonando) nuevas = { ...prefs };
    if (clave === "musica") so.cambiarMusica(nuevas.musica);
    if (clave === "efectos") so.efectos = nuevas.efectos;
    if (clave === "efectos" && nuevas.efectos) so.efecto("pop"); else so.despertar();
    setPrefs(nuevas);
    guardarPreferencias(nuevas);
    setSonando(so.sonando);
  };

  return { prefs, sonando, toque, cambiar };
}
