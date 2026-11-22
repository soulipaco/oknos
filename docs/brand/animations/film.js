/* Oknos films: a motion-comic player (docs/brand/animations/).
   A film is a list of shots: an illustration, how long it stays, where the camera starts and ends
   (a slow pan and zoom), an optional effect, and a caption in Greek with a Turkish and English line.
   Shots cross-fade; tap the picture to pause. Plain script, no build, no libraries. */
(function () {
  "use strict";
  const FADE = 0.9;  // seconds of cross-fade at the start of each shot
  const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
  const ease = (u) => { u = clamp(u); return u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2; };
  const lerp = (a, b, u) => a + (b - a) * u;

  function film({ root, shots, title, end }) {
    const stage = root.querySelector(".stage");
    const capEl = root.querySelector(".cap-el"), capTr = root.querySelector(".cap-tr");
    const bar = root.querySelector(".progress i");
    const replay = root.querySelector(".replay");
    const langBtns = root.querySelectorAll("[data-lang]");
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let lang = (navigator.language || "en").toLowerCase().startsWith("tr") ? "tr" : "en";
    try { lang = localStorage.getItem("oknos-anim-lang") || lang; } catch { /* fine */ }

    // timeline
    let at = 0;
    for (const s of shots) { s.start = at; at += s.d; }
    const endLen = end ? end.d : 0;
    const duration = at + endLen;

    // layers: one <img> per shot, the end card on top, a flash layer
    const layers = shots.map((s) => {
      const img = new Image();
      img.src = s.src; img.alt = s.alt || ""; img.decoding = "async"; img.draggable = false;
      img.className = "shot";
      stage.append(img);
      return img;
    });
    const flash = document.createElement("div"); flash.className = "flash"; stage.append(flash);
    const endCard = document.createElement("div"); endCard.className = "end-card";
    if (end) { endCard.innerHTML = end.html; stage.append(endCard); }

    let shown = -2;
    function caption(i) {
      if (i === shown) return;
      shown = i;
      const c = i >= 0 ? shots[i].cap : (i === -1 && end ? end.cap : null);
      capEl.classList.remove("in"); capTr.classList.remove("in");
      setTimeout(() => {
        capEl.textContent = c ? c.el : ""; capTr.textContent = c ? c[lang] : "";
        if (c) { capEl.classList.add("in"); capTr.classList.add("in"); }
      }, 160);
    }
    function setLang(l) {
      lang = l;
      try { localStorage.setItem("oknos-anim-lang", l); } catch { /* fine */ }
      langBtns.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === l)));
      root.querySelectorAll("[data-en]").forEach((n) => { n.textContent = n.dataset[lang]; });
      const c = shown >= 0 ? shots[shown].cap : (shown === -1 && end ? end.cap : null);
      capTr.textContent = c ? c[lang] : "";
    }
    langBtns.forEach((b) => b.addEventListener("click", () => setLang(b.dataset.lang)));
    setLang(lang);

    function frame(t) {
      let current = 0;
      shots.forEach((s, i) => {
        const img = layers[i];
        const local = t - s.start;
        const visible = local > -0.01 && local < s.d + FADE;
        if (!visible) { img.style.opacity = 0; return; }
        if (local >= 0) current = i;
        // fade in over FADE at the start (the first shot too, from the title), stay until the next one covers it
        const op = i === 0 ? ease(local / FADE) : ease(local / FADE);
        img.style.opacity = op;
        img.style.zIndex = i + 1;
        // the camera: from cam[0] to cam[1] over the shot (and its fade), scale and percent offsets
        const [a, b] = s.cam || [[0, 0, 1.04], [0, 0, 1.1]];
        const u = reduce ? 0 : ease(clamp(local / (s.d + FADE)));
        let x = lerp(a[0], b[0], u), y = lerp(a[1], b[1], u);
        const sc = lerp(a[2], b[2], u);
        if (s.fx === "shake" && local < 1.2) { const k = (1.2 - local) * 1.4; x += k * Math.sin(local * 70); y += k * Math.cos(local * 53); }
        img.style.transform = `translate(${x}%, ${y}%) scale(${sc})`;
        img.style.filter = s.fx === "dream" ? `saturate(${0.85}) brightness(1.04)` : "";
      });
      // a white flash where a shot asks for it
      let fl = 0;
      shots.forEach((s) => { if (s.fx === "flash" || s.fx === "shake") fl = Math.max(fl, 1 - Math.abs(t - s.start) / 0.35); });
      flash.style.opacity = clamp(fl);
      // the end card
      const e = end ? clamp((t - at) / 0.9) : 0;
      endCard.style.opacity = ease(e);
      endCard.style.zIndex = shots.length + 2;
      caption(end && t >= at ? -1 : current);
      if (bar) bar.style.width = `${(100 * t) / duration}%`;
    }

    let t0 = performance.now(), paused = false, pausedAt = 0, done = false;
    function tick(now) {
      if (!paused) {
        const t = Math.min((now - t0) / 1000, duration);
        frame(t);
        if (t >= duration && !done) { done = true; root.classList.add("ended"); }
      }
      requestAnimationFrame(tick);
    }
    replay?.addEventListener("click", () => { t0 = performance.now(); done = false; shown = -2; root.classList.remove("ended", "paused"); paused = false; });
    stage.addEventListener("click", () => {
      if (done) return;
      paused = !paused;
      if (paused) pausedAt = performance.now(); else t0 += performance.now() - pausedAt;
      root.classList.toggle("paused", paused);
    });
    // ?still=12 holds the film at second 12 (for checking one moment); ?t=12 starts there
    const q = new URLSearchParams(location.search);
    if (q.has("t")) t0 = performance.now() - parseFloat(q.get("t")) * 1000;
    document.title = title;
    if (q.has("still")) {
      const ts = parseFloat(q.get("still"));
      Promise.all(layers.map((i) => i.decode().catch(() => {}))).then(() => { frame(ts); caption(end && ts >= at ? -1 : shots.findLastIndex((s) => s.start <= ts)); });
      return;
    }
    // start once the first pictures are ready
    Promise.all(layers.slice(0, 2).map((i) => i.decode().catch(() => {}))).then(() => { t0 = performance.now() - (q.has("t") ? parseFloat(q.get("t")) * 1000 : 0); requestAnimationFrame(tick); });
  }

  window.OknosFilm = { film };
})();
