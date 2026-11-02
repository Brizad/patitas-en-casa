import { useEffect, useState } from "react";
import { ErrorApi, pedir } from "./api";
import { nombreIndicador, plural, textoError } from "./mensajes";

// RF-30, RF-31, RF-32 (#102): indicadores, exportar y (administrador) la bitácora.
type Conteo = Record<string, number>;
interface Datos {
  reportes: { total: number; por_estado: Conteo; por_prioridad_confirmada: Conteo;
    minutos_hasta_confirmar: { mediana: number | null; promedio: number | null };
    acuerdo_por_version_modelo: Record<string, { decisiones: number;
      confirmadas_sin_cambio: number }>;
    tiempos_por_prioridad: Record<string, { mediana_minutos_hasta_confirmar: number | null;
      mediana_minutos_hasta_aceptar_rescate: number | null }> };
  rescates: { por_resultado: Conteo };
  refugios: { nombre: string; ocupados: number; capacidad: number; porcentaje: number }[];
  adopciones: { aprobadas: number; devoluciones: number; seguimientos: Conteo;
    tasa_recomendacion_por_segmento: Record<string, { perfiles: number;
      tasa_recomendacion: number }> };
}
interface Evento {
  momento: string; actor: string; accion: string; objeto: Conteo;
  valor_anterior: Record<string, unknown> | null; valor_nuevo: Record<string, unknown> | null;
}

/** RNF-12: «prioridad: media → alta». */
function cambio(e: Evento): string {
  if (!e.valor_nuevo) return "";
  return Object.entries(e.valor_nuevo).map(([k, v]) => {
    const antes = e.valor_anterior?.[k];
    return `${k}: ${antes === undefined ? "" : `${String(antes)} → `}${String(v)}`;
  }).join("; ");
}

/** Barras en CSS: sin librerías de gráficos (CSP 'self' y paquete pequeño, RNF-07). */
function Barras({ titulo, datos }: { titulo: string; datos: Conteo }) {
  const maximo = Math.max(1, ...Object.values(datos));
  return (
    <div><h3>{titulo}</h3>
      {Object.keys(datos).length === 0 ? <p className="ds-vacio">Sin datos.</p> : (
        <dl className="barras">{Object.entries(datos).map(([k, v]) => (
          <div key={k}><dt>{nombreIndicador(k)}</dt><dd><span style={{ width: `${(v / maximo) * 100}%` }} />
            {v}</dd></div>))}</dl>)}
    </div>
  );
}

async function descargar(token: string, ruta: string, nombre: string) {
  const r = await fetch(ruta, { headers: { Authorization: `Bearer ${token}` } });
  if (!r.ok) throw new ErrorApi(r.status, "No se pudo descargar.");
  const url = URL.createObjectURL(await r.blob());
  Object.assign(document.createElement("a"), { href: url, download: nombre }).click();
  URL.revokeObjectURL(url);
}

