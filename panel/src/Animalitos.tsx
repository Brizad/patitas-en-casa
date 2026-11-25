// Animalitos que caminan por la parte de abajo de la bienvenida (#420): un perro, un gato y un
// cachorro en SVG, movidos solo con CSS (adoptante.css: .paseante, .pata-a, .pata-b, .cola-mueve).
//
// PENDIENTE (Lottie): cuando lleguen los archivos JSON de LottieFiles, se cambia solo el
// contenido de <Animalitos>: el carril (.carril) ya tiene su alto, es decorativo (aria-hidden),
// no recibe toques y se detiene con «Movimiento» apagado o prefers-reduced-motion. Lo único
// que hay que respetar es pausar la animación cuando el contenedor .adop lleva .adop--quieto.

function Perro() {
  return (
    <svg className="paseante paseante--perro" width="96" height="64" viewBox="0 0 96 64">
      <path className="cola-mueve" d="M20 26 q-10 -10 -14 -2" stroke="#C98A4B" strokeWidth="5" fill="none" strokeLinecap="round" />
      <rect className="pata-a" x="26" y="36" width="7" height="18" rx="3.5" fill="#B9773D" />
      <rect className="pata-b" x="36" y="36" width="7" height="18" rx="3.5" fill="#C98A4B" />
      <rect className="pata-b" x="54" y="36" width="7" height="18" rx="3.5" fill="#B9773D" />
      <rect className="pata-a" x="63" y="36" width="7" height="18" rx="3.5" fill="#C98A4B" />
      <ellipse cx="46" cy="32" rx="27" ry="13" fill="#E3A866" stroke="#2B2340" strokeWidth="2" />
      <circle cx="74" cy="20" r="13" fill="#E3A866" stroke="#2B2340" strokeWidth="2" />
      <ellipse cx="68" cy="13" rx="5" ry="9" fill="#8A5428" transform="rotate(-25 68 13)" />
      <circle cx="78" cy="18" r="2.2" fill="#2B2340" />
      <ellipse cx="86" cy="23" rx="3" ry="2.4" fill="#2B2340" />
      <path d="M80 27 q4 3 7 0" stroke="#2B2340" strokeWidth="1.6" fill="none" />
    </svg>
  );
}

function Gato() {
  return (
    <svg className="paseante paseante--gato" width="80" height="56" viewBox="0 0 80 56">
      <path className="cola-mueve" d="M14 24 q-12 -18 2 -20" stroke="#8C8FA3" strokeWidth="5" fill="none" strokeLinecap="round" />
      <rect className="pata-a" x="20" y="32" width="6" height="16" rx="3" fill="#6F7287" />
      <rect className="pata-b" x="29" y="32" width="6" height="16" rx="3" fill="#8C8FA3" />
      <rect className="pata-b" x="44" y="32" width="6" height="16" rx="3" fill="#6F7287" />
      <rect className="pata-a" x="52" y="32" width="6" height="16" rx="3" fill="#8C8FA3" />
      <ellipse cx="38" cy="29" rx="23" ry="10" fill="#A4A7B8" stroke="#2B2340" strokeWidth="2" />
      <circle cx="62" cy="19" r="11" fill="#A4A7B8" stroke="#2B2340" strokeWidth="2" />
      <path d="M54 12 l2 -10 l6 7 z M64 9 l6 -7 l2 10 z" fill="#A4A7B8" stroke="#2B2340" strokeWidth="2" strokeLinejoin="round" />
      <circle cx="66" cy="18" r="2" fill="#2B2340" />
      <circle cx="72" cy="22" r="1.6" fill="#E8508A" />
    </svg>
  );
}

function Cachorro() {
  return (
    <svg className="paseante paseante--cachorro" width="64" height="46" viewBox="0 0 64 46">
      <path className="cola-mueve" d="M12 18 q-8 -10 -10 -1" stroke="#2B2340" strokeWidth="4" fill="none" strokeLinecap="round" />
      <rect className="pata-a" x="16" y="26" width="5" height="13" rx="2.5" fill="#3A3350" />
      <rect className="pata-b" x="23" y="26" width="5" height="13" rx="2.5" fill="#FFFFFF" stroke="#2B2340" />
      <rect className="pata-b" x="35" y="26" width="5" height="13" rx="2.5" fill="#3A3350" />
      <rect className="pata-a" x="41" y="26" width="5" height="13" rx="2.5" fill="#FFFFFF" stroke="#2B2340" />
      <ellipse cx="30" cy="23" rx="18" ry="9" fill="#FFFFFF" stroke="#2B2340" strokeWidth="2" />
      <ellipse cx="26" cy="21" rx="6" ry="4" fill="#3A3350" />
      <circle cx="49" cy="15" r="9" fill="#FFFFFF" stroke="#2B2340" strokeWidth="2" />
      <ellipse cx="45" cy="9" rx="3.5" ry="6" fill="#3A3350" transform="rotate(-30 45 9)" />
      <circle cx="52" cy="13" r="1.7" fill="#2B2340" />
      <ellipse cx="57.5" cy="17" rx="2.2" ry="1.8" fill="#2B2340" />
    </svg>
  );
}

export default function Animalitos() {
  return (
    <div className="carril" aria-hidden="true">
      <Perro /><Gato /><Cachorro />
      <span className="carril-suelo" />
    </div>
  );
}
