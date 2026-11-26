// Animaciones Lottie decorativas de la portada y la app ciudadana (#467).
// Cada elemento con data-lottie="nombre" ya trae su dibujo de siempre (SVG o nada): eso es lo que
// se ve sin JavaScript, sin red, mientras carga y con «reducir movimiento». La animación se pide
// solo cuando el elemento está por verse (IntersectionObserver): primero el reproductor liviano
// (lottie-web light, servido desde el propio sitio) y luego /diseno/lottie/nombre.json. Fuera de
// la pantalla se pausa. Todo es decorativo: los contenedores llevan aria-hidden="true".
(function () {
  'use strict';
  if (!('IntersectionObserver' in window)) return;
  const reducido = window.matchMedia('(prefers-reduced-motion: reduce)');
  let reproductor = null;
  const datos = {};

  function cargarReproductor() {
    if (!reproductor) {
      reproductor = new Promise((listo, fallo) => {
        const script = document.createElement('script');
        script.src = '/diseno/vendor/lottie/lottie_light.min.js';
        script.onload = () => (window.lottie ? listo(window.lottie) : fallo(new Error('sin lottie')));
        script.onerror = fallo;
        document.head.append(script);
      });
    }
    return reproductor;
  }

  function cargarDatos(nombre) {
    if (!datos[nombre]) {
      datos[nombre] = fetch('/diseno/lottie/' + encodeURIComponent(nombre) + '.json')
        .then((r) => { if (!r.ok) throw new Error(String(r.status)); return r.json(); });
    }
    return datos[nombre];
  }

  const animaciones = new WeakMap();

  async function iniciar(elemento) {
    if (elemento.dataset.lottieEstado) return;
    elemento.dataset.lottieEstado = 'cargando';
    try {
      const [lottie, animacion] = await Promise.all([cargarReproductor(), cargarDatos(elemento.dataset.lottie)]);
      const lienzo = document.createElement('span');
      lienzo.className = 'lottie-lienzo';
      elemento.append(lienzo);
      const anim = lottie.loadAnimation({
        container: lienzo, renderer: 'svg', loop: true, autoplay: true,
        animationData: animacion, rendererSettings: { preserveAspectRatio: 'xMidYMid meet' },
      });
      animaciones.set(elemento, anim);
      elemento.classList.add('lottie-activa');  // el CSS oculta el dibujo de siempre
      elemento.dataset.lottieEstado = 'lista';
    } catch (error) {
      elemento.dataset.lottieEstado = 'sin-animacion';  // se queda el dibujo de siempre
    }
  }

  const vigia = new IntersectionObserver((entradas) => {
    for (const entrada of entradas) {
      const anim = animaciones.get(entrada.target);
      if (entrada.isIntersecting) {
        if (anim) anim.play(); else iniciar(entrada.target);
      } else if (anim) {
        anim.pause();
      }
    }
  }, { rootMargin: '120px' });

  function observar(elemento) {
    if (!reducido.matches) vigia.observe(elemento);
  }

  // Si la persona activa «reducir movimiento» con la página abierta, todo vuelve a quedarse quieto.
  reducido.addEventListener?.('change', () => {
    if (!reducido.matches) return;
    document.querySelectorAll('.lottie-activa').forEach((el) => {
      animaciones.get(el)?.destroy();
      animaciones.delete(el);
      el.querySelector('.lottie-lienzo')?.remove();
      el.classList.remove('lottie-activa');
      vigia.unobserve(el);
    });
  });

  window.PatitasLottie = { observar };
  document.querySelectorAll('[data-lottie]').forEach(observar);
})();
