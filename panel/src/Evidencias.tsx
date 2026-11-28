// #504: fotos de evidencia del personal. Nunca tienen URL pública: FotoPrivada las pide con la
// sesión y las muestra como blob; Galeria las amplía al hacer clic (Esc o el botón cierran).
import { useEffect, useState } from "react";
import { fotoConSesion } from "./fotos";
import { fechaExacta } from "./bandejas";
import {
  InformeEnviado, NOMBRE_ENCONTRADO, NOMBRE_ESTADO_ANIMAL, NOMBRE_RESULTADO,
} from "./apiRescatista";

export function FotoPrivada({ token, url, alt, className }: {
  token: string; url: string; alt: string; className?: string;
}) {
  const [src, setSrc] = useState<string | null>(null);
  const [falla, setFalla] = useState(false);
  useEffect(() => {
    let vivo = true;
    let creada: string | null = null;
    fotoConSesion(token, url).then((u) => { creada = u; if (vivo) setSrc(u); else URL.revokeObjectURL(u); })
      .catch(() => { if (vivo) setFalla(true); });
    return () => { vivo = false; if (creada) URL.revokeObjectURL(creada); };
  }, [token, url]);
  if (falla) return <span className={`${className ?? ""} foto-falla`}>Sin foto</span>;
  if (!src) return <span className={`${className ?? ""} foto-cargando`} aria-label="Cargando foto" />;
  return <img className={className} src={src} alt={alt} />;
}

export function Galeria({ token, fotos, codigo }: {
  token: string; fotos: { id: number; url: string }[]; codigo: string;
}) {
  const [abierta, setAbierta] = useState<string | null>(null);
  useEffect(() => {
    if (!abierta) return;
    const alTeclear = (e: KeyboardEvent) => { if (e.key === "Escape") setAbierta(null); };
    window.addEventListener("keydown", alTeclear);
    return () => window.removeEventListener("keydown", alTeclear);
  }, [abierta]);
  if (fotos.length === 0) return <p className="ds-suave">Sin fotos (el animal no estaba en el lugar).</p>;
  return (
    <>
      <ul className="galeria">
        {fotos.map((f, i) => (
          <li key={f.id}>
            <button className="galeria-foto" aria-label={`Ampliar la foto ${i + 1} del caso ${codigo}`}
              onClick={() => setAbierta(f.url)}>
              <FotoPrivada token={token} url={f.url} alt={`Foto de evidencia ${i + 1} del caso ${codigo}`} />
            </button>
          </li>))}
      </ul>
      {abierta && (
        <div className="foto-ampliada" role="dialog" aria-modal="true" aria-label="Foto ampliada"
          onClick={() => setAbierta(null)}>
          <FotoPrivada token={token} url={abierta} alt="Foto de evidencia ampliada" />
          <button className="principal" onClick={() => setAbierta(null)}>Cerrar</button>
        </div>)}
    </>
  );
}

/** El informe completo para el veterinario y el coordinador (el ciudadano nunca lo ve). */
export function InformeDeRescate({ token, informe }: { token: string; informe: InformeEnviado }) {
  return (
    <article className="informe-rescate ds-tarjeta">
      <div className="fila-titulo">
        <h3>Informe de rescate <code>{informe.codigo}</code></h3>
        <span className="ds-insignia ds-insignia--info">{NOMBRE_RESULTADO[informe.resultado]}</span>
      </div>
      <dl className="informe-datos">
        <dt>¿Lo encontró?</dt><dd>{NOMBRE_ENCONTRADO[informe.encontrado]}</dd>
        <dt>Estado del animal</dt>
        <dd>{informe.estados.length ? informe.estados.map((e) => NOMBRE_ESTADO_ANIMAL[e]).join(", ") : "—"}</dd>
        {informe.motivo && <><dt>Por qué no se pudo</dt><dd>{informe.motivo}</dd></>}
        <dt>Nota</dt><dd>{informe.nota ?? "—"}</dd>
        <dt>Hora</dt><dd>{fechaExacta(informe.creado_en)}</dd>
        <dt>Rescatista</dt><dd>{informe.rescatista}</dd>
      </dl>
      <Galeria token={token} fotos={informe.fotos} codigo={informe.codigo} />
    </article>
  );
}
