// Pantallas «Elige a tu compañero» del adoptante (#420). Solo dibujan: los datos y lo que pasa
// con cada toque vienen de Adoptante.tsx (el flujo puro está en flujoAdopcion.ts).
import type { CSSProperties, KeyboardEvent } from "react";
import type { AnimalPublicado, MiSolicitud, Recomendado } from "./apiAdopcion";
import Animalitos from "./Animalitos";
import Cargando from "./Cargando";
import { PREGUNTAS, Respuestas, opcionElegida } from "./encuesta";
import {
  ESTADO_SOLICITUD, Filtro, abierta, especieTexto, estadisticas, fondoDe, hoyYAdulto, insignias,
  mejores, pasosSolicitud, razonCorta, resumenCorto, solicitudDe,
} from "./flujoAdopcion";
import { Confeti, Corazon, FLECHA, FotoAnimal, Huella, Icono } from "./Ilustraciones";

type Animal = AnimalPublicado | Recomendado;
const conPuntaje = (a: Animal): a is Recomendado => "puntaje" in a;
const pct = (v: number) => ({ "--pct": `${v}%` }) as CSSProperties;

function BotonAtras({ alTocar }: { alTocar: () => void }) {
  return <button className="adop-redondo" aria-label="Atrás" onClick={alTocar}><Icono d={FLECHA.izq} /></button>;
}

/** Barra decorativa: el valor ya está escrito al lado (lo lee el lector de pantalla). */
function Barra({ valor }: { valor: number }) {
  return (
    <span className="barra" aria-hidden="true">
      {valor > 0 && <span className="barra-relleno crece" style={pct(valor)} />}
    </span>
  );
}

/** Ocultos = animales del catálogo con una restricción dura para este hogar: no se recomiendan. */
function NotaOcultos({ ocultos, alRevisar }: { ocultos: number; alRevisar: () => void }) {
  if (ocultos <= 0) return null;
  return (
    <p className="adop-nota">
      {ocultos === 1 ? "1 animal no aparece" : `${ocultos} animales no aparecen`} porque necesita
      algo que tu hogar no tiene (patio, o una casa sin niños o sin otros animales).{" "}
      <button className="adop-enlace" onClick={alRevisar}>Revisar mis respuestas</button>
    </p>
  );
}

// ---------- 1 · Bienvenida ----------

export function Bienvenida({ catalogo, cargando, mias, alEmpezar, alVerTodos, alVerSolicitudes }: {
  catalogo: AnimalPublicado[]; cargando: boolean; mias: MiSolicitud[];
  alEmpezar: () => void; alVerTodos: () => void; alVerSolicitudes: () => void;
}) {
  // Primero los que tienen foto; si hay menos de 6, se repiten para llenar el collage.
  const orden = [...catalogo].sort((x, y) => Number(!!y.foto) - Number(!!x.foto));
  const collage = orden.length ? Array.from({ length: 6 }, (_, i) => orden[i % orden.length]) : [];
  const total = catalogo.length;
  return (
    <div className="ini">
      <div className="ini-texto">
        <span className="adop-cinta solo-pc aparece">Refugios de Cúcuta y el área metropolitana</span>
        <h1 className="h ini-titulo aparece" tabIndex={-1} data-titulo>Encuentra a tu compañero peludo</h1>
        <p className="adop-sub aparece d1">
          Responde {PREGUNTAS.length} preguntas rápidas y te mostramos quién combina contigo.
        </p>
        <div className="ini-acciones">
          <button className="adop-boton adop-boton--grande" onClick={alEmpezar}>
            <span className="h">¡Empezar!</span>
            <span className="adop-boton-punta"><Icono d={FLECHA.adelante} /></span>
          </button>
          <button className="adop-enlace" onClick={alVerTodos}>
            {cargando ? "Ver a todos" : `Ver a todos (${total})`}
          </button>
          <button className="adop-enlace adop-enlace--suave" onClick={alVerSolicitudes}>
            Mis solicitudes{mias.length > 0 && ` (${mias.length})`}
          </button>
        </div>
      </div>
      <div className="collage" aria-hidden={collage.length === 0}>
        {cargando && <Cargando que="los animales" />}
        {collage.map((a, i) => (
          <FotoAnimal key={i} a={a} alt={i < 3 ? `Foto de ${a.nombre}` : ""}
            className={`collage-${i + 1} aparece d${i + 1}`} />))}
        {!cargando && (
          <span className="collage-globo flota">
            <Corazon tam={14} className="late" />
            {total === 0 ? "Pronto habrá nuevos amigos" : `${total} te esperan`}
          </span>)}
      </div>
      <Animalitos />
    </div>
  );
}