export default function Indicadores({ token, rol }: { token: string; rol: string }) {
  const [datos, setDatos] = useState<Datos | null>(null);
  const [eventos, setEventos] = useState<Evento[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    pedir<Datos>("/indicadores", {}, token).then(setDatos).catch((e) => setError(textoError(e)));
    if (rol === "administrador") {
      pedir<Evento[]>("/bitacora?limite=50", {}, token).then(setEventos)
        .catch((e) => setError(textoError(e)));
    }
  }, [token, rol]);

  const bajar = (ruta: string, nombre: string) =>
    descargar(token, ruta, nombre).catch((e) => setError(textoError(e)));
  return (
    <section className="pagina">
      {error && <p className="ds-msg ds-msg--error" role="alert">{error}</p>}
      <div className="ds-tarjeta">
        <div className="fila-titulo"><h2>Indicadores</h2>
          <div className="acciones">
            <button onClick={() => void bajar("/indicadores/reportes.csv", "reportes.csv")}>
              Exportar CSV</button>
            <button onClick={() => void bajar("/indicadores/resumen.pdf", "indicadores.pdf")}>
              Exportar PDF</button>
            {rol !== "alcaldia" && (
              <button onClick={() => void bajar("/indicadores/fichas.csv", "fichas.csv")}>
                Fichas CSV</button>)}</div></div>
        <p className="ds-suave">Anonimizados: sin nombres, direcciones, correos ni códigos (RF-31).</p>
        {datos && (<>
          <dl className="kpis">
            {([["Reportes", datos.reportes.total],
              ["Minutos hasta confirmar (mediana)", datos.reportes.minutos_hasta_confirmar.mediana ?? "—"],
              ["Adopciones aprobadas", datos.adopciones.aprobadas],
              ["Devoluciones", datos.adopciones.devoluciones]] as [string, number | string][]).map(([t, v]) => (
              <div key={t} className="kpi"><dd>{v}</dd><dt>{t}</dt></div>))}
          </dl>
          <h3>Tiempo de respuesta por prioridad (mediana, minutos)</h3>
          <ul className="lista-simple">{Object.entries(datos.reportes.tiempos_por_prioridad).map(([p, t]) => (
            <li key={p}><span className={`ds-insignia ds-insignia--${p}`}>{nombreIndicador(p)}</span>
              {" "}confirmar {t.mediana_minutos_hasta_confirmar ?? "—"} · el rescatista
              acepta {t.mediana_minutos_hasta_aceptar_rescate ?? "—"}</li>))}</ul>
          <Barras titulo="Reportes por estado" datos={datos.reportes.por_estado} />
          <Barras titulo="Prioridad confirmada" datos={datos.reportes.por_prioridad_confirmada} />
          <Barras titulo="Resultado de los rescates" datos={datos.rescates.por_resultado} />
          <Barras titulo="Seguimientos de adopción" datos={datos.adopciones.seguimientos} />
          <h3>Acuerdo del veterinario con cada versión del modelo (RF-20)</h3>
          <ul>{Object.entries(datos.reportes.acuerdo_por_version_modelo).map(([v, a]) => (
            <li key={v}>{v}: {Math.round(a.confirmadas_sin_cambio * 100)} % sin cambio en{" "}
              {plural(a.decisiones, "decisión", "decisiones")}</li>))}</ul>
          <h3>Recomendación por tipo de hogar (RNF-16)</h3>
          <p className="ds-suave">Qué parte del catálogo se le recomienda, en promedio, a cada grupo.
            Una diferencia grande es una señal para revisar los pesos.</p>
          <ul>{Object.entries(datos.adopciones.tasa_recomendacion_por_segmento).map(([s, t]) => (
            <li key={s}>{nombreIndicador(s)}: {Math.round(t.tasa_recomendacion * 100)} % ({plural(t.perfiles, "perfil", "perfiles")})
            </li>))}</ul>
          <h3>Ocupación</h3>
          <ul>{datos.refugios.map((r) => (
            <li key={r.nombre}>{r.nombre}: {r.ocupados}/{r.capacidad} ({r.porcentaje} %)</li>))}
          </ul></>)}
      </div>
      {rol === "administrador" && (
        <div className="ds-tarjeta">
          <h2>Bitácora (últimos 50 cambios)</h2>
          <p className="ds-suave">Inmutable: no se puede editar ni borrar (RF-32).</p>
          <div className="ds-tabla-caja"><table className="ds-tabla"><thead><tr><th>Cuándo</th><th>Quién</th><th>Qué</th><th>Antes → después</th></tr>
          </thead><tbody>{eventos.map((e, i) => (
            <tr key={i}><td>{new Date(e.momento).toLocaleString()}</td><td>{e.actor}</td>
              <td><code>{e.accion}</code> {Object.values(e.objeto).join(", ")}</td>
              <td>{cambio(e)}</td></tr>))}
          </tbody></table></div>
        </div>)}
    </section>
  );
}
