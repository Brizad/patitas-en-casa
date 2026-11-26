import Lottie from "./Lottie";

/** #400: mientras llegan los datos se dice, en vez de dejar la tarjeta vacía (con Render
 *  despertando puede tardar hasta un minuto). role="status": el lector de pantalla lo anuncia.
 *  #467: huellitas de Lottie en lugar del círculo que gira (que queda de respaldo). */
export default function Cargando({ que }: { que: string }) {
  return (
    <p className="ds-cargando" role="status">
      <Lottie nombre="huellas-cargando" className="cargando-huellas" respaldo={<span className="ds-giro" />} />
      Cargando {que}…
    </p>
  );
}