// ---------- 2 · Mini encuesta ----------

export function Encuesta({ paso, respuestas, catalogo, alResponder, alAtras }: {
  paso: number; respuestas: Respuestas; catalogo: AnimalPublicado[];
  alResponder: (opcion: number) => void; alAtras: () => void;
}) {
  const p = PREGUNTAS[paso];
  const marcada = opcionElegida(p, respuestas);
  const guia = catalogo.length ? catalogo[paso % catalogo.length] : null;
  return (
    <div className="encuesta">
      <div className="encuesta-cabeza">
        <BotonAtras alTocar={alAtras} />
        <ol className="puntos" aria-hidden="true">
          {PREGUNTAS.map((_, i) => (
            <li key={i} className={i < paso ? "hecho" : i === paso ? "ahora" : ""} />))}
        </ol>
        <span className="adop-contador">{paso + 1} de {PREGUNTAS.length}</span>
      </div>
      <div className="encuesta-guia aparece" key={`g${paso}`}>
        <span className="encuesta-foto bambolea">
          {guia ? <FotoAnimal a={guia} /> : <Huella tam={36} color="#E8508A" />}
        </span>
        <span className="globo">{p.burbuja}</span>
      </div>
      <h1 className="h encuesta-pregunta aparece d1" key={`p${paso}`} tabIndex={-1} data-titulo>
        <span className="visualmente-oculto">Pregunta {paso + 1} de {PREGUNTAS.length}: </span>
        {p.texto}
      </h1>
      <div className={`opciones opciones--${p.opciones.length}`} key={`o${paso}`}>
        {p.opciones.map((o, i) => (
          <button key={i} className={`opcion hundible aparece d${i + 1}`} aria-pressed={i === marcada}
            style={{ backgroundColor: o.fondo }} onClick={() => alResponder(i)}>
            <span className="opcion-icono"><Icono d={o.icono} tam={26} grosor={2} /></span>
            <span className="opcion-texto">
              <span className="h opcion-titulo">{o.titulo}</span>
              <span className="opcion-sub">{o.sub}</span>
            </span>
            {i === marcada && <span className="opcion-marca">Tu respuesta</span>}
          </button>))}
      </div>
    </div>
  );
}

// ---------- 3 · ¡Ellos combinan contigo! ----------

export function Combinan({ recomendados, respuestas, cargando, ocultos, total, alVer, alVerTodos, alRepetir }: {
  recomendados: Recomendado[] | null; respuestas: Respuestas; cargando: boolean; ocultos: number;
  total: number; alVer: (a: Recomendado) => void; alVerTodos: () => void; alRepetir: () => void;
}) {
  const { lista, ajustado } = mejores(recomendados ?? [], respuestas);
  return (
    <div className="combinan">
      <span className="adop-cinta aparece">Según tus respuestas</span>
      <h1 className="h combinan-titulo aparece d1" tabIndex={-1} data-titulo>¡Ellos combinan contigo!</h1>
      {cargando ? <Cargando que="quién combina contigo" /> : <>
        <p className="adop-sub">
          {lista.length ? "Toca uno para conocerlo de cerca." : "Por ahora ninguno combina con tu hogar."}
        </p>
        {ajustado && <p className="adop-nota">No hay justo lo que pediste (especie o tamaño): estos
          son los que más combinan con tu hogar.</p>}
        <div className="mejores">
          {lista.map((a, k) => (
            <button key={a.animal_id} className={`mejor hundible aparece d${k + 1}`} onClick={() => alVer(a)}>
              <FotoAnimal a={a} className="mejor-foto" />
              <span className="mejor-datos">
                <span className="mejor-nombre">
                  <span className="h">{a.nombre}</span>
                  {k === 0 && <span className="mejor-insignia">Mejor match</span>}
                </span>
                <span className="mejor-resumen">{resumenCorto(a)}</span>
                <span className="mejor-razon">{razonCorta(a)}</span>
                <span className="mejor-barra">
                  <span className="barra"><span className="barra-relleno crece" style={{
                    ...pct(a.puntaje), backgroundColor: "var(--a-acento)" }} /></span>
                  <span className="h mejor-pct">{a.puntaje}%</span>
                </span>
                {a.alertas.length > 0 && (
                  <span className="mejor-alerta">Para conversar: {a.alertas.join("; ")}.</span>)}
              </span>
            </button>))}
        </div>
        <NotaOcultos ocultos={ocultos} alRevisar={alRepetir} />
        <div className="combinan-pie">
          <button className="adop-enlace" onClick={alVerTodos}>Ver a todos ({total})</button>
          <button className="adop-enlace adop-enlace--suave" onClick={alRepetir}>Repetir encuesta</button>
        </div>
      </>}
    </div>
  );
}

