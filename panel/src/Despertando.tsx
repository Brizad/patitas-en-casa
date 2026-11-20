import { useEffect, useState } from "react";
import { alCambiarEspera } from "./api";

/** El plan gratis de Render se duerme: la primera petición puede tardar hasta un minuto. Este
 *  aviso aparece cuando una petición lleva más de 4 segundos y se va al llegar la respuesta. */
export default function Despertando() {
  const [lentas, setLentas] = useState(0);
  useEffect(() => alCambiarEspera(setLentas), []);
  if (lentas === 0) return null;
  return (
    <p className="ds-msg ds-msg--aviso" role="status">
      El servidor está despertando: puede tardar hasta un minuto. No cierres esta página.
    </p>
  );
}
