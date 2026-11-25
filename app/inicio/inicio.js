// Portada (#426; inicio v3). La página funciona sin esto: las ilustraciones y las fotos fijas del
// diseño (Lupe, Cascabel, Copo, Nube y Toby) son imágenes estáticas del repo (#452) y nunca
// dependen del catálogo. Aquí solo se agrega lo que viene del servidor:
// - cuatro animales «En adopción» del catálogo, con su foto real,
// - las cifras anónimas (reportes y en adopción; si fallan, se queda «—»: nunca se inventan),
// - «Copiar enlace» con el portapapeles real.
// Render (plan gratuito) se duerme: la primera petición puede tardar o fallar mientras despierta.
// Por eso se reintenta con espera creciente, y una foto que falla se vuelve a pedir antes de
// rendirse; la huella de reemplazo sale solo si el animal de verdad no tiene foto.
// Los datos nunca se pegan como HTML (XSS): todo se arma con createElement y textContent.
(function () {
  "use strict";

  const PREFERIDOS = ["Cascabel", "Bombón", "Mochi", "Copo"]; // si están publicados (con foto)
  const TAMANO = { pequeno: "Pequeño", mediano: "Mediano", grande: "Grande" };

  function edad(meses) {
    if (meses < 12) return meses + (meses === 1 ? " mes" : " meses");
    const anos = Math.floor(meses / 12);
    return anos + (anos === 1 ? " año" : " años");
  }

  const esperar = (ms) => new Promise((listo) => setTimeout(listo, ms));

  /** GET con reintentos: 6 intentos (unos 90 s en total) mientras el servidor despierta. Un 4xx
   *  no se reintenta (no va a cambiar). */
  async function pedir(ruta) {
    let ultimo;
    for (let intento = 0; intento < 6; intento++) {
      const corte = new AbortController();
      const reloj = setTimeout(() => corte.abort(), 25000);
      try {
        const r = await fetch(ruta, { headers: { Accept: "application/json" }, signal: corte.signal });
        if (r.ok) return await r.json();
        ultimo = new Error(String(r.status));
        if (r.status >= 400 && r.status < 500) throw ultimo;
      } catch (e) {
        if (e === ultimo && /^4/.test(e.message)) throw e;
        ultimo = e;
      } finally {
        clearTimeout(reloj);
      }
      await esperar(Math.min(2000 * 2 ** intento, 15000));
    }
    throw ultimo;
  }

  const SVG = "http://www.w3.org/2000/svg";

  /** Huella de reemplazo: solo para el animal que de verdad no tiene foto. */
  function huella() {
    const svg = document.createElementNS(SVG, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("class", "huella-reemplazo");
    const partes = [["ellipse", { cx: 12, cy: 15.5, rx: 5, ry: 4.2 }], ["circle", { cx: 6, cy: 9.5, r: 2.2 }],
      ["circle", { cx: 10, cy: 6, r: 2.2 }], ["circle", { cx: 14, cy: 6, r: 2.2 }], ["circle", { cx: 18, cy: 9.5, r: 2.2 }]];
    for (const [tipo, attrs] of partes) {
      const el = document.createElementNS(SVG, tipo);
      for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, String(v));
      svg.append(el);
    }
    return svg;
  }

  /** Foto del catálogo. Si falla (el servidor despertando), se pide otra vez hasta 3 veces con
   *  espera creciente; solo entonces queda la huella. Nunca una imagen rota. */
  function imagen(animal, alt) {
    const img = document.createElement("img");
    let intentos = 0;
    img.alt = alt;
    img.decoding = "async";
    img.addEventListener("error", () => {
      if (intentos < 3) {
        intentos += 1;
        setTimeout(() => { img.src = animal.foto + "?intento=" + intentos; }, 1500 * 2 ** intentos);
      } else {
        img.replaceWith(huella());
      }
    });
    img.src = animal.foto;
    return img;
  }

  function texto(clase, valor, etiqueta) {
    const el = document.createElement(etiqueta || "span");
    el.className = clase;
    el.textContent = valor;
    return el;
  }

  /** Tarjeta centrada (inicio v3): foto circular, nombre, «especie · edad · tamaño», su
   *  carácter (primera etiqueta de la ficha, si la tiene) y «Conocer». */
  function tarjeta(animal) {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.className = "animal";
    a.href = "/panel/#adoptar/animales";
    const foto = document.createElement("span");
    foto.className = "animal-foto";
    foto.append(animal.foto ? imagen(animal, "") : huella());
    const especie = animal.especie === "gato" ? "Gatito" : "Perrito";
    a.append(foto, texto("h animal-nombre", animal.nombre),
      texto("animal-datos", [especie, edad(animal.edad_meses), TAMANO[animal.tamano] || animal.tamano].join(" · ")));
    const caracter = (animal.etiquetas || [])[0];
    if (caracter) a.append(texto("animal-caracter", caracter));
    a.append(texto("animal-conocer", "Conocer"));
    li.append(a);
    return li;
  }

  /** Cuatro del catálogo: los del prototipo primero, luego los que tienen foto. */
  function elegirCuatro(animales) {
    const orden = [
      ...PREFERIDOS.map((n) => animales.find((a) => a.nombre === n && a.foto)),
      ...animales.filter((a) => a.foto), ...animales];
    const elegidos = [];
    for (const a of orden) {
      if (a && !elegidos.includes(a)) elegidos.push(a);
      if (elegidos.length === 4) break;
    }
    return elegidos;
  }

  async function animales() {
    try {
      const lista = await pedir("/adopciones/animales");
      ponerCifra("en_adopcion", lista.length);  // en adopción = el catálogo público
      const cuatro = elegirCuatro(lista);
      if (cuatro.length) document.getElementById("en-adopcion").replaceChildren(...cuatro.map(tarjeta));
    } catch (e) {
      /* sin conexión o sin catálogo: se quedan las huellas y el enlace a la adopción */
    }
  }

  /** Pone una cifra real en todos sus huecos (el hero y los óvalos); sin dato, queda «—». */
  function ponerCifra(clave, valor) {
    if (!Number.isInteger(valor)) return;
    for (const el of document.querySelectorAll('[data-cifra="' + clave + '"]')) {
      el.textContent = valor.toLocaleString("es-CO");
    }
  }

  async function cifras() {
    try {
      const c = await pedir("/indicadores/publicos");
      ponerCifra("reportes", c.reportes);
      ponerCifra("rescatados", c.rescatados);
    } catch (e) {
      /* se quedan los «—» */
    }
  }

  function compartir() {
    const boton = document.getElementById("compartir");
    const aviso = document.getElementById("compartido");
    boton.addEventListener("click", async () => {
      const enlace = new URL(boton.getAttribute("data-enlace") || "/", location.href).href;
      try {
        await navigator.clipboard.writeText(enlace);
        aviso.textContent = "¡Enlace copiado! Pégalo en tu chat del barrio.";
      } catch (e) {
        aviso.textContent = "Copia este enlace: " + enlace;
      }
    });
  }

  compartir();
  void animales();
  void cifras();
})();