// ---------- 4 · Elige a tu compañero ----------

export function Elegir({ lista, animal, filtro, conteo, ocultos, cargando, conPerfil, aceptaSeguimiento,
  mias, enviando, alFiltrar, alMover, alVer, alElegir, alVerSolicitud, alRevisar, alAtras }: {
  lista: Animal[]; animal: Animal | null; filtro: Filtro; conteo: Record<Filtro, number>;
  ocultos: number; cargando: boolean; conPerfil: boolean; aceptaSeguimiento: boolean;
  mias: MiSolicitud[]; enviando: boolean;
  alFiltrar: (f: Filtro) => void; alMover: (paso: 1 | -1) => void; alVer: (a: Animal) => void;
  alElegir: (a: Animal) => void; alVerSolicitud: (a: Animal) => void; alRevisar: () => void;
  alAtras: () => void;
}) {
  const i = animal ? lista.indexOf(animal) : -1;
  const teclas = (e: KeyboardEvent) => {
    if (e.key === "ArrowLeft") { e.preventDefault(); alMover(-1); }
    if (e.key === "ArrowRight") { e.preventDefault(); alMover(1); }
  };
  const chips: [Filtro, string][] = [["todos", "Todos"], ["perro", "Perritos"], ["gato", "Gatitos"]];
  const suya = animal ? solicitudDe(mias, animal.animal_id) : undefined;
  return (
    <div className="elegir" onKeyDown={teclas}>
      <div className="elegir-cabeza">
        <BotonAtras alTocar={alAtras} />
        <h1 className="h elegir-titulo" tabIndex={-1} data-titulo>Elige a tu compañero</h1>
        <span className="adop-contador" aria-label={i >= 0 ? `${i + 1} de ${lista.length}` : undefined}>
          {i >= 0 ? `${i + 1}/${lista.length}` : ""}</span>
      </div>
      <div className="chips" role="group" aria-label="Mostrar">
        {chips.map(([f, texto]) => (
          <button key={f} className="chip" aria-pressed={filtro === f} onClick={() => alFiltrar(f)}>
            {texto} ({conteo[f]})</button>))}
      </div>
      {cargando && <Cargando que="los animales" />}
      {!cargando && !animal && (
        <p className="ds-vacio adop-vacio"><strong>No hay animales publicados ahora.</strong>{" "}
          El refugio publica animales nuevos con frecuencia: vuelve pronto.</p>)}
      {animal && <>
        <div className="tarjeta-grande aparece" key={animal.animal_id}
          style={{ backgroundColor: fondoDe(animal.animal_id) }}>
          <span className="tarjeta-burbuja rebota">
            <FotoAnimal a={animal} alt={`Foto de ${animal.nombre}`} />
          </span>
          <span className="cinta-nombre"><span className="h">{animal.nombre}</span></span>
          <button className="adop-redondo flecha flecha--izq hundible" aria-label="Anterior"
            onClick={() => alMover(-1)} disabled={lista.length < 2}><Icono d={FLECHA.izq} /></button>
          <button className="adop-redondo flecha flecha--der hundible" aria-label="Siguiente"
            onClick={() => alMover(1)} disabled={lista.length < 2}><Icono d={FLECHA.der} /></button>
          <span className="tarjeta-especie">{especieTexto(animal.especie)}</span>
        </div>
        <div className="elegir-info" aria-live="polite">
          <div className="solo-pc elegir-nombre">
            <span className="h">{animal.nombre}</span>
          </div>
          <p className="elegir-resumen">{resumenCorto(animal)}</p>
          <div className="insignias">
            {insignias(animal).map((t, k) => <span key={t} className={`insignia insignia--${k}`}>{t}</span>)}
          </div>
          <p className="elegir-desc">{animal.descripcion}</p>
          <ul className="stats">
            {estadisticas(animal).map((e) => (
              <li key={e.etiqueta} className="stat">
                <span className="stat-nombre">{e.etiqueta}</span><span className="stat-valor">{e.texto}</span>
                <Barra valor={e.valor} />
              </li>))}
          </ul>
          {conPuntaje(animal) && animal.restricciones.length > 0 && (
            <p className="adop-alerta adop-alerta--dura" role="note">
              El refugio no podría aprobar esta adopción: {animal.restricciones.join("; ")}.</p>)}
          {conPuntaje(animal) && animal.alertas.length > 0 && (
            <p className="adop-alerta" role="note">Para conversar con el refugio: {animal.alertas.join("; ")}.</p>)}
          <HoyYAdulto a={animal} />
          {abierta(suya)
            ? <button className="adop-boton" onClick={() => alVerSolicitud(animal)}>
                <span className="h">Ver mi solicitud por {animal.nombre}</span>
                <span className="adop-boton-punta adop-boton-punta--rosa"><Corazon /></span></button>
            : <button className="adop-boton" disabled={enviando} onClick={() => alElegir(animal)}>
                <span className="h">{enviando ? "Enviando…" : `¡Te elijo, ${animal.nombre}!`}</span>
                <span className="adop-boton-punta adop-boton-punta--rosa anillo"><Corazon className="late" /></span>
              </button>}
          {!conPerfil && <p className="adop-nota">Para solicitar, primero cuéntanos de tu hogar
            ({PREGUNTAS.length} preguntas).</p>}
          {conPerfil && !aceptaSeguimiento && (
            <p className="adop-nota">Para solicitar debes aceptar las visitas o llamadas del refugio.{" "}
              <button className="adop-enlace" onClick={alRevisar}>Cambiar mi respuesta</button></p>)}
        </div>
        <div className="miniaturas" role="group" aria-label="Todos los animales">
          {lista.map((a) => (
            <button key={a.animal_id} className={`miniatura${a === animal ? " miniatura--activa anillo" : ""}`}
              aria-label={`Ver a ${a.nombre}`} aria-pressed={a === animal} onClick={() => alVer(a)}>
              <FotoAnimal a={a} />
            </button>))}
        </div>
      </>}
      <NotaOcultos ocultos={ocultos} alRevisar={alRevisar} />
    </div>
  );
}

