// Portada (#426). La página funciona sin esto; aquí solo se agrega lo que viene del servidor:
// - fotos reales de los animales publicados (Pinina, Mochi, Lupe…; si no están, otros con foto),
// - cuatro animales «En adopción» del catálogo,
// - las tres cifras anónimas de /indicadores/publicos (si fallan, se queda «—»: nunca se inventan),
// - «Copiar enlace» con el portapapeles real.
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

  async function pedir(ruta) {
    const r = await fetch(ruta, { headers: { Accept: "application/json" } });
    if (!r.ok) throw new Error(String(r.status));
    return r.json();
  }

  function imagen(animal, alt) {
    const img = document.createElement("img");
    img.src = animal.foto;
    img.alt = alt;
    img.loading = "lazy";
    img.decoding = "async";
    img.addEventListener("error", () => img.remove()); // sin foto rota: queda la huella
    return img;
  }

  /** Pone la foto en cada hueco [data-animal]: el animal de ese nombre o, si no está, otro con
   *  foto que aún no se haya usado. */
  function ponerFotos(animales) {
    const conFoto = animales.filter((a) => a.foto);
    const usados = new Set();
    for (const hueco of document.querySelectorAll("[data-animal]")) {
      const nombre = hueco.getAttribute("data-animal");
      // El mismo animal puede salir en dos secciones (como Winny en el prototipo); el reemplazo,
      // si no está publicado, es uno que aún no se haya usado.
      const animal = conFoto.find((a) => a.nombre === nombre)
        || conFoto.find((a) => !usados.has(a.animal_id));
      if (!animal) continue;
      usados.add(animal.animal_id);
      const alt = hueco.hasAttribute("data-alt") ? "Foto de " + animal.nombre : "";
      hueco.prepend(imagen(animal, alt));
    }
  }

  function fila(lista, nombre, valor) {
    const dt = document.createElement("dt");
    dt.textContent = nombre;
    const dd = document.createElement("dd");
    dd.textContent = valor;
    lista.append(dt, dd);
  }

  function tarjeta(animal) {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.className = "animal tarjeta";
    a.href = "/panel/#adoptar";
    const foto = document.createElement("span");
    foto.className = "foto";
    if (animal.foto) foto.append(imagen(animal, ""));
    const nombre = document.createElement("span");
    nombre.className = "h animal-nombre";
    nombre.textContent = animal.nombre;
    const datos = document.createElement("dl");
    fila(datos, "Especie", animal.especie === "gato" ? "Gatito" : "Perrito");
    fila(datos, "Edad", edad(animal.edad_meses));
    fila(datos, "Tamaño", TAMANO[animal.tamano] || animal.tamano);
    const pie = document.createElement("span");
    pie.className = "animal-pie";
    const conocer = document.createElement("span");
    conocer.className = "animal-conocer";
    conocer.textContent = "Conocer";
    const corazon = document.querySelector(".hero-corazon svg").cloneNode(true);
    corazon.classList.add("late");
    pie.append(conocer, corazon);
    a.append(foto, nombre, datos, pie);
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
      ponerFotos(lista);
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
