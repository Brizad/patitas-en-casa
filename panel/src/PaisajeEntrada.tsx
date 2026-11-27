// Fondo de la entrada del adoptante (#482), como docs/prototipo/referencias/vista-previa-adoptar-fondo.png:
// hojas en las esquinas de arriba (detrás de todo) y, abajo, la foto completa de dos gatitos asomados
// al muro (#484: nítida, sin recortes), con los bordes fundidos en el crema. Solo adorno: oculto al lector, sin texto alternativo, sin eventos y
// con carga diferida. La franja va en el flujo, después del contenido: si la pantalla es bajita, baja.
import gatos from "./img/entrada/gatos-muro.jpg";
import gatosW from "./img/entrada/gatos-muro.webp";
import hojasDer from "./img/entrada/hojas-der.png";
import hojasDerW from "./img/entrada/hojas-der.webp";
import hojasIzq from "./img/entrada/hojas-izq.png";
import hojasIzqW from "./img/entrada/hojas-izq.webp";

const HOJAS = [["izq", hojasIzqW, hojasIzq], ["der", hojasDerW, hojasDer]] as const;

export default function PaisajeEntrada() {
  return (
    <>
      <div className="paisaje paisaje-arriba" aria-hidden="true">
        {HOJAS.map(([lado, webp, png]) => (
          <picture key={lado}><source srcSet={webp} type="image/webp" />
            <img className={`paisaje-hojas paisaje-hojas--${lado}`} src={png} alt="" width={620} height={330}
              loading="lazy" decoding="async" /></picture>))}
      </div>
      <div className="paisaje paisaje-franja" aria-hidden="true">
        <picture><source srcSet={gatosW} type="image/webp" />
          <img src={gatos} alt="" width={1200} height={675} loading="lazy" decoding="async" /></picture>
      </div>
    </>
  );
}
