// Fondo de la entrada del adoptante (#482), como docs/prototipo/referencias/vista-previa-adoptar-fondo.png:
// hojas en las esquinas de arriba (detrás de todo) y, abajo, una franja con dos gatitos asomados al
// muro que se funde con el crema. Solo adorno: oculto al lector, sin texto alternativo, sin eventos y
// con carga diferida. La franja va en el flujo, después del contenido: si la pantalla es bajita, baja.
import gatos960 from "./img/entrada/gatos-muro-960.jpg";
import gatos960w from "./img/entrada/gatos-muro-960.webp";
import gatos1920 from "./img/entrada/gatos-muro-1920.jpg";
import gatos1920w from "./img/entrada/gatos-muro-1920.webp";
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
        <picture><source srcSet={`${gatos960w} 960w, ${gatos1920w} 1920w`} sizes="100vw" type="image/webp" />
          <img src={gatos1920} srcSet={`${gatos960} 960w, ${gatos1920} 1920w`} sizes="100vw" alt="" width={1920}
            height={1080} loading="lazy" decoding="async" /></picture>
      </div>
    </>
  );
}
