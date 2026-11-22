/* Oknos films: a motion-comic player (docs/brand/animations/).
   A film is a list of shots: an illustration, how long it stays, where the camera starts and ends
   (a slow pan and zoom), an optional effect, and a caption in Greek with a Turkish and English line.
   Shots cross-fade; tap the picture to pause. Plain script, no build, no libraries.
   Sound: voice/<shot>.mp3 (the picture's name: f1-01, f3-06; the end card f1-end) is the shot's
   narration, made by scripts/film_voice.py and not tracked by git. When the clips are there, a
   "Play with sound" button starts the film again with them, each shot lasting at least its clip
   plus a pause; without them the film plays silently, as before. */
(function () {
  "use strict";
  const FADE = 0.9;  // seconds of cross-fade at the start of each shot
  const LEAD = 0.35, REST = 0.8;  // with sound: the clip starts this far into its shot, and the shot lasts this long after it
  const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
  const ease = (u) => { u = clamp(u); return u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2; };
  const lerp = (a, b, u) => a + (b - a) * u;

  function film({ root, shots, title, end }) {
    const stage = root.querySelector(".stage");
    const capEl = root.querySelector(".cap-el"), capTr = root.querySelector(".cap-tr");
    const bar = root.querySelector(".progress i");
    const replay = root.querySelector(".replay");
    const controls = root.querySelector(".controls");
    const langBtns = root.querySelectorAll("[data-lang]");
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let lang = (navigator.language || "en").toLowerCase().startsWith("tr") ? "tr" : "en";
    try { lang = localStorage.getItem("oknos-anim-lang") || lang; } catch { /* fine */ }

    // timeline: each shot's own length, or (with sound) at least its clip's
    let at = 0, duration = 0, voiced = false;
    shots.forEach((s) => { s.d0 = s.d; });
    if (end) end.d0 = end.d;
    function timeline() {
      at = 0;
      for (const s of shots) {
        s.d = voiced && s.clip ? Math.max(s.d0, LEAD + s.clip.duration + REST) : s.d0;
        s.start = at; at += s.d;
      }
      if (end) end.start = at;
      if (end) end.d = voiced && end.clip ? Math.max(end.d0, LEAD + end.clip.duration + REST + 0.6) : end.d0;
      duration = at + (end ? end.d : 0);
    }
    timeline();

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
      if (voiced) sound(t);
    }

    // sound: one <audio> element (unlocked by the tap), set to the clip of the moment
    const player = new Audio();
    player.preload = "auto";
    let playing = null;  // the clip the player holds now; null: look again (after a pause, a replay, a seek)
    function sound(t) {
      const parts = end ? [...shots, end] : shots;
      let want = null, offset = 0;
      for (const s of parts) {
        const u = t - s.start - LEAD;
        if (s.clip && u >= 0 && u < s.clip.duration) { want = s.clip; offset = u; }
      }
      if (want === playing) return;
      playing = want;
      if (!want) return;  // a clip that ends by itself is left to end
      player.src = want.src;
      try { player.currentTime = offset; } catch { /* fine */ }
      player.play().catch(() => { /* blocked or interrupted: the film goes on silently */ });
    }
    function hush() { player.pause(); playing = null; }

    let t0 = performance.now(), paused = false, pausedAt = 0, done = false;
    function tick(now) {
      if (!paused) {
        const t = Math.min((now - t0) / 1000, duration);
        frame(t);
        if (t >= duration && !done) { done = true; root.classList.add("ended"); }
      }
      requestAnimationFrame(tick);
    }
    function restart() { hush(); t0 = performance.now(); done = false; shown = -2; root.classList.remove("ended", "paused"); paused = false; }
    replay?.addEventListener("click", restart);
    stage.addEventListener("click", () => {
      if (done) return;
      paused = !paused;
      if (paused) { pausedAt = performance.now(); hush(); } else t0 += performance.now() - pausedAt;
      root.classList.toggle("paused", paused);
    });

    // the clips: each one's length is read from the file; the button appears only if some are there
    const name = (src) => src.split("/").pop().replace(/\.[a-z0-9]+$/i, "");
    function probe(src) {
      return new Promise((done) => {
        const a = new Audio();
        const fin = (ok) => { clearTimeout(timer); done(ok && isFinite(a.duration) && a.duration > 0 ? { src, duration: a.duration } : null); };
        const timer = setTimeout(() => fin(false), 6000);
        a.preload = "metadata";
        a.addEventListener("loadedmetadata", () => fin(true), { once: true });
        a.addEventListener("error", () => fin(false), { once: true });
        a.src = src;
      });
    }
    let soundBtn = null;
    function label() {
      if (!soundBtn) return;
      const k = !voiced ? "play" : player.muted ? "on" : "off";
      const words = { play: { en: "▶ Play with sound", tr: "▶ Sesli oynat" }, on: { en: "Sound on", tr: "Sesi aç" }, off: { en: "Sound off", tr: "Sesi kapat" } }[k];
      soundBtn.dataset.en = words.en; soundBtn.dataset.tr = words.tr; soundBtn.textContent = words[lang];
      soundBtn.setAttribute("aria-pressed", String(voiced && !player.muted));
    }
    function offerSound() {
      if (!controls) return;
      const stem = name(shots[0].src).split("-")[0];
      Promise.all([...shots.map((s) => probe(`voice/${name(s.src)}.mp3`)), end ? probe(`voice/${stem}-end.mp3`) : null])
        .then((found) => {
          shots.forEach((s, i) => { s.clip = found[i]; });
          if (end) end.clip = found[shots.length];
          if (!found.some(Boolean)) return;
          soundBtn = document.createElement("button");
          soundBtn.type = "button"; soundBtn.className = "sound";
          controls.prepend(soundBtn);
          label();
          soundBtn.addEventListener("click", () => {
            if (!voiced) {
              // unlock the player inside the tap (Safari asks for that), then start again with the voice's timing
              player.src = (shots.find((s) => s.clip) || end).clip.src;
              player.play().then(() => { if (playing === null) player.pause(); }).catch(() => {});
              voiced = true; timeline(); restart();
            } else {
              player.muted = !player.muted;
            }
            label();
          });
        });
    }

    // ?still=12 holds the film at second 12 (for checking one moment); ?t=12 starts there
    const q = new URLSearchParams(location.search);
    if (q.has("t")) t0 = performance.now() - parseFloat(q.get("t")) * 1000;
    document.title = title;
    if (q.has("still")) {
      const ts = parseFloat(q.get("still"));
      Promise.all(layers.map((i) => i.decode().catch(() => {}))).then(() => { frame(ts); caption(end && ts >= at ? -1 : shots.findLastIndex((s) => s.start <= ts)); });
      return;
    }
    offerSound();
    // start once the first pictures are ready
    Promise.all(layers.slice(0, 2).map((i) => i.decode().catch(() => {}))).then(() => { t0 = performance.now() - (q.has("t") ? parseFloat(q.get("t")) * 1000 : 0); requestAnimationFrame(tick); });
  }

  window.OknosFilm = { film };
})();
