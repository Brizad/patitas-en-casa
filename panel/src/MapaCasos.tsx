// Mapa de los casos disponibles del rescatista (#496): un punto por caso con el color de su
// prioridad y el punto elegido resaltado. Los puntos de las ofertas son aproximados (~110 m): la
// dirección exacta se ve al aceptar. Mismo Leaflet y teselas que MiniMapa (#430, #442).
import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Nivel, Punto } from "./bandejas";

const TESELAS = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const ATRIBUCION = '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
const CUCUTA: [number, number] = [7.8939, -72.5078];
export const COLOR_NIVEL: Record<Nivel, string> = { urgente: "#E8508A", alta: "#FFD23F", normal: "#D7F0DC" };

export interface CasoEnMapa { codigo: string; nivel: Nivel; latitud: number | null; longitud: number | null }

export default function MapaCasos({ casos, elegido, yo, alElegir }: {
  casos: CasoEnMapa[]; elegido: string | null; yo: Punto | null; alElegir: (codigo: string) => void;
}) {
  const caja = useRef<HTMLDivElement>(null);
  const mapa = useRef<L.Map | null>(null);
  const capa = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    if (!caja.current) return;
    const m = L.map(caja.current, { center: CUCUTA, zoom: 13, scrollWheelZoom: false });
    m.attributionControl.setPrefix(false);
    // OSM bloquea las teselas sin Referer; solo ellas envían el origen (#442).
    L.tileLayer(TESELAS, { maxZoom: 19, attribution: ATRIBUCION,
      referrerPolicy: "strict-origin-when-cross-origin" }).addTo(m);
    mapa.current = m;
    capa.current = L.layerGroup().addTo(m);
    return () => { m.remove(); mapa.current = null; };
  }, []);

  useEffect(() => {
    const m = mapa.current;
    const grupo = capa.current;
    if (!m || !grupo) return;
    grupo.clearLayers();
    const puntos: L.LatLngExpression[] = [];
    for (const c of casos) {
      if (c.latitud === null || c.longitud === null) continue;
      const activo = c.codigo === elegido;
      L.circleMarker([c.latitud, c.longitud], {
        radius: activo ? 13 : 8, color: "#2B2340", weight: activo ? 4 : 2,
        fillColor: COLOR_NIVEL[c.nivel], fillOpacity: 1,
      }).on("click", () => alElegir(c.codigo)).bindTooltip(c.codigo).addTo(grupo);
      puntos.push([c.latitud, c.longitud]);
    }
    if (yo) {
      L.circleMarker([yo.latitud, yo.longitud], { radius: 7, color: "#FFFFFF", weight: 3,
        fillColor: "#7A5AF8", fillOpacity: 1 }).bindTooltip("Tú").addTo(grupo);
      puntos.push([yo.latitud, yo.longitud]);
    }
    if (puntos.length > 1) m.fitBounds(L.latLngBounds(puntos), { padding: [24, 24], maxZoom: 15 });
    else if (puntos.length === 1) m.setView(puntos[0], 15);
    m.invalidateSize();
  }, [casos, elegido, yo, alElegir]);

  return <div ref={caja} className="mapa-casos" role="region"
    aria-label="Mapa de los casos disponibles: puntos de color según la prioridad" />;
}
