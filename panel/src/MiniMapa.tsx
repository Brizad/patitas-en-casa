// Mini mapa del lugar del reporte (#430) para el veterinario y el rescatista que aceptó. Leaflet
// empaquetado por Vite (se sirve desde /panel/assets) y teselas de OpenStreetMap (la CSP solo
// admite ese servidor y solo para imágenes). Si las teselas no cargan, quedan el texto y los
// enlaces a Google Maps; el mapa nunca es la única forma de saber dónde es.
import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import icono from "leaflet/dist/images/marker-icon.png";
import icono2x from "leaflet/dist/images/marker-icon-2x.png";
import sombra from "leaflet/dist/images/marker-shadow.png";
import { enlaceComoLlegar, enlaceMapa } from "./mensajes";

const TESELAS = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const ATRIBUCION = '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
// Con un bundler, Leaflet no encuentra solo las imágenes del pin: se le dan.
const PIN = L.icon({ iconUrl: icono, iconRetinaUrl: icono2x, shadowUrl: sombra,
  iconSize: [25, 41], iconAnchor: [12, 41], shadowSize: [41, 41] });

export default function MiniMapa({ latitud, longitud }: { latitud: number; longitud: number }) {
  const caja = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!caja.current) return;
    const mapa = L.map(caja.current, { center: [latitud, longitud], zoom: 16, scrollWheelZoom: false });
    mapa.attributionControl.setPrefix(false);
    // OSM bloquea las teselas sin Referer; solo ellas envían el origen (la página sigue sin Referer).
    L.tileLayer(TESELAS, { maxZoom: 19, attribution: ATRIBUCION,
      referrerPolicy: "strict-origin-when-cross-origin" }).addTo(mapa);
    L.marker([latitud, longitud], { icon: PIN, keyboard: false, title: "Lugar del reporte",
      alt: "Pin del lugar del reporte" }).addTo(mapa);
    return () => { mapa.remove(); };
  }, [latitud, longitud]);
  return <div ref={caja} className="mini-mapa" role="region" aria-label="Mapa con el lugar del reporte" />;
}

type Ubicacion = { latitud: number | null; longitud: number | null; direccion: string | null };

/** Mini mapa (solo si hay GPS) y los botones «Abrir en Google Maps» y «Cómo llegar». */
export function Lugar({ u }: { u: Ubicacion }) {
  const abrir = enlaceMapa(u);
  const llegar = enlaceComoLlegar(u);
  return (
    <div className="lugar">
      {u.latitud !== null && u.longitud !== null && <MiniMapa latitud={u.latitud} longitud={u.longitud} />}
      {(abrir || llegar) && (
        <p className="acciones lugar-enlaces">
          {abrir && <a className="ds-btn ds-btn--chico" href={abrir} target="_blank"
            rel="noopener noreferrer">Abrir en Google Maps</a>}
          {llegar && <a className="ds-btn ds-btn--chico" href={llegar} target="_blank"
            rel="noopener noreferrer">Cómo llegar</a>}
        </p>)}
    </div>
  );
}