function HoyYAdulto({ a }: { a: AnimalPublicado }) {
  const { hoy, adulto } = hoyYAdulto(a);
  return (
    <div className="hoy-adulto">
      <FotoAnimal a={a} className="hoy-foto" />
      <span className="hoy-texto"><span>Hoy</span><span>{hoy}</span></span>
      <svg width="34" height="16" viewBox="0 0 34 16" fill="none" stroke="currentColor" strokeWidth="2.4"
        strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M2 8h28M24 2l6 6-6 6" /></svg>
      <FotoAnimal a={a} className="hoy-foto hoy-foto--adulto" />
      <span className="hoy-texto"><span>De adulto</span><span>{adulto}</span></span>
    </div>
  );
}

// ---------- 5 · ¡Lo elegiste! ----------

export function Listo({ animal, solicitud, recien, alDescargar, alInicio, alSolicitudes }: {
  animal: AnimalPublicado; solicitud?: MiSolicitud; recien: boolean;
  alDescargar: (id: number) => void; alInicio: () => void; alSolicitudes: () => void;
}) {
  const estado = solicitud?.estado ?? "pendiente";
  const festeja = estado !== "rechazada" && estado !== "devuelta";
  return (
    <div className="listo">
      {recien && festeja && <Confeti />}
      <span className="adop-cinta aparece">{recien ? "¡Nuevo compañero!" : ESTADO_SOLICITUD[estado] ?? estado}</span>
      <div className="listo-foto aparece d1">
        <span className="listo-anillo anillo" style={{ backgroundColor: fondoDe(animal.animal_id) }} />
        <span className="listo-burbuja rebota"><FotoAnimal a={animal} alt={`Foto de ${animal.nombre}`} /></span>
        {festeja && <Corazon tam={44} className="listo-corazon late" />}
      </div>
      <h1 className="h listo-titulo aparece d2" tabIndex={-1} data-titulo>
        {festeja ? `¡${animal.nombre} y tú, gran equipo!` : `Tu solicitud por ${animal.nombre}`}
      </h1>
      <p className="adop-sub aparece d3">
        {recien ? "Enviamos tu solicitud al refugio. Aquí y en «Mis solicitudes» verás cuándo la revisen."
          : "Así va tu solicitud."}
      </p>
      <ol className="pasos">
        {pasosSolicitud(estado).map((p, n) => (
          <li key={p.titulo} className={`paso paso--${p.estado}`}>
            <span className="h paso-numero">{p.estado === "hecho" ? "✓" : n + 1}</span>
            <span><strong>{p.titulo}</strong><span>{p.detalle}</span></span>
          </li>))}
      </ol>
      {solicitud?.estado === "aprobada" && (
        <button className="adop-boton" onClick={() => alDescargar(solicitud.id)}>
          <span className="h">Descargar compromiso (PDF)</span>
          <span className="adop-boton-punta"><Icono d="M12 4v11M7 10l5 5 5-5M5 20h14" /></span>
        </button>)}
      <div className="listo-pie">
        <button className="adop-boton adop-boton--claro" onClick={alSolicitudes}><span className="h">Mis solicitudes</span></button>
        <button className="adop-enlace" onClick={alInicio}>Volver al inicio</button>
      </div>
    </div>
  );
}

