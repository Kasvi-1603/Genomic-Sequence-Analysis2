/**
 * Figma DNA — lottie-web renders exported JSON.
 * Layer stack: simple-ready (helix) + animaed-ready (FX) + signal-ready.
 */
(function () {
  function countRotationKeyframes(data) {
    let n = 0;
    function walk(obj) {
      if (!obj || typeof obj !== "object") return;
      if (Array.isArray(obj)) {
        obj.forEach(walk);
        return;
      }
      const r = obj.r;
      if (r && r.a === 1 && Array.isArray(r.k) && r.k.length > 2) n += 1;
      Object.values(obj).forEach(walk);
    }
    walk(data);
    return n;
  }

  function initDnaLottieHero() {
    const root = document.getElementById("figma-dna-hero");
    if (!root) return;

    if (typeof lottie === "undefined") {
      console.error("lottie-web failed to load");
      return;
    }

    const simpleUrl = root.dataset.lottieSimple;
    const animaedUrl = root.dataset.lottieAnimaed;
    const signalUrl = root.dataset.lottieSignal;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    root.innerHTML = `
      <div class="dna-lottie-stage">
        <div class="dna-lottie-layer dna-lottie-layer--simple" id="dna-lottie-simple"></div>
        <div class="dna-lottie-layer dna-lottie-layer--fx" id="dna-lottie-fx"></div>
        <div class="dna-lottie-layer dna-lottie-layer--signal" id="dna-lottie-signal"></div>
      </div>
    `;

    const simpleEl = document.getElementById("dna-lottie-simple");
    const fxEl = document.getElementById("dna-lottie-fx");
    const signalEl = document.getElementById("dna-lottie-signal");

    let simpleAnim = null;
    let fxAnim = null;
    let signalAnim = null;
    let master = null;

    function fitSvg(container) {
      const svg = container?.querySelector("svg");
      if (!svg) return;
      svg.style.width = "100%";
      svg.style.height = "100%";
      svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    }

    function loadLottie(url, container) {
      return new Promise((resolve, reject) => {
        const anim = lottie.loadAnimation({
          container,
          renderer: "svg",
          loop: true,
          autoplay: false,
          path: url,
          rendererSettings: {
            preserveAspectRatio: "xMidYMid meet",
            progressiveLoad: false,
            hideOnTransparent: true,
          },
        });

        anim.addEventListener("DOMLoaded", () => {
          fitSvg(container);
          resolve(anim);
        });
        anim.addEventListener("data_failed", () => reject(new Error(url)));
        anim.addEventListener("config_ready", () => {
          const rot = countRotationKeyframes(anim.animationData);
          if (rot === 0) {
            console.warn(
              "[DNA] No multi-keyframe rotation in",
              url,
              "— export Animaed frame with LottieFiles for Figma (see docs/DNA_LOTTIE_EXPORT.md)"
            );
          }
        });
      });
    }

    function syncFollowers() {
      if (!master) return;
      const frame = master.currentFrame;
      if (fxAnim && fxAnim !== master) {
        fxAnim.goToAndStop(Math.min(frame, fxAnim.totalFrames - 1), true);
      }
      if (signalAnim && signalAnim !== master) {
        const t = frame / master.totalFrames;
        const sf = Math.floor(t * signalAnim.totalFrames) % signalAnim.totalFrames;
        signalAnim.goToAndStop(sf, true);
      }
    }

    function start() {
      if (!master) return;
      if (!reduceMotion) {
        master.play();
      } else {
        master.goToAndStop(0, true);
      }
      syncFollowers();
    }

    Promise.all([
      loadLottie(simpleUrl, simpleEl).then((a) => {
        simpleAnim = a;
        const w = a.animationData?.w;
        const h = a.animationData?.h;
        if (w && h) {
          simpleEl.style.setProperty("--helix-w", String(w));
          simpleEl.style.setProperty("--helix-h", String(h));
        }
      }),
      loadLottie(animaedUrl, fxEl).then((a) => {
        fxAnim = a;
      }),
      loadLottie(signalUrl, signalEl)
        .then((a) => {
          signalAnim = a;
        })
        .catch((err) => {
          console.warn("Signal Lottie skipped:", err);
        }),
    ])
      .then(() => {
        master = simpleAnim;
        master.addEventListener("enterFrame", syncFollowers);
        start();
      })
      .catch((err) => console.error("DNA Lottie failed:", err));

    document.addEventListener("visibilitychange", () => {
      if (!master || reduceMotion) return;
      if (document.visibilityState === "visible") master.play();
      else master.pause();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initDnaLottieHero);
  } else {
    initDnaLottieHero();
  }
})();
