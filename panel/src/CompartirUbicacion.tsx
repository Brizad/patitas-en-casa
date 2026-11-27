// #498: el rescatista en camino comparte su ubicación para que el ciudadano lo vea en el mapa.
// Con consentimiento expreso (Ley 1581 de 2012). Mientras comparte, watchPosition da muchas
// posiciones y se envía una cada 12 s; al dejar de estar «en camino» este componente se desmonta
// y deja de leer la ubicación (el servidor, además, borra la posición guardada).
import { useEffect, useRef, useState } from "react";
import { compartirUbicacion, dejarDeCompartir, tocaEnviar } from "./apiRescatista";
import { textoError } from "./mensajes";

export default function CompartirUbicacion({ token, codigo }: { token: string; codigo: string }) {
  const [acepta, setAcepta] = useState(false);
  const [compartiendo, setCompartiendo] = useState(false);
  const [error, setError] = useState("");
  const vigilancia = useRef<number | null>(null);
  const ultimo = useRef<number | null>(null);

  function parar() {
    if (vigilancia.current !== null) navigator.geolocation.clearWatch(vigilancia.current);
    vigilancia.current = null;
    ultimo.current = null;
    setCompartiendo(false);
  }

  useEffect(() => () => {
    if (vigilancia.current !== null) navigator.geolocation.clearWatch(vigilancia.current);
  }, []);

  function empezar() {
    if (!("geolocation" in navigator)) {
      setError("Este navegador no puede leer tu ubicación.");
      return;
    }
    setError("");
    setCompartiendo(true);
    vigilancia.current = navigator.geolocation.watchPosition((p) => {
      const ahora = Date.now();
      if (!tocaEnviar(ultimo.current, ahora)) return;
      ultimo.current = ahora;
      compartirUbicacion(token, codigo, p.coords.latitude, p.coords.longitude).catch((e) => {
        setError(textoError(e));
        parar(); // ya no va en camino o el caso no es suyo: se deja de leer la ubicación
      });
    }, () => {
      setError("No pudimos leer tu ubicación. Revisa el permiso de ubicación del navegador.");
      parar();
    }, { enableHighAccuracy: true, maximumAge: 10_000, timeout: 30_000 });
  }

  async function dejar() {
    parar();
    try {
      await dejarDeCompartir(token, codigo);
    } catch (e) {
      setError(textoError(e));
    }
  }

  return (
    <div className="compartir-ubicacion">
      <h3>Compartir mi ubicación mientras voy en camino</h3>
      {compartiendo ? (
        <>
          <p className="compartiendo"><span className="punto-vivo" aria-hidden="true" />
            Compartiendo tu ubicación con quien reportó el caso.</p>
          <p className="ds-msg aviso-abierta">Mantén la app abierta mientras vas en camino.</p>
          <button onClick={() => void dejar()}>Dejar de compartir</button>
        </>
      ) : (
        <>
          <p className="ds-suave">Quien reportó verá en un mapa por dónde vas y cuánto falta, con tu
            nombre de pila y la posición aproximada (unos 50 m). Nunca tu teléfono ni tu correo. Se
            deja de compartir al llegar o al atender el caso, y la posición se borra.</p>
          <label className="en-linea">
            <input type="checkbox" checked={acepta} onChange={(e) => setAcepta(e.target.checked)} />
            Autorizo compartir mi ubicación solo durante este rescate (Ley 1581 de 2012).</label>
          <button className="principal" disabled={!acepta} onClick={empezar}>Compartir mi ubicación</button>
        </>)}
      {error && <p className="ds-msg ds-msg--error" role="alert">{error}</p>}
    </div>
  );
}
