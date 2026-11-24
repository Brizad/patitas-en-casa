/** #400: mientras llegan los datos se dice, en vez de dejar la tarjeta vacía (con Render
 *  despertando puede tardar hasta un minuto). role="status": el lector de pantalla lo anuncia. */
export default function Cargando({ que }: { que: string }) {
  return (
    <p className="ds-cargando" role="status">
      <span className="ds-giro" aria-hidden="true" />Cargando {que}…
    </p>
  );
}