// ---------- Mis solicitudes ----------

export function MisSolicitudes({ mias, animalDe, alVer, alDescargar, alAtras, alVerTodos }: {
  mias: MiSolicitud[]; animalDe: (id: number) => AnimalPublicado;
  alVer: (s: MiSolicitud) => void; alDescargar: (id: number) => void; alAtras: () => void;
  alVerTodos: () => void;
}) {
  const orden = [...mias].sort((x, y) => y.creada_en.localeCompare(x.creada_en));
  return (
    <div className="solicitudes">
      <div className="elegir-cabeza">
        <BotonAtras alTocar={alAtras} />
        <h1 className="h elegir-titulo" tabIndex={-1} data-titulo>Mis solicitudes</h1>
        <span className="adop-contador" />
      </div>
      {mias.length === 0 && (
        <p className="ds-vacio adop-vacio"><strong>Aún no has hecho solicitudes.</strong>{" "}
          Elige a tu compañero y toca «¡Te elijo!».{" "}
          <button className="adop-enlace" onClick={alVerTodos}>Ver a todos</button></p>)}
      <ul className="solicitudes-lista">
        {orden.map((s) => {
          const a = animalDe(s.animal_id);
          return (
            <li key={s.id} className="solicitud">
              <FotoAnimal a={a} className="solicitud-foto" />
              <span className="solicitud-datos">
                <span className="h">{a.nombre}</span>
                <span className={`estado estado--${s.estado}`}>{ESTADO_SOLICITUD[s.estado] ?? s.estado}</span>
              </span>
              <span className="solicitud-acciones">
                <button className="adop-boton adop-boton--claro adop-boton--chico" onClick={() => alVer(s)}>Ver pasos</button>
                {s.estado === "aprobada" && (
                  <button className="adop-boton adop-boton--chico" onClick={() => alDescargar(s.id)}>
                    Descargar compromiso (PDF)</button>)}
              </span>
            </li>);
        })}
      </ul>
    </div>
  );
}
