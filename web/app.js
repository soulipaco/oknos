// Oknos front end. Plain ES module, no build step.

const app = document.getElementById("app");
const LANGS = ["en", "tr"];

const state = {
  lang: "en",
  strings: {},
  home: null,
  session: null,   // {session_id, cards, index, total, done}
  card: null,      // per-card UI state
  mock: null,      // a mock-exam section in progress: {section_id, cards, answers, deadline, ...}
};

// ---------- small helpers ----------

function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

function t(key, vars = {}) {
  const s = state.strings[key] ?? key;
  return s.replace(/\{(\w+)\}/g, (_, k) => (k in vars ? vars[k] : `{${k}}`));
}

function tr(textObj) {
  // A content translation in the UI language: tr falls back to en (SPEC §4.3).
  if (!textObj) return null;
  return textObj[state.lang] || textObj.en || null;
}

async function api(path, body) {
  const opts = body === undefined ? {} : {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.json();
}

async function loadStrings(lang) {
  const res = await fetch(`i18n/${lang}.json`);
  state.strings = await res.json();
  state.lang = lang;
  document.documentElement.lang = lang;
  document.title = t("app_name");
}

function showError() {
  app.replaceChildren(h("div", { class: "center-note" }, h("p", {}, t("error"))));
}

// Where the current card is drawn: the page, or a block inside a chapter (phase 5c).
const cardRoot = () => state.cardRoot || app;

const packOf = (itemKey) => itemKey.split("/")[0];
const idOf = (itemKey) => itemKey.split("/").slice(1).join("/");

// ---------- Greek speech: made-ahead clips first (phase 10, docs/VOICE.md), then the browser voice ----------

let greekVoice = null;
let voiceClips = 0;  // how many clips this learner has made (from /api/voice)
const canSpeak = () => !!greekVoice || voiceClips > 0;

function showSpeakButtons() {
  document.querySelectorAll(".speak, .play-all").forEach(b => { b.hidden = !canSpeak(); });
}

function pickVoice() {
  if (!("speechSynthesis" in window)) return;
  const voices = speechSynthesis.getVoices();
  greekVoice = voices.find(v => v.lang.toLowerCase().startsWith("el") && v.localService) || null;
  showSpeakButtons();
}
if ("speechSynthesis" in window) {
  pickVoice();
  speechSynthesis.addEventListener("voiceschanged", pickVoice);
}
fetch("/api/voice?brief=1").then(r => r.ok ? r.json() : null).then(st => { voiceClips = st?.files || 0; showSpeakButtons(); }).catch(() => {});

const voiceUrl = (text, role = "f") => `/voice?r=${role === "m" ? "m" : "f"}&t=${encodeURIComponent(text)}`;
let playing = null;  // the clip now playing, so a new one stops it
let speakRun = 0;    // bumps on every new request, so an older "play all" stops

function stopSpeaking() {
  speakRun += 1;
  if (playing) { playing.pause(); playing = null; }
  if ("speechSynthesis" in window) speechSynthesis.cancel();
}

function browserSay(text, rate) {
  if (!greekVoice) return Promise.resolve(false);
  return new Promise(resolve => {
    const u = new SpeechSynthesisUtterance(text);
    u.voice = greekVoice; u.lang = greekVoice.lang; u.rate = rate;
    u.onend = () => resolve(true); u.onerror = () => resolve(false);
    speechSynthesis.speak(u);
  });
}

function clipSay(text, role, rate) {
  // resolves true when the clip has played to the end, false if there is none
  return new Promise(resolve => {
    const a = new Audio(voiceUrl(text, role));
    a.playbackRate = Math.min(1, rate / 0.9);
    a.onended = () => resolve(true);
    a.onerror = () => resolve(false);
    playing = a;
    a.play().catch(() => resolve(false));
  });
}

async function say(text, rate, role, run) {
  if (voiceClips > 0 && await clipSay(text, role, rate)) return true;
  if (run !== speakRun) return false;
  return browserSay(text, rate);
}

function speak(text, rate = 0.9, role = "f") {
  if (!canSpeak() || !text) return false;
  stopSpeaking();
  say(text, rate, role, speakRun);
  if (state.card) state.card.audioPlays += 1;
  return true;
}

const SPEAKER_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 5 6 9H3v6h3l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M18.5 5.5a9 9 0 0 1 0 13"/></svg>';

function speakButton(text, small = false, role = "f") {
  const b = h("button", {
    class: small ? "speak small" : "speak",
    type: "button",
    title: t("listen"),
    "aria-label": t("listen"),
    onclick: (e) => { e.stopPropagation(); speak(text, 0.9, role); },
  });
  b.innerHTML = SPEAKER_SVG;
  b.hidden = !canSpeak();
  return b;
}

// ---------- tappable Greek words ----------

const GREEK_WORD = /([Ͱ-Ͽἀ-῿]+(?:['’][Ͱ-Ͽἀ-῿]+)?)/u;

function greekText(text, { tag = "span", cls = "", tappable = true } = {}) {
  // Greek text in which every word can be tapped for its meaning (logged as a lookup).
  const el = h(tag, { class: cls, lang: "el" });
  for (const part of String(text).split(GREEK_WORD)) {
    if (!part) continue;
    if (tappable && GREEK_WORD.test(part) && part.length > 1) {
      el.append(h("span", { class: "w", role: "button", tabindex: "0", "data-w": part }, part));
    } else {
      el.append(document.createTextNode(part));
    }
  }
  return el;
}

let popover = null;

function closePopover() {
  if (popover) { popover.remove(); popover = null; }
}

async function lookupWord(target) {
  closePopover();
  const word = target.dataset.w;
  const c = state.card;
  if (c) c.lookups += 1;
  const box = h("div", { class: "popover", role: "dialog" }, h("p", { class: "muted small" }, t("loading")));
  document.body.append(box);
  popover = box;
  const r = target.getBoundingClientRect();
  box.style.left = `${Math.max(8, Math.min(window.scrollX + r.left, window.scrollX + document.documentElement.clientWidth - 300))}px`;
  box.style.top = `${window.scrollY + r.bottom + 6}px`;
  let res;
  try {
    res = await api("/api/lookup", { word, item_key: c?.data.item_key ?? null, ui_lang: state.lang });
  } catch { res = { entries: [] }; }
  if (popover !== box) return;
  const rows = res.entries.length
    ? res.entries.map(e => h("div", { class: "pop-row" },
        h("span", { class: "el", lang: "el" }, e.el), speakButton(e.say || e.el, true),
        h("span", { class: "pop-meaning" }, meaningText(e.meaning, e.meaning_lang))))
    : [h("p", { class: "muted" }, t("lookup_none", { word }))];
  const formOf = res.entries[0]?.form_of || null;  // a verb form, or a form a glossary maps to its word
  if (formOf) rows.unshift(h("p", { class: "muted small form-of" }, t("lookup_form", { word, lemma: formOf })));
  if (res.match === "stem") rows.push(h("p", { class: "muted small" }, t("lookup_similar")));
  if (res.match === "phrase") rows.push(h("p", { class: "muted small" }, t("lookup_phrase")));
  box.replaceChildren(h("div", { class: "pop-head" }, h("strong", { lang: "el" }, word),
    // a single letter or pair (σ, μπ) is read as the card's name and example, not spelled out
    speakButton((word.length <= 2 && res.entries[0]?.say) || word, true)), ...rows);
}

document.addEventListener("click", (e) => {
  const w = e.target.closest?.(".w");
  if (w) { e.preventDefault(); lookupWord(w); return; }
  if (popover && !e.target.closest(".popover")) closePopover();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closePopover();
  const w = e.target.closest?.(".w");
  if (w && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); lookupWord(w); }
});

function meaningText(text, lang) {
  // A meaning in the UI language as plain text; one that fell back to the other language says so.
  if (!lang || lang === state.lang) return text;
  return h("span", { class: "other-lang", title: t("meaning_other_lang") }, text, " ", h("span", { class: "lang-tag" }, lang.toUpperCase()));
}

function translatable(greekEl, translation, { rubric = false } = {}) {
  // A Greek line with a "Translate" toggle underneath it. In a mock exam only the rubric can be
  // translated: a translation of the text or the statements would give answers away.
  if (!translation || (state.mock && !rubric)) return [greekEl];
  const line = h("div", { class: "translation", hidden: true }, translation);
  const toggle = h("button", { class: "link-button small", type: "button" }, t("translate"));
  toggle.addEventListener("click", () => {
    line.hidden = !line.hidden;
    toggle.textContent = line.hidden ? t("translate") : t("hide_translation");
  });
  return [greekEl, line, toggle];
}

// ---------- on-screen Greek keyboard ----------

// The standard Greek layout on a Latin keyboard, so a physical keyboard also types Greek.
const LATIN_TO_GREEK = {
  a: "α", b: "β", g: "γ", d: "δ", e: "ε", z: "ζ", h: "η", u: "θ", i: "ι", k: "κ", l: "λ", m: "μ",
  n: "ν", j: "ξ", o: "ο", p: "π", r: "ρ", s: "σ", w: "ς", t: "τ", y: "υ", f: "φ", x: "χ", c: "ψ", v: "ω",
};
const ACCENTED = { "α": "ά", "ε": "έ", "η": "ή", "ι": "ί", "ο": "ό", "υ": "ύ", "ω": "ώ", "ϊ": "ΐ", "ϋ": "ΰ" };
const DIAERESIS = { "ι": "ϊ", "υ": "ϋ", "ί": "ΐ", "ύ": "ΰ" };
const KEY_ROWS = [
  ["ς", "ε", "ρ", "τ", "υ", "θ", "ι", "ο", "π"],
  ["α", "σ", "δ", "φ", "γ", "η", "ξ", "κ", "λ"],
  ["ζ", "χ", "ψ", "ω", "β", "ν", "μ"],
];

function insertAtCursor(input, text) {
  const start = input.selectionStart ?? input.value.length;
  const end = input.selectionEnd ?? input.value.length;
  input.value = input.value.slice(0, start) + text + input.value.slice(end);
  input.selectionStart = input.selectionEnd = start + text.length;
  input.dispatchEvent(new Event("input"));
}

function accentLast(input, table) {
  // Put the accent (or diaeresis) on the vowel just before the cursor.
  const pos = input.selectionStart ?? input.value.length;
  for (let i = pos - 1; i >= 0 && i >= pos - 3; i--) {
    const ch = input.value[i];
    if (table[ch]) {
      input.value = input.value.slice(0, i) + table[ch] + input.value.slice(i + 1);
      input.selectionStart = input.selectionEnd = pos;
      input.dispatchEvent(new Event("input"));
      return;
    }
  }
}

function greekInput(onEnter, label, { multiline = false } = {}) {
  const input = multiline
    ? h("textarea", { class: "typed el long", lang: "el", rows: "7", autocomplete: "off", autocapitalize: "sentences",
        spellcheck: "false", "aria-label": label || t("type_answer") })
    : h("input", {
        class: "typed el", lang: "el", type: "text", autocomplete: "off", autocapitalize: "off",
        spellcheck: "false", "aria-label": label || t("type_answer"),
      });
  input.convert = true;
  // Latin letters become Greek as they arrive (keyboard, paste or phone), using the standard
  // Greek layout; ";" before a vowel puts the accent on it, as on a Greek keyboard.
  input.addEventListener("input", () => {
    if (!input.convert) return;
    const pos = input.selectionStart ?? input.value.length;
    const before = input.value.slice(0, pos);
    const convert = (text) => text
      .replace(/[a-zA-Z]/g, ch => {
        const g = LATIN_TO_GREEK[ch.toLowerCase()];
        return g ? (ch === ch.toLowerCase() ? g : g.toUpperCase()) : ch;
      })
      .replace(/;([αεηιουωϊϋ])/g, (_, v) => ACCENTED[v] || v)
      .replace(/:([ιυ])/g, (_, v) => DIAERESIS[v] || v);
    const value = convert(input.value);
    if (value !== input.value) {
      const caret = convert(before).length;
      input.value = value;
      input.selectionStart = input.selectionEnd = caret;
    }
  });
  input.addEventListener("keydown", (e) => {
    if (multiline) return;
    if (e.key === "Enter" && !e.ctrlKey && !e.metaKey && !e.altKey) { e.preventDefault(); onEnter(); }
  });
  const key = (label, onclick, cls = "") => h("button", { type: "button", class: `k ${cls}`, tabindex: "-1",
    onmousedown: (e) => e.preventDefault(), onclick: () => { onclick(); input.focus(); } }, label);
  const board = h("div", { class: "keyboard", "aria-hidden": "true" },
    ...KEY_ROWS.map(row => h("div", { class: "krow" }, row.map(ch => key(ch, () => insertAtCursor(input, ch))))),
    h("div", { class: "krow" },
      key("´", () => accentLast(input, ACCENTED), "wide"),
      key("¨", () => accentLast(input, DIAERESIS)),
      key(t("space"), () => insertAtCursor(input, " "), "space"),
      key("⌫", () => {
        const s = input.selectionStart ?? input.value.length;
        if (s > 0) {
          input.value = input.value.slice(0, s - 1) + input.value.slice(input.selectionEnd ?? s);
          input.selectionStart = input.selectionEnd = s - 1;
          input.dispatchEvent(new Event("input"));
        }
      }, "wide"),
      multiline ? key("↵", () => insertAtCursor(input, "\n"), "wide") : null));
  return { input, board };
}

// ---------- navigation: one URL per screen, an app bar on every screen (phase 5c) ----------

// Screen name -> renderer. The URL is ?<name> or ?<name>=<arg>; the home screen is the bare path.
const SCREENS = {
  home: () => renderHome(),
  book: () => renderBook(),
  stage: (id) => renderStage(id),
  lesson: (id) => renderChapter(id),
  practise: () => renderPractise(),
  words: () => renderWords(),
  verbs: () => renderVerbs(),
  exam: () => renderExam(),
  writing: () => renderWriting(),
  submission: (id) => renderSubmission(Number(id)),
  mock: (id) => renderMockRun(Number(id)),
  voice: () => renderVoice(),
  films: (n) => renderFilms(n),
  podcast: (id) => renderPodcast(id),
};
const SCREEN_ALIASES = { map: "book" };  // older links

function urlFor(name, arg = null) {
  if (name === "home") return location.pathname;
  return `?${name}${arg !== null && arg !== undefined ? `=${encodeURIComponent(arg)}` : ""}`;
}

function parseRoute() {
  for (const [k, v] of new URLSearchParams(location.search)) {
    const name = SCREEN_ALIASES[k] || k;
    if (name in SCREENS && name !== "home") return { name, arg: v || null };
  }
  return { name: "home", arg: null };
}

function go(name, arg = null, { replace = false } = {}) {
  // Open a screen and give it its own entry in the browser history.
  const url = urlFor(name, arg);
  const here = name === "home" ? location.search === "" : location.search === url;
  if (replace) history.replaceState({ name, arg }, "", url);
  else if (!here) history.pushState({ name, arg }, "", url);
  state.route = { name, arg };
  return SCREENS[name](arg);
}

function rerender() {
  // The same screen again (after a language change, say).
  const r = state.route || parseRoute();
  return SCREENS[r.name](r.arg);
}

window.addEventListener("popstate", () => {
  if (state.mock?.timer) return rerender();  // a timed section: the back button does not leave it
  state.route = parseRoute();
  rerender();
});

const NAV_ITEMS = [["home", "nav_home"], ["book", "nav_book"], ["practise", "nav_practise_short"],
                   ["words", "nav_words_short"], ["verbs", "nav_verbs_short"], ["podcast", "nav_podcast"],
                   ["exam", "nav_exam"]];

function navLink(name, label, arg = null, cls = "") {
  // A real link (it opens in a new tab with a middle click), routed in place on a normal click.
  return h("a", { href: urlFor(name, arg), class: cls, onclick: (e) => {
    if (e.ctrlKey || e.metaKey || e.shiftKey || e.button === 1) return;
    e.preventDefault();
    go(name, arg);
  } }, label);
}

function appBar(active) {
  // The top of every screen outside a session: the name, theme and language, and the main sections.
  const nav = h("nav", { class: "app-nav", "aria-label": t("nav_label") },
    NAV_ITEMS.map(([name, key]) => {
      const a = navLink(name, t(key), null, name === active ? "on" : "");
      if (name === active) a.setAttribute("aria-current", "page");
      return a;
    }));
  // On a phone the bar scrolls sideways: bring the current section into view.
  setTimeout(() => {  // once the bar is on the page (not requestAnimationFrame: a hidden tab never runs it)
    const on = nav.querySelector(".on");
    if (!on || nav.scrollWidth <= nav.clientWidth) return;
    const box = nav.getBoundingClientRect(), it = on.getBoundingClientRect();
    nav.scrollLeft += (it.left + it.width / 2) - (box.left + box.width / 2);
  });
  return [h("header", { class: "topbar" }, navLink("home", wordmark(), null, "home-link"), topActions()), nav];
}

function crumb(name, label, arg = null) {
  return h("p", { class: "crumb" }, navLink(name, `← ${label}`, arg));
}

// ---------- home ----------

function greeting() {
  const hour = new Date().getHours();
  return hour < 13 ? ["Καλημέρα!", t("greeting_morning")] : ["Καλησπέρα!", t("greeting_evening")];
}

function langSwitch() {
  return h("div", { class: "lang-switch", role: "group", "aria-label": t("language") },
    ...[["en", "English"], ["tr", "Türkçe"]].map(([code, label]) =>
      h("button", {
        type: "button",
        "aria-pressed": String(state.lang === code),
        onclick: async () => {
          if (state.lang === code) return;
          await loadStrings(code);
          api("/api/profile", { ui_lang: code }).catch(() => {});
          rerender();
        },
        "aria-label": label,
      }, h("span", { class: "lang-long" }, label), h("span", { class: "lang-short", "aria-hidden": "true" }, code.toUpperCase()))));
}

function wordmark() {
  return h("div", { class: "wordmark" },
    h("img", { class: "mark", src: "favicon.svg", alt: "", width: "28", height: "28" }), t("app_name"));
}

// ---------- the brand's drawings: the rope, the ring, the donkey, the icons (docs/brand/README.md) ----------
// The same geometry as scripts/make_brand.py. Colours come from the theme's CSS variables.

function svgEl(markup) {
  const tpl = document.createElement("template");
  tpl.innerHTML = markup.trim();
  return tpl.content.firstChild;
}

let ropeIds = 0;
const fmt = (v) => (Math.round(v * 100) / 100).toString();
const polyline = (pts) => "M" + pts.map(([x, y]) => `${fmt(x)} ${fmt(y)}`).join(" L");

function ropeSegments(kind, { width = 600, a = 4.2, n = 22, R = 32, steps = 6 } = {}) {
  // Two strands crossing over and under: along a line, or around a ring (r = R ± a·sin(nθ)).
  const segs = { A: [], B: [] };
  const count = kind === "ring" ? 2 * n : 2 * n + 1;
  for (let k = 0; k < count; k++) {
    for (const [s, sg] of [["A", 1], ["B", -1]]) {
      const pts = [];
      for (let i = 0; i <= steps; i++) {
        if (kind === "ring") {
          const t0 = (k - 0.5) * Math.PI / n, t1 = (k + 0.5) * Math.PI / n;
          const th = t0 + (t1 - t0) * i / steps, r = R + sg * a * Math.sin(n * th);
          pts.push([50 + r * Math.sin(th), 50 - r * Math.cos(th)]);
        } else {
          const u0 = Math.max(0, (k - 0.5) / (2 * n)), u1 = Math.min(1, (k + 0.5) / (2 * n));
          const u = u0 + (u1 - u0) * i / steps;
          pts.push([width * u, sg * a * Math.sin(2 * Math.PI * n * u)]);
        }
      }
      segs[s].push([polyline(pts), (k % 2 === 0) === (s === "A")]);
    }
  }
  return { segs, count };
}

function ropeStrands({ segs }, upto, strokeW, gap, box) {
  const id = `rope-${++ropeIds}`;
  const pick = (over) => ["A", "B"].flatMap(s => segs[s].filter(([, o], i) => o === over && i < upto).map(([d]) => d)).join(" ");
  const [x, y, w, hh] = box;
  return `<defs><mask id="${id}" maskUnits="userSpaceOnUse" x="${x}" y="${y}" width="${w}" height="${hh}">`
    + `<rect x="${x}" y="${y}" width="${w}" height="${hh}" fill="#fff"/>`
    + `<path d="${pick(true)}" fill="none" stroke="#000" stroke-width="${strokeW + 2 * gap}" stroke-linecap="round"/></mask></defs>`
    + `<g fill="none" style="stroke:var(--accent)" stroke-width="${strokeW}" stroke-linecap="round" stroke-linejoin="round">`
    + `<path mask="url(#${id})" d="${pick(false)}"/><path d="${pick(true)}"/></g>`;
}

function ropeBar(done, total, cls = "") {
  // Progress as a plaited rope: plaited as far as you have got, a faint dotted line after (the brand's "session bar").
  const frac = total ? Math.min(1, done / total) : 1;
  const width = 600, rope = ropeSegments("line", { width });
  const upto = frac > 0 ? Math.max(1, Math.round(frac * rope.count)) : 0;
  const end = width * upto / rope.count;
  const rest = upto < rope.count
    ? `<path d="M${fmt(upto ? end + 8 : 0)} 0 H${width}" style="stroke:var(--line)" stroke-width="3.4" stroke-dasharray="1 9" stroke-linecap="round"/>`
    : "";
  const pct = Math.round(frac * 100);
  return svgEl(`<svg class="rope-bar ${cls}" viewBox="-6 -10 ${width + 12} 20" preserveAspectRatio="xMinYMid meet" `
    + `role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}">`
    + rest + (upto ? ropeStrands(rope, upto, 4.6, 1.6, [-6, -10, width + 12, 20]) : "") + `</svg>`);
}

function ropeRing(frac, label = "", size = 36) {
  // A stage's ring: it closes as the stage is learned. The label (the lesson's number) sits inside.
  const rope = ropeSegments("ring", { n: 5, a: 5, steps: 8 });
  const upto = Math.round(Math.min(1, Math.max(0, frac)) * rope.count);
  const dotted = `<circle cx="50" cy="50" r="32" fill="none" style="stroke:var(--line)" stroke-width="5" stroke-dasharray="1.5 9" stroke-linecap="round"/>`;
  const text = label === "" ? "" : `<text x="50" y="62" text-anchor="middle" font-size="34" font-weight="700" style="fill:var(--accent)">${label}</text>`;
  return svgEl(`<svg class="ring" width="${size}" height="${size}" viewBox="0 0 100 100" aria-hidden="true">`
    + dotted + (upto ? ropeStrands(rope, upto, 8.4, 1.8, [0, 0, 100, 100]) : "") + text + `</svg>`);
}

const DONKEY_EARS = {  // the agent's three moods, shown by the ears
  ready: ["C40 30 40 16 47 6 C53 14 55 28 53 39", "C59 30 68 20 79 15 C79 26 71 37 62 44", true],
  working: ["C40 30 40 16 47 6 C53 14 55 28 53 39", "C61 36 74 30 92 30 C86 38 74 42 62 44", true],
  resting: ["C40 31 44 18 55 10 C58 20 56 30 53 39", "C61 36 74 30 92 30 C86 38 74 42 62 44", false],
};

function donkey(mood = "ready", size = 56) {
  // The mascot: it stands for the agent, so it appears where the agent has done (or will do) something.
  const [e1, e2, open] = DONKEY_EARS[mood];
  const eye = open ? `<circle cx="39" cy="54" r="2.4" stroke="none" style="fill:var(--ink)"/>` : `<path d="M36 55 q3 2.6 6 0"/>`;
  return svgEl(`<svg class="donkey" width="${size}" height="${Math.round(size * 1.2)}" viewBox="2 2 96 116" aria-hidden="true">`
    + `<g fill="none" style="stroke:var(--ink)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">`
    + `<path d="M66 114 C64 102 60 94 54 90 C46 88 36 90 28 90 C16 90 9 83 9 74 C9 64 15 58 24 57 C33 55 39 48 43 41 ${e1} ${e2} C71 50 80 60 84 74 C87 86 88 100 90 114"/>`
    + `${eye}<path d="M14 72 q2 -1.6 4 0"/><path d="M13 83 q5 2.2 10 0.6"/></g></svg>`);
}

const ICONS = {  // one line style: a 24 grid, 2 px, round ends
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/>',
  system: '<circle cx="12" cy="12" r="9"/><path d="M12 3v18" /><path d="M12 3a9 9 0 0 1 0 18z" fill="currentColor"/>',
  flag: '<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>',
  book: '<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M4 19V5"/>',
  voice: '<path d="M11 5 6 9H3v6h3l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M18.5 5.5a9 9 0 0 1 0 13"/>',
  up: '<path d="M6 15l6-6 6 6"/>',
  pen: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
  mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0"/><path d="M12 18v3"/>',
  headphones: '<path d="M3 14v-2a9 9 0 0 1 18 0v2"/><path d="M21 15a2 2 0 0 1-2 2h-1v-5h1a2 2 0 0 1 2 2z"/><path d="M3 15a2 2 0 0 0 2 2h1v-5H5a2 2 0 0 0-2 2z"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
  down: '<path d="M6 9l6 6 6-6"/>',
  lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5"/>',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
  film: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M10 9.5v5l4.5-2.5z"/>',
  play: '<path d="M7 4.5v15l12.5-7.5z"/>',
  pause: '<path d="M8 5v14M16 5v14"/>',
  lines: '<path d="M4 6h16M4 12h16M4 18h10"/>',
  close: '<path d="M6 6l12 12M18 6 6 18"/>',
};

function icon(name) {
  return svgEl(`<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" `
    + `stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name]}</svg>`);
}

function areaName(area) {
  if (area === "vocab") return t("area_vocab");
  if (area.startsWith("verbs.")) return t("area_verbs", { tense: tenseName(area.slice(6)) });
  if (area.startsWith("skill.")) return t(`skill_${area.slice(6)}`);
  return area;
}

function pct(x) { return Math.round(x * 100); }

function tenseName(tense) {
  // Coach-written items may use tenses the UI has no label for; show the name rather than a key.
  const key = `tense_${tense}`;
  return key in state.strings ? t(key) : String(tense).replace(/_/g, " ");
}

function todayLine(stats) {
  const parts = [];
  if (stats.due.vocab_shown) parts.push(t("due_reviews", { n: stats.due.vocab_shown }));
  if (stats.due.vocab > stats.due.vocab_shown) parts.push(t("due_waiting", { n: stats.due.vocab - stats.due.vocab_shown }));
  const verbs = stats.due.verbs || Math.min(4, stats.verbs_new_available);
  if (verbs) parts.push(t("due_verbs", { n: verbs }));
  if (stats.new_available) parts.push(t("due_new"));
  return parts.join(" · ");
}

function consistencyGrid(stats) {
  const max = Math.max(10, ...stats.grid.map(d => d.minutes));
  const cells = stats.grid.map(d => {
    const level = d.answers === 0 ? 0 : Math.min(4, 1 + Math.floor((d.minutes / max) * 4));
    const label = d.answers ? t("grid_day", { date: d.date, minutes: d.minutes, answers: d.answers }) : t("grid_none", { date: d.date });
    return h("span", { class: `cell l${level}`, title: label, "aria-label": label });
  });
  const week = stats.grid.slice(-7).reduce((a, d) => a + d.minutes, 0);
  return h("section", { class: "panel" },
    h("h2", {}, t("consistency")),
    h("div", { class: "grid28", role: "img", "aria-label": t("grid_label") }, cells),
    h("p", { class: "muted small" }, t("consistency_line", { days: stats.days_studied_14, minutes: Math.round(week) })));
}

function meter(label, parts, total) {
  // A stacked bar: known / learning / unseen, with counts.
  const seg = (n, cls) => h("span", { class: `seg ${cls}`, style: `width:${total ? (n / total) * 100 : 0}%` });
  return h("div", { class: "meter" },
    h("div", { class: "meter-head" }, h("span", {}, label),
      h("span", { class: "muted small" }, t("meter_counts", { known: parts.known, learning: parts.learning, unseen: parts.unseen }))),
    h("div", { class: "bar" }, seg(parts.known, "known"), seg(parts.learning, "learning")));
}

function standing(stats) {
  const rows = stats.areas.map(a => h("div", { class: "area" },
    h("span", { class: "area-name" }, areaName(a.area)),
    a.enough
      ? h("span", { class: "area-bar" }, h("span", { style: `width:${a.accuracy * 100}%` }))
      : h("span", { class: "area-bar thin" }),
    h("span", { class: "area-num small" }, a.enough ? `${t("pct", { pct: pct(a.accuracy) })} · n=${a.n}` : t("not_enough", { n: a.n }))));
  const weakest = stats.weakest
    ? t("weakest_line", { area: areaName(stats.weakest.area), pct: pct(stats.weakest.accuracy), n: stats.weakest.n })
    : t("weakest_none");
  const retention = stats.retention.n >= 10
    ? t("retention_line", { pct: pct(stats.retention.rate), n: stats.retention.n })
    : null;
  return h("section", { class: "panel" },
    h("h2", {}, t("standing")),
    h("p", { class: "weakest" }, weakest),
    meter(t("words"), stats.words, stats.words.total),
    stats.verbs.total ? meter(t("verb_forms"), stats.verbs, stats.verbs.total) : null,
    retention ? h("p", { class: "muted small" }, retention) : null,
    rows.length ? h("div", { class: "areas" }, rows) : null,
    stats.lookups_30 ? h("p", { class: "muted small" }, t("lookups_line", { n: stats.lookups_30 })) : null);
}

function fmtDate(iso) {
  if (!iso) return "";
  const d = new Date(`${iso.slice(0, 10)}T12:00:00`);
  return d.toLocaleDateString(state.lang === "tr" ? "tr-TR" : "en-GB", { day: "numeric", month: "long", year: "numeric" });
}

function coachTile(coach) {
  // What the agent did: its note (with the donkey), feedback ready, and any scheduled run that failed.
  if (!coach) return null;
  const blocks = [];
  for (const p of coach.run_problems || []) {
    blocks.push(h("p", { class: "warn" }, t(p.problem === "failed" ? "run_failed" : "run_missing",
      { skill: p.skill, date: fmtDate(p.since) })));
  }
  const text = coach.message ? (coach.message[state.lang] || coach.message.en || coach.message.tr) : null;
  blocks.push(h("div", { class: "tile-head" }, donkey(text ? "ready" : "resting", 44),
    h("div", {}, h("p", { class: "eyebrow" }, t("home_coach")),
      coach.message ? h("p", { class: "small muted" }, fmtDate(coach.message.date)) : null)));
  blocks.push(h("p", {}, text || t("home_coach_none")));
  if (coach.feedback_ready?.length) {
    const first = coach.feedback_ready[0];
    blocks.push(h("button", { class: "secondary small-btn feedback-ready", type: "button", onclick: () => go("submission", first.id) },
      t(first.kind === "speaking" ? "feedback_ready_speaking" : "feedback_ready_writing")));
  }
  blocks.push(h("p", { class: "small muted" }, t("tutor_line")));
  if (coach.submissions_total) blocks.push(navLink("writing", t("your_writing"), null, "tile-link"));
  const today = state.home?.podcast_today;
  if (today) blocks.push(navLink("podcast", [icon("headphones"), t(today.kind === "weekly" ? "pod_link_week" : "pod_link_today",
    { n: Math.max(1, Math.round((today.seconds || 0) / 60)) })], today.id, "tile-link films-link"));
  if (state.home?.podcasts) blocks.push(navLink("podcast", [icon("headphones"), t("pod_link_home", { n: state.home.podcasts })], null, "tile-link films-link"));
  blocks.push(navLink("films", [icon("film"), t("films_link_coach")], null, "tile-link films-link"));
  return h("section", { class: "tile coach-tile" }, ...blocks);
}

function datesTile(coach) {
  const entries = coach?.dates?.entries || [];
  if (!entries.length) return null;
  const today = state.home.today;
  const rows = entries.map(e => {
    const what = (state.lang === "tr" && e.what_tr) || e.what;
    const reg = e.registration;
    let date, line;
    if (reg?.opens && reg.opens > today) { date = reg.opens; line = t("date_reg_opens_short", { what }); }
    else if (reg?.closes && reg.closes >= today) { date = reg.closes; line = t("date_reg_closes_short", { what }); }
    else { date = e.date; line = what; }
    return h("li", {}, h("span", { class: "date-chip" }, shortDate(date)), h("span", {}, line));
  });
  return h("section", { class: "tile" }, h("p", { class: "eyebrow" }, icon("calendar"), t("home_dates")), h("ul", { class: "dates" }, rows));
}

function shortDate(iso) {
  try { return new Date(iso + "T12:00:00").toLocaleDateString(state.lang === "tr" ? "tr-TR" : "en-GB", { day: "numeric", month: "short" }); }
  catch { return iso; }
}

function resetScreens() {
  clearInterval(state.mock?.timer);
  state.mock = null;
  state.session = null;
  state.card = null;
  state.cardRoot = null;
  state.inline = null;
  if ("speechSynthesis" in window) speechSynthesis.cancel();
  closePopover();
}

function topActions() {
  const voiceLink = navLink("voice", icon("voice"), null, "theme-switch voice-link");
  voiceLink.title = t("voice_title"); voiceLink.setAttribute("aria-label", t("voice_title"));
  return h("div", { class: "top-actions" }, voiceLink, themeSwitch(), langSwitch());
}

async function renderHome() {
  resetScreens();
  try {
    state.home = await api("/api/home");
  } catch { return showError(); }
  const { stats, minutes } = state.home;
  const [hello, helloT] = greeting();
  const status = stats.today.state;
  const startLabel = status === "resume" ? t("continue_daily", { left: stats.today.left })
    : status === "done" ? t("more5") : t("start_daily", { minutes });
  const first = stats.answers_total === 0;
  const na = state.home.next_action || { kind: "daily" };
  const daily = () => startSession(status === "done" ? "extra" : "daily");

  // One thing to do first (phase 5c): read the current lesson's chapter, or the daily session.
  let primary;
  const second = [];
  if (na.kind === "read") {
    primary = h("button", { class: "start", type: "button", id: "start", onclick: () => go("lesson", na.stage) },
      na.opened ? t("na_continue_read", { name: tr(na.title) }) : t("na_read", { name: tr(na.title), minutes: na.minutes }));
    second.push(h("p", { class: "muted small" }, t("na_read_line")));
    if (na.then === "daily") second.push(h("button", { class: "link-button", type: "button", onclick: daily }, `${t("na_or_daily")}: ${startLabel}`));
  } else {
    primary = h("button", { class: status === "done" ? "start secondary-start" : "start", type: "button", id: "start", onclick: daily }, startLabel);
    second.push(h("p", { class: "counts muted" }, first ? t("home_first") : todayLine(stats)));
  }
  // Your progress (the 28 days, words and areas) lives on the exam screen since 2026-11-22.
  const words = state.home.words;
  const today = stats.today;
  const rope = status === "resume" && today.planned ? h("div", { class: "today-rope" },
    ropeBar(today.planned - today.left, today.planned),
    h("span", { class: "small muted" }, t("home_rope_line", { done: today.planned - today.left, total: today.planned }))) : null;
  const hero = h("section", { class: "hero" },
    h("p", { class: "eyebrow" }, `${t("home_today")} · ${fmtDate(state.home.today)}`),
    h("h1", { class: "greeting", lang: "el" }, hello),
    h("p", { class: "greeting-tr" }, `${helloT} · ${t("tagline")}`),
    status === "done" && na.kind !== "read" ? h("p", { class: "done-today" }, t("done_today")) : null,
    na.kind !== "read" && words?.new?.length && status !== "done"
      ? [h("p", { class: "eyebrow strip-head" }, t("home_new_words", { n: words.new_count })), wordStrip(words.new)] : null,
    primary, ...second, rope);
  app.replaceChildren(
    ...appBar("home"),
    h("div", { class: "home-grid" }, hero, lessonTile(state.home.curriculum, words)),
    h("div", { class: "tiles" }, coachTile(state.home.coach), datesTile(state.home.coach), examTile(state.home)),
    ...(first ? [] : [h("p", { class: "progress-link" }, navLink("exam", [t("home_progress_link"), icon("arrow")], null, "tile-link"))]),
  );
  document.getElementById("start").focus();
}

// ---------- theme: system, light or dark (phase 5c) ----------

const THEMES = ["system", "light", "dark"];

function currentTheme() {
  try { const v = localStorage.getItem("gc-theme"); return THEMES.includes(v) ? v : "system"; } catch { return "system"; }
}

function applyTheme(theme) {
  if (theme === "system") delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = theme;
}

function themeSwitch() {
  const b = h("button", { class: "theme-switch", type: "button" });
  const paint = () => {
    const th = currentTheme();
    b.replaceChildren(icon(th === "dark" ? "moon" : th === "light" ? "sun" : "system"));
    b.title = t(`theme_${th}`);
    b.setAttribute("aria-label", t(`theme_${th}`));
  };
  b.addEventListener("click", () => {
    const next = THEMES[(THEMES.indexOf(currentTheme()) + 1) % THEMES.length];
    try { localStorage.setItem("gc-theme", next); } catch { /* the choice lasts this page only */ }
    applyTheme(next);
    paint();
  });
  paint();
  return b;
}

// ---------- session ----------

async function startSession(kind, items = [], extra = {}) {
  resetScreens();
  app.replaceChildren(h("div", { class: "center-note" }, t("loading")));
  try {
    const s = await api("/api/session", { kind, items, ui_lang: state.lang, has_voice: canSpeak(), ...extra });
    if (!s.cards.length) {
      const back = kind === "choose" ? "practise" : "home";
      app.replaceChildren(...appBar(back), h("section", { class: "empty-state" }, donkey("resting", 72),
        h("p", {}, t(kind === "choose" ? "nothing_choose" : "nothing")),
        h("p", {}, navLink(back, t(kind === "choose" ? "nothing_back_practise" : "nothing_back_home"), null, "secondary"))));
      return;
    }
    state.session = { ...s, index: 0 };
    renderCard();
  } catch { showError(); }
}

async function startCheck(stageId) {
  app.replaceChildren(h("div", { class: "center-note" }, t("loading")));
  try {
    const s = await api(`/api/curriculum/stages/${encodeURIComponent(stageId)}/check`, {});
    state.session = { ...s, index: 0 };
    renderCard();
  } catch { showError(); }
}

function sessionFrame(body, label = null) {
  const s = state.session;
  const card = s.cards[s.index];
  const done = (s.done || 0) + s.index;
  const total = s.total || s.cards.length;
  return [
    h("header", { class: "topbar" },
      h("span", { class: "muted small" }, `${label || t(`segment_${card.segment || "review"}`)} · ${t("progress", { done: done + 1, total })}`),
      h("button", { class: "link-button", type: "button", onclick: finishSession }, t("enough")),
    ),
    h("div", { class: "progress" }, ropeBar(done, total, "session")),
    body,
  ];
}

function flagButton() {
  const menu = h("div", { class: "flag-menu", hidden: true },
    ...["wrong", "confusing", "audio"].map(reason => h("button", { type: "button", onclick: async () => {
      menu.hidden = true;
      try {
        await api("/api/flag", { item_key: state.card.data.item_key, reason });
        btn.textContent = t("flag_thanks");
        btn.disabled = true;
      } catch { /* the flag is optional */ }
    } }, t(`flag_${reason}`))));
  const btn = h("button", { class: "flag", type: "button", title: t("flag_title"), "aria-label": t("flag_title"),
    onclick: () => { menu.hidden = !menu.hidden; } }, icon("flag"));
  return h("div", { class: "flag-wrap" }, btn, menu);
}

const RENDERERS = {};

function renderLearn(card) {
  // Teach before testing (phase 5c): a word never seen is shown first, ungraded.
  const L = card.learn;
  state.card = null;
  const go = h("button", { class: "primary", type: "button", id: "next", onclick: () => {
    state.session.learned.add(card.item_key);
    renderCard();
  } }, t("learn_go"));
  const example = L.example ? h("div", { class: "example" }, speakButton(L.example.el, true),
    h("div", {}, greekText(L.example.el, { tag: "p", cls: "el" }),
      tr(L.example) ? h("p", { class: "translation" }, tr(L.example)) : null)) : null;
  const body = h("article", { class: "card learn-card" },
    h("div", { class: "question" }, h("div", { class: "ask" }, t("learn_title")),
      h("div", { class: "prompt-row" }, greekText(L.el, { tag: "p", cls: "big-greek", tappable: false }), speakButton(L.say || L.el))),
    L.picture ? h("img", { class: "word-picture", src: L.picture, alt: "", width: "200", height: "200" }) : null,
    h("p", { class: "learn-meaning" }, meaningText(L.meaning, L.meaning_lang)),
    example ? h("div", { class: "learn-example" }, h("p", { class: "muted small" }, t("learn_example")), example) : null,
    h("div", { class: "actions" }, go));
  app.replaceChildren(...sessionFrame(body, t("segment_learn")));
  setTimeout(() => speak(L.say || L.el, 0.85), 200);
  go.focus();
}

function renderCard() {
  closePopover();
  const s = state.session;
  const card = s.cards[s.index];
  s.learned ||= new Set();
  if (card.learn && !state.mock && s.kind !== "check" && !s.learned.has(card.item_key)) return renderLearn(card);
  state.card = { data: card, answered: false, started: performance.now(), audioPlays: 0, lookups: 0, tf: [], picks: {} };
  const body = (RENDERERS[card.type] || RENDERERS.mcq)(card);
  if (state.mock) {
    app.replaceChildren(...mockFrame(body));
    mockRestore(card, body);
    return;
  }
  body.prepend(flagButton());
  app.replaceChildren(...sessionFrame(body));
  if (s.index === 0 && (state.home?.stats?.answers_total ?? 0) < 10) {
    app.append(h("p", { class: "hint muted small" }, t("keys_hint")));
  }
  const first = app.querySelector("input.typed") || app.querySelector("article.card");
  if (first?.tagName === "ARTICLE") first.setAttribute("tabindex", "-1");
  first?.focus({ preventScroll: true });
}

function optionList(options, greek, onPick) {
  return h("div", { class: "options" },
    options.map((text, i) => h("button", {
      class: greek ? "option el" : "option",
      type: "button",
      lang: greek ? "el" : null,
      "data-index": i,
      onclick: () => onPick(i),
    }, h("span", { class: "key", "aria-hidden": "true" }, String(i + 1)), text)));
}

function pictureOptions(urls, onPick) {
  // Four pictures to choose from; keys 1–4 work as for words.
  return h("div", { class: "options pictures" },
    urls.map((src, i) => h("button", { class: "option picture-option", type: "button", "data-index": i, onclick: () => onPick(i),
      "aria-label": String(i + 1) },
      h("span", { class: "key", "aria-hidden": "true" }, String(i + 1)), h("img", { src, alt: "", width: "160", height: "160" }))));
}

function rubricLine(rubric, ask) {
  // The rubric (Greek, translatable), then the item's question or situation in the UI language,
  // always visible: the question is never only in the hidden translation.
  const askText = ask ? tr(ask) : null;
  return [
    rubric?.el ? h("div", { class: "rubric" }, ...translatable(greekText(rubric.el, { cls: "el" }), tr(rubric), { rubric: true })) : null,
    askText ? h("p", { class: "ask" }, askText) : null,
  ];
}

function checkRow(onCheck) {
  const btn = h("button", { class: "primary", type: "button", disabled: true, onclick: onCheck }, state.mock ? t("mock_save") : t("check"));
  return [h("div", { class: "actions check-row" }, btn), btn];
}

// Listening: file audio first, then audio the coach pre-generated, then the browser voice.
function listenBlock(card) {
  const st = card.stimulus;
  if (!st || !(st.audio || st.tts)) return null;
  const limit = st.plays || 2;
  // In a mock, items that share one recording (one dialogue, several questions) share its plays.
  const playKey = st.audio ? `${st.audio}|${st.start || 0}` : card.item_key;
  let used = state.mock ? (state.mock.plays[playKey] || 0) : 0;
  let audio = null;
  const status = h("span", { class: "muted small" }, t("plays_left", { n: Math.max(0, limit - used) }));
  const play = h("button", { class: "primary listen", type: "button", disabled: used >= limit }, `▶ ${t("play")}`);
  const sources = [];
  if (st.audio) sources.push(`/packs/${encodeURIComponent(packOf(card.item_key))}/${st.audio.split("/").map(encodeURIComponent).join("/")}`);
  sources.push(`/audio-cache/${encodeURIComponent(packOf(card.item_key))}/${encodeURIComponent(idOf(card.item_key))}`);
  const start = st.start || 0;
  async function getAudio() {
    for (const src of sources) {
      try {
        const r = await fetch(src, { method: "HEAD" });
        if (r.ok) {
          const a = new Audio(src);
          // Only part of the file (one part of an exam recording): stop at `end`.
          if (st.end) a.addEventListener("timeupdate", () => { if (a.currentTime >= st.end) a.pause(); });
          return a;
        }
      } catch { /* try the next */ }
    }
    return null;
  }
  play.addEventListener("click", async () => {
    if (used >= limit && !state.card.answered) return;
    if (audio === null) audio = (await getAudio()) || false;
    if (audio) { audio.currentTime = start; audio.play(); state.card.audioPlays += 1; }
    else if (!speak(st.tts, 0.85)) { status.textContent = t("no_voice"); return; }
    used += 1;
    if (state.mock) state.mock.plays[playKey] = used;
    if (!state.card.answered) {
      status.textContent = t("plays_left", { n: Math.max(0, limit - used) });
      if (used >= limit) play.disabled = true;
    }
  });
  const transcript = st.tts ? h("div", { class: "transcript", hidden: true }, greekText(st.tts, { tag: "p", cls: "el" })) : null;
  state.card.revealTranscript = () => {
    play.disabled = false;
    status.textContent = "";
    if (transcript) transcript.hidden = false;
  };
  return h("div", { class: "listen-block" }, h("div", { class: "listen-row" }, play, status), transcript);
}

function scenePicture(url, alt) {
  // A scene of the story (docs/brand/CHARACTERS.md) above a task or a dialogue.
  return url ? h("figure", { class: "scene" }, h("img", { src: url, alt: alt || "", width: "512", height: "512", loading: "lazy" })) : null;
}

function scenePictures(urls) {
  // One scene, or two side by side labelled α and β (the exams' "describe and compare two photos").
  if (!urls?.length) return null;
  if (urls.length === 1) return scenePicture(urls[0]);
  return h("div", { class: "scene-pair" }, urls.map((u, i) => h("figure", { class: "scene" },
    h("img", { src: u, alt: "", width: "512", height: "512", loading: "lazy" }),
    h("figcaption", { lang: "el" }, ["α", "β"][i]))));
}

function stimulusBlock(card) {
  const pic = scenePictures(card.stimulus?.pictures);
  if (card.stimulus?.text) return [pic, h("div", { class: "notice" }, greekText(card.stimulus.text, { tag: "p" }))];
  return [pic, listenBlock(card)];
}

RENDERERS.vocab = (card) => {
  const dir = card.direction;
  const ask = { el_meaning: t("q_meaning"), meaning_el: t("q_greek"), audio_meaning: t("q_heard"), meaning_el_typed: t("q_type"),
    el_picture: t("q_picture") }[dir];
  let promptEl;
  if (dir === "el_meaning" || dir === "el_picture") promptEl = h("div", { class: "prompt-row" }, greekText(card.prompt, { tag: "p", cls: "big-greek", tappable: false }), speakButton(card.speak));
  else if (dir === "audio_meaning") {
    const b = h("button", { class: "primary listen big", type: "button", onclick: () => speak(card.speak, 0.8) }, `▶ ${t("play")}`);
    setTimeout(() => speak(card.speak, 0.8), 250);
    promptEl = h("div", { class: "prompt-row" }, b);
  } else promptEl = h("div", { class: "prompt-row" }, h("p", { class: "big-meaning" }, card.prompt));
  const question = h("div", { class: "question" }, h("div", { class: "ask" }, ask), promptEl);
  if (dir === "meaning_el_typed") {
    const { input, board } = greekInput(() => send());
    const [row, btn] = checkRow(() => send());
    btn.disabled = false;
    const send = () => { if (input.value.trim()) submit({ text: input.value }, { typed: input }); };
    return h("article", { class: "card" }, question, h("div", { class: "typed-wrap" }, input), board, row, h("div", { class: "slot" }));
  }
  const pick = (i) => submit({ choice: card.options[i] }, { pickedIndex: i });
  if (dir === "el_picture") {
    setTimeout(() => speak(card.speak, 0.85), 250);
    return h("article", { class: "card" }, question, pictureOptions(card.options, pick), h("div", { class: "slot" }));
  }
  if (dir === "meaning_el" && card.picture) question.append(h("img", { class: "word-picture small", src: card.picture, alt: "", width: "120", height: "120" }));
  return h("article", { class: "card" }, question, optionList(card.options, dir === "meaning_el", pick), h("div", { class: "slot" }));
};

RENDERERS.form = (card) => {
  const cue = card.cue || {};
  const cueLine = h("p", { class: "cue" },
    cue.lemma ? h("span", { class: "el cue-lemma", lang: "el" }, cue.lemma) : null,
    cue.tense ? h("span", { class: "chip" }, tenseName(cue.tense)) : null,
    cue.person ? h("span", { class: "chip" }, t(`person_${cue.person}`)) : null);
  const parts = card.text.split(/(\{\w+\})/);
  const inputs = {};
  let keyboard = null;
  const sentence = h("p", { class: "sentence el", lang: "el" });
  const send = () => {
    if (Object.values(inputs).some(i => !i.value.trim())) return;
    submit({ answers: Object.fromEntries(Object.entries(inputs).map(([g, i]) => [g, i.value])) }, { formInputs: inputs });
  };
  for (const part of parts) {
    const m = part.match(/^\{(\w+)\}$/);
    if (!m) { if (part) sentence.append(greekText(part)); continue; }
    const gap = m[1];
    if (card.options?.[gap]) {
      const slot = h("span", { class: "gap empty", "data-gap": gap }, "…");
      inputs[gap] = { value: "", el: slot };
      sentence.append(slot);
    } else {
      const { input, board } = greekInput(send, t("type_form"));
      input.classList.add("inline");
      inputs[gap] = input;
      keyboard = keyboard || board;
      sentence.append(input);
    }
  }
  const [row, btn] = checkRow(send);
  btn.disabled = false;
  const blocks = [rubricLine(card.rubric, card.ask), cueLine, ...translatable(sentence, tr(card.translation))];
  const gapWithOptions = Object.keys(card.options || {});
  if (gapWithOptions.length) {
    const gap = gapWithOptions[0];
    blocks.push(optionList(card.options[gap], true, (i) => {
      inputs[gap].value = card.options[gap][i];
      inputs[gap].el.textContent = card.options[gap][i];
      inputs[gap].el.classList.remove("empty");
      submit({ answers: { [gap]: card.options[gap][i] } }, { formInputs: inputs, pickedIndex: i });
    }));
  } else {
    blocks.push(keyboard, row);
  }
  return h("article", { class: "card" }, ...blocks, h("div", { class: "slot" }));
};

RENDERERS.mcq = (card) => {
  const prompt = greekText(card.prompt.el, { tag: "p", cls: "prompt-greek" });
  const question = h("div", { class: "question" }, ...translatable(prompt, tr(card.prompt)));
  const opts = optionList(card.options, true, (i) => submit({ choice: i }, { pickedIndex: i }));
  return h("article", { class: "card" }, rubricLine(card.rubric, card.ask), stimulusBlock(card), question, opts, h("div", { class: "slot" }));
};

RENDERERS.true_false = (card) => {
  const [row, checkBtn] = checkRow(() => submit({ answers: state.card.tf }));
  const statements = card.statements.map((st, i) => {
    const choose = (value) => {
      if (state.card.answered) return;
      state.card.tf[i] = value;
      line.querySelectorAll(".tf button").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.value === String(value))));
      checkBtn.disabled = card.statements.some((_, j) => typeof state.card.tf[j] !== "boolean");
    };
    const btn = (value, greek, key) => h("button", { type: "button", "data-value": String(value), "aria-pressed": "false", onclick: () => choose(value) },
      h("span", { lang: "el" }, greek), h("span", { class: "gloss" }, t(key)));
    const line = h("div", { class: "statement" },
      ...translatable(greekText(st.el, { tag: "p", cls: "el" }), tr(st)),
      h("div", { class: "tf" }, btn(true, "ΣΩΣΤΟ", "true"), btn(false, "ΛΑΘΟΣ", "false")));
    return line;
  });
  return h("article", { class: "card" }, rubricLine(card.rubric, card.ask), stimulusBlock(card),
    h("div", { class: "statements" }, statements), row, h("div", { class: "slot" }));
};

RENDERERS.match = (card) => {
  // Tap a left item, then the right item that goes with it. Tap a paired left item to undo.
  const picks = state.card.picks;
  let active = 0;
  const [row, checkBtn] = checkRow(() => submit({ answers: card.left.map((_, i) => picks[i]) }));
  const leftEls = card.left.map((text, i) => h("button", { class: "pick side-left el", type: "button", lang: "el", "data-i": i,
    onclick: () => { if (state.card.answered) return; if (picks[i] !== undefined) delete picks[i]; active = i; paint(); } },
    h("span", { class: "badge" }, String.fromCharCode(65 + i)), h("span", {}, text)));
  const rightEls = card.right.map((text, j) => h("button", { class: "pick side-right el", type: "button", lang: "el", "data-j": j,
    onclick: () => {
      if (state.card.answered) return;
      for (const [k, v] of Object.entries(picks)) if (v === j) delete picks[k];
      picks[active] = j;
      const next = card.left.findIndex((_, i) => picks[i] === undefined);
      active = next === -1 ? active : next;
      paint();
    } }, h("span", { class: "badge" }, ""), h("span", {}, text)));
  function paint() {
    leftEls.forEach((el, i) => el.classList.toggle("active", i === active && !state.card.answered));
    rightEls.forEach((el, j) => {
      const owner = Object.entries(picks).find(([, v]) => v === j);
      el.querySelector(".badge").textContent = owner ? String.fromCharCode(65 + Number(owner[0])) : "";
      el.classList.toggle("paired", !!owner);
    });
    leftEls.forEach((el, i) => el.classList.toggle("paired", picks[i] !== undefined));
    checkBtn.disabled = card.left.some((_, i) => picks[i] === undefined);
  }
  state.card.paintMatch = (answer, parts) => {
    leftEls.forEach((el, i) => {
      el.classList.add(parts[i] ? "right" : "wrong");
      if (!parts[i]) el.append(h("span", { class: "fix" }, `→ ${card.right[answer[i]]}`));
    });
  };
  paint();
  // The server shuffles the right column so that no pair sits on one row (`right_order`); a card made
  // before that is shown rotated by one, since most items are written pair by pair.
  const n = card.right.length;
  const order = Array.isArray(card.right_order) && card.right_order.length === n
    ? card.right_order : card.right.map((_, j) => (j + 1) % n);
  return h("article", { class: "card" }, rubricLine(card.rubric, card.ask), stimulusBlock(card),
    card.prompt?.el ? greekText(card.prompt.el, { tag: "p", cls: "prompt-greek" }) : null,
    h("div", { class: "match" }, h("div", { class: "col" }, leftEls), h("div", { class: "col" }, order.map(j => rightEls[j]))),
    row, h("div", { class: "slot" }));
};

RENDERERS.gap_bank = (card) => {
  const fill = state.card.picks;
  let active = null;
  const gaps = {};
  const text = h("p", { class: "sentence el", lang: "el" });
  const [row, checkBtn] = checkRow(() => submit({ answers: Object.fromEntries(Object.keys(gaps).map(g => [g, fill[g]])) }));
  for (const part of card.text.split(/(\{\w+\})/)) {
    const m = part.match(/^\{(\w+)\}$/);
    if (!m) { if (part) text.append(greekText(part)); continue; }
    const g = m[1];
    gaps[g] = h("button", { class: "gap empty", type: "button", "data-gap": g, onclick: () => {
      if (state.card.answered) return;
      if (fill[g]) delete fill[g];
      active = g;
      paint();
    } }, `(${g})`);
    text.append(gaps[g]);
  }
  const chips = card.bank.map(word => h("button", { class: "chip-word el", type: "button", lang: "el", onclick: () => {
    if (state.card.answered) return;
    for (const [k, v] of Object.entries(fill)) if (v === word) delete fill[k];
    const target = active && !fill[active] ? active : Object.keys(gaps).find(g => !fill[g]);
    if (!target) return;
    fill[target] = word;
    active = Object.keys(gaps).find(g => !fill[g]) || null;
    paint();
  } }, word));
  function paint() {
    for (const [g, el] of Object.entries(gaps)) {
      el.textContent = fill[g] || `(${g})`;
      el.classList.toggle("empty", !fill[g]);
      el.classList.toggle("active", g === active);
    }
    chips.forEach(c => c.classList.toggle("used", Object.values(fill).includes(c.textContent)));
    checkBtn.disabled = Object.keys(gaps).some(g => !fill[g]);
  }
  state.card.paintGaps = (answer, parts) => {
    Object.keys(gaps).sort((a, b) => Number(a) - Number(b)).forEach((g, i) => {
      gaps[g].classList.add(parts[i] ? "right" : "wrong");
      if (!parts[i]) gaps[g].textContent = `${fill[g]} → ${answer[g]}`;
    });
  };
  active = Object.keys(gaps)[0];
  paint();
  return h("article", { class: "card" }, rubricLine(card.rubric, card.ask), listenBlock(card),
    ...translatable(text, tr(card.translation)), h("div", { class: "bank" }, chips), row, h("div", { class: "slot" }));
};

RENDERERS.categorise = (card) => {
  const picks = state.card.picks;
  const [row, checkBtn] = checkRow(() => submit({ answers: card.items.map((_, i) => picks[i]) }));
  const rows = card.items.map((text, i) => {
    const buttons = card.categories.map((cat, c) => h("button", { type: "button", class: "cat", lang: "el", "aria-pressed": "false",
      onclick: () => {
        if (state.card.answered) return;
        picks[i] = c;
        buttons.forEach((b, k) => b.setAttribute("aria-pressed", String(k === c)));
        checkBtn.disabled = card.items.some((_, j) => picks[j] === undefined);
      } }, cat));
    return h("div", { class: "cat-row", "data-i": i }, greekText(text, { tag: "p", cls: "el" }), h("div", { class: "cats" }, buttons));
  });
  state.card.paintCats = (answer, parts) => {
    rows.forEach((r, i) => {
      r.querySelectorAll(".cat").forEach((b, c) => {
        if (c === answer[i]) b.classList.add("right");
        else if (c === picks[i]) b.classList.add("wrong");
      });
    });
  };
  return h("article", { class: "card" }, rubricLine(card.rubric, card.ask), stimulusBlock(card),
    card.prompt?.el ? greekText(card.prompt.el, { tag: "p", cls: "prompt-greek" }) : null,
    h("div", { class: "cat-list" }, rows), row, h("div", { class: "slot" }));
};

RENDERERS.table_fill = (card) => {
  // A table with typed cells (B1 comparison and note-taking). Each cell has its own Greek
  // keyboard, shown while that cell has the focus.
  const inputs = [];
  const boards = [];
  const send = () => {
    if (inputs.some(i => !i.value.trim())) return;
    submit({ answers: inputs.map(i => i.value) }, { tableInputs: inputs });
  };
  const [row, checkBtn] = checkRow(send);
  const refresh = () => { checkBtn.disabled = inputs.some(i => !i.value.trim()); };
  const head = h("tr", {}, h("th", {}), card.columns.map(c => h("th", { lang: "el" }, greekText(c))));
  const body = card.rows.map((label, i) => h("tr", {},
    h("th", { scope: "row", lang: "el" }, greekText(label)),
    card.columns.map((_, j) => {
      if (!card.cells[i][j]) return h("td", { class: "given el", lang: "el" }, card.given?.[i]?.[j] ?? "");
      const { input, board } = greekInput(() => {
        const next = inputs[inputs.indexOf(input) + 1];
        if (next) next.focus(); else send();
      }, `${label} · ${card.columns[j]}`);
      input.classList.add("cell-input");
      input.addEventListener("input", refresh);
      input.addEventListener("focus", () => boards.forEach(b => { b.hidden = b !== board; }));
      board.hidden = true;
      inputs.push(input);
      boards.push(board);
      return h("td", {}, input);
    })));
  state.card.paintTable = (answer, parts) => {
    inputs.forEach((input, k) => {
      input.classList.add(parts[k] ? "right" : "wrong");
      if (!parts[k]) input.after(h("span", { class: "fix el", lang: "el" }, `→ ${answer[k]}`));
    });
    boards.forEach(b => { b.hidden = true; });
  };
  if (boards[0]) boards[0].hidden = false;
  return h("article", { class: "card" }, rubricLine(card.rubric, card.ask), stimulusBlock(card),
    card.prompt?.el ? greekText(card.prompt.el, { tag: "p", cls: "prompt-greek" }) : null,
    h("div", { class: "table-wrap" }, h("table", { class: "fill-table" }, h("thead", {}, head), h("tbody", {}, body))),
    h("p", { class: "muted small" }, t("table_hint")),
    ...boards, row, h("div", { class: "slot" }));
};

function countWords(text) {
  return text.split(/\s+/).filter(w => /[\p{L}\p{N}]/u.test(w)).length;
}

function openTaskPrompt(card) {
  const prompt = greekText(card.prompt.el, { tag: "p", cls: "prompt-greek" });
  return [scenePictures(card.stimulus?.pictures), h("div", { class: "question" }, ...translatable(prompt, tr(card.prompt)))];
}

function skipButton() {
  if (state.mock) return null;
  return h("button", { class: "link-button", type: "button", onclick: () => submit({ skipped: true }, { skipped: true }) },
    t("skip_today"));
}

RENDERERS.write = (card) => {
  const [lo, hi] = card.words;
  const { input, board } = greekInput(() => {}, t("write_label"), { multiline: true });
  const counter = h("p", { class: "muted small word-count" }, t("word_count", { n: 0, lo, hi }));
  const save = h("button", { class: "primary", type: "button", disabled: true,
    onclick: () => submit({ text: input.value }, { typed: input }) }, t("write_save"));
  if (state.mock) {
    // In a mock, the text is saved as a draft while it is written, so an interruption loses nothing.
    let timer = null;
    input.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(() => { if (input.value.trim()) mockSave({ text: input.value }, { quiet: true }); }, 1500);
    });
  }
  input.addEventListener("input", () => {
    const n = countWords(input.value);
    counter.textContent = t("word_count", { n, lo, hi });
    counter.classList.toggle("ok", n >= lo && n <= hi);
    save.disabled = n === 0;
  });
  const convert = h("input", { type: "checkbox", checked: true, onchange: (e) => { input.convert = e.target.checked; } });
  const checklist = card.must_include?.length
    ? h("div", { class: "must" }, h("p", { class: "small" }, t("write_include")),
        h("ul", {}, card.must_include.map(m => h("li", {}, tr(m) || m.el || ""))))
    : null;
  return h("article", { class: "card write" }, rubricLine(card.rubric, card.ask), openTaskPrompt(card), checklist,
    h("div", { class: "typed-wrap" }, input), counter, board,
    h("label", { class: "small muted convert" }, convert, t("write_convert")),
    h("div", { class: "actions check-row" }, save, skipButton()), h("div", { class: "slot" }));
};

RENDERERS.speak = (card) => {
  const note = h("p", { class: "muted small" }, t("speak_hint", { seconds: card.seconds }));
  const player = h("audio", { controls: true, hidden: true });
  const recordBtn = h("button", { class: "primary", type: "button" }, `● ${t("speak_record")}`);
  const useBtn = h("button", { class: "primary", type: "button", hidden: true }, t("speak_use"));
  const aloud = h("button", { class: "secondary", type: "button", onclick: () => submit({ done: true }, {}) }, t("speak_aloud"));
  let recorder = null;
  let chunks = [];
  let blob = null;
  let timer = null;
  const stop = () => { if (recorder && recorder.state === "recording") recorder.stop(); };
  recordBtn.addEventListener("click", async () => {
    if (recorder && recorder.state === "recording") return stop();
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      note.textContent = t("speak_no_mic");
      return;
    }
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      note.textContent = t("speak_no_mic");
      return;
    }
    const type = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg", "audio/mp4"].find(x => MediaRecorder.isTypeSupported(x));
    recorder = new MediaRecorder(stream, type ? { mimeType: type } : {});
    chunks = [];
    recorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
    recorder.onstop = () => {
      clearTimeout(timer);
      stream.getTracks().forEach(tr => tr.stop());
      blob = new Blob(chunks, { type: (recorder.mimeType || "audio/webm").split(";")[0] });
      player.src = URL.createObjectURL(blob);
      player.hidden = false;
      useBtn.hidden = false;
      recordBtn.textContent = `● ${t("speak_again")}`;
      note.textContent = t("speak_listen_back");
    };
    recorder.start();
    recordBtn.textContent = `■ ${t("speak_stop")}`;
    note.textContent = t("speak_recording");
    timer = setTimeout(stop, card.seconds * 2000);
  });
  useBtn.addEventListener("click", async () => {
    if (!blob) return;
    useBtn.disabled = true;
    try {
      const res = await fetch("/api/recording", { method: "POST", headers: { "Content-Type": blob.type || "audio/webm" }, body: blob });
      if (!res.ok) throw new Error(String(res.status));
      const { recording } = await res.json();
      submit({ recording }, {});
    } catch { useBtn.disabled = false; note.textContent = t("error"); }
  });
  const useful = card.useful?.length
    ? h("div", { class: "useful" }, h("p", { class: "small" }, t("speak_useful")),
        h("ul", {}, card.useful.map(u => h("li", {}, greekText(u, { cls: "el" })))))
    : null;
  return h("article", { class: "card speak-card" }, rubricLine(card.rubric, card.ask), openTaskPrompt(card), useful, note,
    h("div", { class: "actions" }, recordBtn, useBtn), player,
    h("div", { class: "actions check-row" }, aloud, skipButton()), h("div", { class: "slot" }));
};

function openTaskFeedback(card, result, ui) {
  // Writing and speaking are not marked by the app: the coach marks them later.
  const parts = [];
  if (ui.skipped) {
    parts.push(h("p", {}, t("skipped_line")));
  } else if (card.type === "write") {
    parts.push(h("p", { class: "verdict" }, t("write_saved")), h("p", {}, t("write_saved_line")));
  } else {
    parts.push(h("p", { class: "verdict" }, t("speak_done")));
    if (result.submission_id) parts.push(h("p", {}, t("speak_saved_line")));
    if (card.model?.el) {
      parts.push(h("p", { class: "small" }, t("speak_model")),
        h("div", { class: "example" }, speakButton(card.model.el, true),
          h("div", {}, greekText(card.model.el, { tag: "p", cls: "el" }),
            tr(card.model) ? h("p", { class: "translation" }, tr(card.model)) : null)));
    }
  }
  return parts;
}

async function submit(response, ui = {}) {
  const c = state.card;
  if (state.mock) return mockSave(response, ui);
  if (!c || c.answered) return;
  c.answered = true;
  closePopover();
  cardRoot().querySelectorAll(".option, .tf button, .check-row button, .typed, .keyboard .k, .speak-card .actions button")
    .forEach(b => { b.disabled = true; });
  let result;
  try {
    result = await api("/api/attempt", {
      session_id: state.session.session_id,
      item_key: c.data.item_key,
      card: c.data,
      response,
      latency_ms: Math.round(performance.now() - c.started),
      audio_plays: c.audioPlays,
      lookups: c.lookups,
    });
  } catch { return showError(); }
  showFeedback(result, ui);
}

function showFeedback(result, ui) {
  const card = state.card.data;
  const slot = cardRoot().querySelector(".slot");
  const parts = [];
  if (state.card.revealTranscript) state.card.revealTranscript();

  if (card.type === "write" || card.type === "speak") {
    cardRoot().querySelector(".check-row")?.remove();
    const last = state.session.index >= state.session.cards.length - 1;
    const next = nextButton(last);
    slot.replaceChildren(h("div", { class: "feedback neutral", role: "status" }, ...openTaskFeedback(card, result, ui)),
      h("div", { class: "actions" }, next));
    next.focus();
    return;
  }

  if (card.type === "vocab" && card.direction === "meaning_el_typed") {
    ui.typed?.classList.add(result.correct ? "right" : "wrong");
    if (!result.correct) parts.push(h("p", {}, t("answer_is", { answer: result.answer })));
    parts.push(h("div", { class: "example" }, speakButton(result.answer, true), greekText(result.answer, { cls: "el" })));
  } else if (card.type === "vocab" || card.type === "mcq") {
    const buttons = [...cardRoot().querySelectorAll(".option")];
    const rightIndex = card.type === "mcq" ? result.answer : card.options.indexOf(result.answer);
    buttons.forEach((b, i) => {
      if (i === rightIndex) b.classList.add("right");
      else if (i === ui.pickedIndex) b.classList.add("wrong");
    });
    if (!result.correct) {
      const answerText = card.type === "mcq" ? card.options[result.answer]
        : card.direction === "el_picture" ? card.meaning : result.answer;
      parts.push(h("p", {}, t("answer_is", { answer: answerText })));
    }
    if (card.type === "vocab" && card.picture && card.direction !== "el_picture") {
      parts.push(h("img", { class: "word-picture small", src: card.picture, alt: "", width: "120", height: "120" }));
    }
    if (card.type === "vocab" && card.direction !== "el_meaning") {
      parts.push(h("div", { class: "example" }, speakButton(card.speak, true), greekText(card.el || card.speak, { cls: "el" })));
    }
  } else if (card.type === "form") {
    for (const [g, input] of Object.entries(ui.formInputs || {})) {
      const el = input.el || input;
      el.classList.add(result.parts.length && result.correct ? "right" : "wrong");
    }
    cardRoot().querySelectorAll(".option").forEach((b, i) => {
      const text = b.lastChild.textContent;
      if (Object.values(result.answer).includes(text)) b.classList.add("right");
      else if (i === ui.pickedIndex) b.classList.add("wrong");
    });
    const right = Object.values(result.answer).join(", ");
    parts.push(h("div", { class: "example" }, speakButton(card.text.replace(/\{(\w+)\}/g, (_, g) => result.answer[g]), true),
      greekText(card.text.replace(/\{(\w+)\}/g, (_, g) => result.answer[g]), { tag: "p", cls: "el" })));
    if (!result.correct) parts.push(h("p", {}, t("answer_is", { answer: right })));
  } else if (card.type === "true_false") {
    cardRoot().querySelectorAll(".statement").forEach((row, i) => {
      const right = result.answer[i];
      row.querySelectorAll(".tf button").forEach(b => {
        const value = b.dataset.value === "true";
        if (value === right) b.classList.add("right");
        else if (value === state.card.tf[i]) b.classList.add("wrong");
      });
      const ok = result.parts[i];
      row.querySelector(".tf").append(h("span", { class: `mark ${ok ? "good" : "bad"}`, "aria-hidden": "true" }, ok ? "✓" : "✗"));
    });
    parts.push(h("p", {}, t("parts_score", { right: result.parts.filter(Boolean).length, total: result.parts.length })));
  } else {
    if (card.type === "match") state.card.paintMatch(result.answer, result.parts);
    if (card.type === "gap_bank") state.card.paintGaps(result.answer, result.parts);
    if (card.type === "categorise") state.card.paintCats(result.answer, result.parts);
    if (card.type === "table_fill") state.card.paintTable(result.answer, result.parts);
    parts.push(h("p", {}, t("parts_score", { right: result.parts.filter(Boolean).length, total: result.parts.length })));
  }
  cardRoot().querySelector(".check-row")?.remove();

  if (result.accent_note) parts.push(h("p", { class: "accent-note" }, t("accent_note", { word: result.accent_note })));
  if (result.example) {
    parts.push(h("div", { class: "example" },
      speakButton(result.example.el, true),
      h("div", {},
        greekText(result.example.el, { tag: "p", cls: "el" }),
        tr(result.example) ? h("p", { class: "translation" }, tr(result.example)) : null)));
  }
  if (result.translation && tr(result.translation)) parts.push(h("p", { class: "translation" }, tr(result.translation)));
  const explain = tr(result.explain);
  if (explain) parts.push(h("p", { class: "muted" }, explain));
  if (!result.correct && result.next_due) parts.push(h("p", { class: "muted small" }, t("comes_back")));

  const last = state.session.index >= state.session.cards.length - 1;
  const next = nextButton(last);
  slot.replaceChildren(
    h("div", { class: `feedback ${result.correct ? "good" : "bad"}`, role: "status" },
      h("p", { class: "verdict" }, result.correct ? (result.accent_note ? t("right_accent") : t("right")) : t("wrong")), ...parts),
    h("div", { class: "actions" }, next));
  next.focus();
}

function nextButton(last) {
  // In a chapter's "try it" block the button stays inside the chapter.
  if (state.inline) {
    return h("button", { class: "primary", type: "button", id: "next", onclick: inlineNext }, last ? t("ch_check_back") : t("next"));
  }
  return h("button", { class: "primary", type: "button", id: "next", onclick: nextCard }, last ? t("finish") : t("next"));
}

function nextCard() {
  const s = state.session;
  if (!s) return;
  if (s.index >= s.cards.length - 1) return finishSession();
  s.index += 1;
  renderCard();
}

async function finishSession() {
  const s = state.session;
  if (!s) return go("home");
  state.session = null;
  state.card = null;
  closePopover();
  let sum;
  try {
    sum = await api(`/api/session/${s.session_id}/end`, {});
  } catch { return showError(); }
  renderSummary(sum);
}

function renderSummary(sum) {
  const lines = [];
  if (sum.check) {
    lines.push(h("p", { class: sum.check.passed ? "line good-line" : "line" },
      t(sum.check.passed ? "check_passed" : "check_failed", { pct: Math.round(sum.check.score * 100), need: Math.round(sum.check.needed * 100) })));
  }
  if (sum.written) lines.push(h("p", { class: "line" }, t("summary_written")));
  if (!sum.done && !sum.written) {
    lines.push(h("p", { class: "line" }, t("summary_none")));
  } else if (!sum.done) {
    /* only writing or speaking this time */
  } else {
    lines.push(h("p", { class: "line" }, t(sum.done === 1 ? "summary_line_one" : "summary_line",
      { done: sum.done, right: sum.right, minutes: Math.max(1, Math.round(sum.minutes)) })));
    for (const [area, v] of Object.entries(sum.by_area)) {
      lines.push(h("p", { class: "muted" }, t("summary_area", { area: areaName(area), right: v.right, done: v.done })));
    }
    if (sum.right === sum.done) lines.push(h("p", {}, t("summary_perfect")));
  }
  if (sum.left) lines.push(h("p", { class: "muted" }, t("summary_left", { n: sum.left })));
  lines.push(h("p", {}, t("summary_tomorrow", { n: sum.due_tomorrow })));
  const missed = sum.missed?.length
    ? [h("h2", {}, t("summary_missed")),
       h("ul", {}, sum.missed.map(w => h("li", {}, greekText(w.el, { cls: "el" }), speakButton(w.say || w.el, true), h("span", { class: "muted" }, w.meaning))))]
    : [];
  const done = h("button", { class: "primary", type: "button", onclick: () => go("home") }, t("done"));
  const head = lines.shift();
  const total = sum.done + (sum.left || 0);
  const rope = sum.done && total ? h("div", { class: "today-rope" },
    h("span", { class: "small muted" }, t("summary_rope")), ropeBar(sum.done, total),
    h("span", { class: "small muted" }, t("summary_rope_line", { done: sum.done, total }))) : null;
  app.replaceChildren(
    ...appBar(null),
    h("section", { class: "summary done-day" },
      h("div", { class: "done-head" }, donkey("resting", 76), h("div", {}, h("h1", {}, t("summary_title")), head)),
      rope,
      ...lines,
      ...missed,
      h("div", { class: "actions" },
        done,
        h("button", { class: "secondary", type: "button", onclick: () => startSession(sum.left ? "daily" : "extra") },
          sum.left ? t("continue_daily", { left: sum.left }) : t("more5")))));
  done.focus();
}

// ---------- writing and speaking, with the coach's feedback ----------

function wordDiff(before, after) {
  // Word-level longest common subsequence: which words of each text the other one lacks.
  const a = before.split(/(\s+)/).filter(Boolean);
  const b = after.split(/(\s+)/).filter(Boolean);
  const key = (w) => w.toLowerCase().replace(/[.,;:!?«»"'()·]/g, "");
  const n = a.length, m = b.length;
  const L = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) {
    L[i][j] = key(a[i]) === key(b[j]) ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
  }
  const keepA = new Set(), keepB = new Set();
  for (let i = 0, j = 0; i < n && j < m;) {
    if (key(a[i]) === key(b[j])) { keepA.add(i); keepB.add(j); i++; j++; }
    else if (L[i + 1][j] >= L[i][j + 1]) i++;
    else j++;
  }
  const render = (tokens, keep, cls) => h("p", { class: "el diff", lang: "el" },
    tokens.map((tok, i) => /^\s+$/.test(tok) ? tok : keep.has(i) ? tok : h("mark", { class: cls }, tok)));
  return [render(a, keepA, "del"), render(b, keepB, "ins")];
}

function topbarBack(onBack) {
  return h("header", { class: "topbar" }, wordmark(),
    h("button", { class: "link-button", type: "button", onclick: onBack }, t("back")));
}

async function renderWriting() {
  closePopover();
  let res;
  try { res = await api("/api/submissions"); } catch { return showError(); }
  const rows = res.submissions.map(s => h("li", {},
    h("button", { class: "sub-row", type: "button", onclick: () => go("submission", s.id) },
      h("span", { class: "muted small" }, `${fmtDate(s.ts)} · ${t(s.kind === "speaking" ? "kind_speaking" : "kind_writing")}`),
      h("span", { class: "el", lang: "el" }, (s.prompt?.el || "").slice(0, 90) + ((s.prompt?.el || "").length > 90 ? "…" : "")),
      h("span", { class: `badge ${s.status}` }, s.status === "marked" ? t("status_marked") : t("status_waiting")))));
  app.replaceChildren(...appBar(null),
    h("section", { class: "summary writing" }, h("h1", {}, t("your_writing")),
      rows.length ? h("ul", { class: "sub-list" }, rows) : h("p", { class: "muted" }, t("no_writing"))));
}

async function renderSubmission(id) {
  closePopover();
  let s;
  try { s = await api(`/api/submissions/${id}`); } catch { return showError(); }
  const fb = s.feedback;
  const blocks = [h("h1", {}, t(s.kind === "speaking" ? "kind_speaking" : "kind_writing")),
    h("p", { class: "muted small" }, fmtDate(s.ts) + (s.word_count ? ` · ${t("words_n", { n: s.word_count })}` : "")),
    s.prompt?.el ? h("div", { class: "rubric" }, ...translatable(greekText(s.prompt.el, { tag: "p", cls: "el" }), tr(s.prompt))) : null];
  if (!fb) blocks.push(h("p", { class: "coach-note" }, t("feedback_waiting")));
  if (fb?.summary) blocks.push(h("div", { class: "coach-note" }, h("p", {}, fb.summary)));
  if (fb?.score && fb.score.points != null) {
    const sc = fb.score;
    blocks.push(h("div", { class: "score" },
      h("p", { class: "score-line" }, t("score_line", { points: sc.points, out_of: sc.out_of ?? "?", exam: sc.exam === "b1-keg" ? "B1" : sc.exam === "a2ltr" ? "A2" : (sc.exam || "") })),
      sc.criteria?.length ? h("table", { class: "criteria" }, sc.criteria.map(c => h("tr", {},
        h("td", {}, c.name), h("td", { class: "num" }, c.points != null ? `${c.points}/${c.out_of ?? "?"}` : ""),
        h("td", { class: "muted small" }, c.comment || "")))) : null,
      h("p", { class: "muted small" }, t(sc.unverified ? "score_estimate_unverified" : "score_estimate"))));
  }
  if (s.kind === "writing") {
    if (fb?.corrected) {
      const [orig, corr] = wordDiff(s.text || "", fb.corrected);
      blocks.push(h("div", { class: "side-by-side" },
        h("div", {}, h("h2", {}, t("you_wrote")), orig),
        h("div", {}, h("h2", {}, t("corrected")), corr, speakButton(fb.corrected, true))));
    } else {
      blocks.push(h("h2", {}, t("you_wrote")), h("p", { class: "el diff", lang: "el" }, s.text || ""));
    }
  } else {
    if (s.recording) blocks.push(h("audio", { controls: true, src: s.recording }));
    const heard = fb?.heard ?? s.transcript;
    if (heard != null) blocks.push(h("h2", {}, t("heard")), h("p", { class: "el diff", lang: "el" }, heard || "…"));
    if (fb?.corrected) blocks.push(h("h2", {}, t("better")), h("div", { class: "example" }, speakButton(fb.corrected, true), greekText(fb.corrected, { tag: "p", cls: "el" })));
    if (s.model?.el) blocks.push(h("h2", {}, t("speak_model")), h("div", { class: "example" }, speakButton(s.model.el, true), greekText(s.model.el, { tag: "p", cls: "el" })));
  }
  if (fb?.errors?.length) {
    blocks.push(h("h2", {}, t("errors_title")), h("ol", { class: "errors" }, fb.errors.map(e => h("li", {},
      h("p", {}, h("del", { class: "el", lang: "el" }, e.original), " → ", h("strong", { class: "el", lang: "el" }, e.fix)),
      h("p", { class: "muted" }, e.why)))));
  }
  if (fb?.exercises?.length) {
    blocks.push(h("div", { class: "actions" }, h("button", { class: "secondary", type: "button",
      onclick: () => startSession("practice", fb.exercises) }, t("practise_these", { n: fb.exercises.length }))));
  }
  app.replaceChildren(...appBar(null), crumb("writing", t("your_writing")), h("section", { class: "summary writing" }, ...blocks));
}


// ---------- the course: where you are, what you know, what you choose (phase 5b) ----------

const STATUS_KEYS = { new: "st_new", learning: "st_learning", secure: "st_secure", known: "st_known" };

function stageName(st) {
  return tr(st.title) || st.id;
}

function ringLabel(title, position) {
  // The lesson's number inside its ring, unless the title already carries one ("Ders 1"):
  // a book's own numbering need not match the position, which counts the intro too.
  return /\d/.test(title || "") ? "" : String(position);
}

function progressBar(done, total, cls = "") {
  return ropeBar(done, total, cls);
}

function wordStrip(words) {
  // Words with their pictures (phase 9); a word without one gets a plain Greek tile.
  return h("div", { class: "word-strip" }, words.map(w => h("figure", { class: "nw", title: w.meaning || "" },
    w.picture ? h("img", { src: w.picture, alt: w.meaning || "", width: "120", height: "120" })
              : h("span", { class: "nw-plain" }, w.meaning || ""),
    h("figcaption", { lang: "el" }, w.el))));
}

function lessonTile(cur, words) {
  // The current lesson: its ring and rope, how far it is, its own words, what to do with it.
  if (!cur) return null;
  const st = cur.current;
  const actions = [];
  if (st.chapter) {
    actions.push(h("button", { class: "secondary small-btn", type: "button", onclick: () => go("lesson", st.id) },
      icon("book"), st.chapter.read ? t("ch_reread_short") : t("ch_read_min", { minutes: st.chapter.minutes })));
  }
  if (!st.chapter || st.chapter.read) {
    actions.push(h("button", { class: "secondary small-btn", type: "button",
      onclick: () => startSession("choose", [], { what: "all", stage: st.id, minutes: 10 }) }, t("stage_practise")));
  }
  return h("section", { class: "tile lesson-tile" },
    h("p", { class: "eyebrow" }, t("home_lesson", { n: cur.stages_done + 1, total: cur.stages_total })),
    h("button", { class: "lesson-head", type: "button", onclick: () => go("stage", st.id) },
      ropeRing(st.core ? st.learned / st.core : 0, ringLabel(stageName(st), cur.stages_done + 1), 56),
      h("span", {}, h("strong", { class: "lesson-name" }, stageName(st)),
        st.theme ? h("span", { class: "muted lesson-theme" }, tr(st.theme)) : null)),
    progressBar(st.learned, st.core),
    h("p", { class: "small muted" }, [st.core ? t("stage_secure", { n: st.learned, total: st.core }) : t("stage_nothing"),
      st.chapter?.read ? ` · ✓ ${t("ch_was_read")}` : ""].join("")),
    words?.lesson?.length ? [h("p", { class: "eyebrow strip-head" }, t("home_in_lesson")), wordStrip(words.lesson)] : null,
    cur.next ? h("p", { class: "small muted" }, t("stage_next", { name: stageName(cur.next) })) : null,
    h("div", { class: "tile-actions" }, actions));
}

const LEVEL_NAMES = { A1: "lvl_a1", A2: "lvl_a2", B1: "lvl_b1" };

function picStrip(pics, n = 3, size = 44) {
  // A few of a lesson's words, as small pictures (phase 9)
  if (!pics?.length) return null;
  return h("div", { class: "pic-strip" }, pics.slice(0, n).map(p =>
    h("img", { src: p.picture, alt: p.meaning || p.el, title: p.el, width: String(size), height: String(size), loading: "lazy" })));
}

function lessonStatus(st) {
  const ch = st.chapter;
  if (st.state === "done") return [t("bk_done", { pct: Math.round((st.share || 0) * 100) }), "done"];
  if (st.state === "current") return [ch && !ch.read ? t("bk_now_read", { minutes: ch.minutes }) : t("bk_now_practise"), "now"];
  if (ch?.read) return [t("bk_read_ahead_done"), "later"];
  if (ch) return [t("bk_later_read", { minutes: ch.minutes }), "later"];
  return [t("bk_later"), "later"];
}

async function renderBook() {
  // The book: where you are (one big card), then every lesson by level, each with its ring and a few of its pictures.
  closePopover();
  let cur, pods;
  try { [cur, pods] = await Promise.all([api("/api/curriculum"), podcastsByStage()]); } catch { return showError(); }
  if (!cur.curriculum) return go("home", null, { replace: true });
  const pics = cur.pictures || {};
  const idx = Math.max(0, cur.stages.findIndex(s => s.id === cur.current?.id));
  const cst = cur.stages[idx];

  const actions = [];
  if (cst.chapter) {
    actions.push(h("button", { class: cst.chapter.read ? "secondary" : "primary", type: "button", onclick: () => go("lesson", cst.id) },
      icon("book"), cst.chapter.read ? t("ch_reread_short") : t("ch_read_min", { minutes: cst.chapter.minutes })));
  }
  if (cst.state !== "locked" && (!cst.chapter || cst.chapter.read)) {
    actions.push(h("button", { class: "primary", type: "button", onclick: () => startSession("choose", [], { what: "all", stage: cst.id, minutes: 10 }) }, t("stage_practise")));
  }
  if (pods[cst.id]) actions.push(podListenLink(pods[cst.id], "secondary-link"));
  actions.push(navLink("stage", t("bk_see_lesson"), cst.id, "secondary-link"));
  const heroPics = pics[cst.id] || [];
  const hero = h("section", { class: "bk-hero", "aria-label": t("bk_here") },
    h("div", { class: "bk-hero-main" },
      h("p", { class: "eyebrow accent" }, t("bk_here")),
      h("div", { class: "bk-hero-head" },
        ropeRing(cst.core ? cst.learned / cst.core : 0, ringLabel(stageName(cst), idx + 1), 72),
        h("div", { class: "bk-hero-names" },
          h("h2", {}, cst.chapter ? tr(cst.chapter.title) : stageName(cst)),
          h("p", { class: "muted" }, [stageName(cst), cst.core ? t("bk_words_forms", { n: cst.core }) : null].filter(Boolean).join(" · ")))),
      cst.can_do?.length ? h("p", { class: "bk-can" }, t("bk_can", { what: cst.can_do.slice(0, 2).map(tr).join("; ") }))
        : cst.theme ? h("p", {}, tr(cst.theme)) : null,
      cst.core ? h("div", { class: "bk-rope" }, ropeBar(cst.learned, cst.core),
        h("span", { class: "small muted" }, t("stage_secure", { n: cst.learned, total: cst.core }))) : null,
      h("div", { class: "tile-actions" }, actions)),
    heroPics.length ? h("div", { class: "bk-hero-words" }, h("p", { class: "eyebrow" }, t("home_in_lesson")), wordStrip(heroPics)) : null);

  const groups = [];
  cur.stages.forEach((st, i) => {
    let g = groups.find(x => x.level === st.level);
    if (!g) groups.push(g = { level: st.level, items: [] });
    g.items.push([st, i]);
  });
  const sections = groups.map(g => {
    const done = g.items.filter(([s]) => s.state === "done").length;
    const tiles = g.items.map(([st, i]) => {
      const [line, kind] = lessonStatus(st);
      const frac = st.state === "done" ? 1 : st.core && st.state !== "locked" ? st.share : 0;
      return h("article", { class: `bk-tile ${st.state}${st.id === cst.id ? " here" : ""}` },
        h("div", { class: "bk-tile-head" },
          ropeRing(frac, st.state === "done" ? "✓" : ringLabel(stageName(st), i + 1), 48),
          h("div", { class: "bk-tile-names" }, navLink("stage", stageName(st), st.id, "bk-title"),
            st.chapter ? h("span", { class: "bk-chapter" }, tr(st.chapter.title)) : st.theme ? h("span", { class: "bk-chapter" }, tr(st.theme)) : null)),
        picStrip(pics[st.id]),
        h("div", { class: "bk-tile-foot" }, h("span", { class: `bk-state ${kind}` }, line),
          pods[st.id] ? navLink("podcast", [icon("headphones"), t("pod_listen_short")], pods[st.id], "bk-read") : null,
          st.chapter ? navLink("lesson", [icon("book"), st.chapter.read ? t("ch_reread_short") : t("bk_read")], st.id, "bk-read") : null));
    });
    const head = h("div", { class: "bk-group-head" },
      h("h2", {}, `${g.level} · ${t(LEVEL_NAMES[g.level] || "lvl_other")}`),
      h("span", { class: "small muted" }, t("bk_group_done", { n: done, total: g.items.length })));
    const here = g.items.some(([s]) => s.id === cst.id);
    if (here || g.items.length <= 3) return h("section", { class: "bk-group" }, head, h("div", { class: "bk-grid" }, tiles));
    return h("details", { class: "bk-group" }, h("summary", {}, head), h("div", { class: "bk-grid" }, tiles));
  });

  app.replaceChildren(...appBar("book"),
    h("section", { class: "bk-head" },
      h("div", { class: "bk-head-text" }, h("p", { class: "eyebrow" }, t("bk_eyebrow")), h("h1", {}, tr(cur.title)),
        h("p", { class: "muted" }, t("book_line", { n: cur.stages.filter(s => s.chapter).length, total: cur.stages.length })),
        h("p", { class: "bk-films" }, navLink("films", [icon("film"), t("films_link_book")], null, "tile-link"))),
      h("div", { class: "bk-total" }, h("span", {}, h("strong", {}, `${cur.stages_done} / ${cur.stages_total}`), " ",
        h("span", { class: "muted" }, t("bk_lessons_done"))), ropeBar(cur.stages_done, cur.stages_total))),
    hero, ...sections);
}

function statusChip(status) {
  return h("span", { class: `chip st-${status}` }, t(STATUS_KEYS[status] || status));
}

async function renderStage(id) {
  closePopover();
  let st;
  try { st = await api(`/api/curriculum/stages/${encodeURIComponent(id)}`); } catch { return showError(); }
  const words = st.words_list.map(w => h("li", { class: "word-row" },
    speakButton(w.say || w.el, true), greekText(w.el, { cls: "el", tappable: false }), h("span", { class: "muted" }, meaningText(w.meaning, w.meaning_lang)), statusChip(w.status)));
  const byLemma = {};
  for (const f of st.forms_list) (byLemma[f.lemma || "?"] ||= []).push(f);
  const forms = Object.entries(byLemma).map(([lemma, fs]) => h("li", {},
    h("span", { class: "el", lang: "el" }, lemma), " ",
    h("span", { class: "muted small" }, `${fs.filter(f => f.status === "secure" || f.status === "known").length}/${fs.length}`)));
  const actions = [];
  if (st.chapter) {
    actions.push(h("button", { class: st.chapter.read ? "secondary" : "primary", type: "button", onclick: () => go("lesson", st.id) },
      st.chapter.read ? t("ch_reread") : t("ch_read_min", { minutes: st.chapter.minutes })));
  }
  if (st.state !== "locked") {
    actions.push(h("button", { class: "primary", type: "button", onclick: () => startSession("choose", [], { what: "all", stage: st.id, minutes: 10 }) }, t("stage_practise")));
  }
  if (st.can_check && st.state !== "done") {
    actions.push(h("button", { class: "secondary", type: "button", onclick: () => startCheck(st.id) }, t("stage_check")));
  }
  app.replaceChildren(...appBar("book"), crumb("book", t("nav_book")),
    h("section", { class: "summary" },
      h("h1", {}, stageName(st)), st.theme ? h("p", { class: "muted" }, tr(st.theme)) : null,
      h("p", {}, h("span", { class: `chip map-${st.state}` }, t(`map_${st.state}`)), " ",
        st.core ? t("stage_secure", { n: st.learned, total: st.core }) : t("stage_nothing")),
      st.core ? progressBar(st.learned, st.core) : null,
      st.core ? h("p", { class: "muted small" }, t("stage_secure_line", { n: st.secure, days: 6 })) : null,
      st.state === "locked" ? h("p", { class: "muted small" }, t("stage_locked_line")) : null,
      st.chapter && !st.chapter.read && st.state !== "locked" ? h("p", { class: "muted small" }, t("stage_read_first")) : null,
      st.can_do?.length ? h("div", { class: "coach-note" }, h("p", { class: "small" }, h("strong", {}, t("stage_can_do"))),
        h("ul", { class: "small" }, st.can_do.map(c => h("li", {}, tr(c))))) : null,
      actions.length ? h("div", { class: "actions" }, actions) : null,
      st.can_check && st.state !== "done" ? h("p", { class: "muted small" }, t("stage_check_line")) : null,
      words.length ? [h("h2", {}, t("stage_words", { n: words.length })), h("ul", { class: "word-list" }, words)] : null,
      forms.length ? [h("h2", {}, t("stage_forms", { n: st.forms_list.length })), h("ul", { class: "lemma-list" }, forms)] : null,
      st.tasks_list.length ? h("p", { class: "muted" }, t("stage_tasks", { n: st.tasks_list.length, seen: st.tasks_list.filter(x => x.seen).length })) : null,
      st.extra_words ? h("p", { class: "muted small" }, t("stage_extra", { n: st.extra_words })) : null));
}

const PR_KINDS = [  // the tiles: the choice, its icon and its tint; words show one of the lesson's pictures
  ["words", "book", "accent"], ["verbs", "pen", "accent"], ["reading", "book", "accent"],
  ["listening", "headphones", "accent"], ["writing", "pen", "bad"], ["speaking", "mic", "good"],
];
const PR_SECONDS = { words: 20, verbs: 30, reading: 90, listening: 90, writing: 360, speaking: 120, all: 30, review: 25 };

async function renderPractise() {
  // Choose one thing to practise: tiles that say how much is waiting, and a summary of the session you are about to start.
  closePopover();
  let cur, counts;
  try {
    [cur, counts] = await Promise.all([api("/api/curriculum").catch(() => ({ curriculum: null })), api("/api/practise")]);
  } catch { return showError(); }
  const pick = { what: "words", stage: "", minutes: 10 };
  const reached = (cur.stages || []).filter(st => st.state !== "locked");
  const pics = cur.pictures || {};
  const wordPic = (pics[cur.current?.id] || Object.values(pics).flat())[0];
  const tiles = h("section", { class: "pr-tiles", "aria-label": t("pr_what") });
  const aside = h("aside", { class: "pr-aside", "aria-label": t("pr_session") });

  const line = (what) => {
    if (what === "all") return t("pr_all_line");
    if (what === "review") return t("pr_review_line", { due: counts.review.due, mistakes: counts.review.mistakes });
    const c = counts[what];
    if (!c || !c.total) return t("pr_none_yet");
    return c.new ? t("pr_count", { due: c.due, new: c.new }) : t("pr_count_due", { due: c.due });
  };
  const empty = (what) => what !== "all" && what !== "review" && !counts[what]?.total;

  function tile(what, iconName, tint, wide = false) {
    const visual = what === "words" && wordPic
      ? h("img", { src: wordPic.picture, alt: "", width: "72", height: "72", class: "pr-pic" })
      : h("span", { class: `pr-icon ${tint}` }, icon(iconName));
    return h("button", { type: "button", class: `pr-tile${wide ? " wide" : ""}`, "aria-pressed": String(pick.what === what), disabled: empty(what),
      onclick: () => { pick.what = what; paint(); } },
      visual, h("span", { class: "pr-tile-text" }, h("strong", {}, t(`pr_${what}`)), h("span", { class: "small muted" }, line(what))));
  }

  function paint() {
    tiles.replaceChildren(
      ...PR_KINDS.map(([w, ic, tint]) => tile(w, ic, tint)),
      tile("all", "target", "accent", true),
      tile("review", "flag", "bad", true));
    const c = pick.what === "review" ? { due: counts.review.due, new: 0 } : pick.what === "all" ? null : counts[pick.what];
    const n = Math.max(1, Math.round((pick.minutes * 60) / (PR_SECONDS[pick.what] || 30)));
    const chip = (value, label) => h("button", { type: "button", class: "choice", "aria-pressed": String(pick.stage === value),
      onclick: async () => { pick.stage = value; await refresh(); } }, label);
    const recent = reached.slice(-2).reverse();
    const others = reached.filter(st => !recent.includes(st));
    aside.replaceChildren(
      h("h2", {}, `${t(`pr_${pick.what}`)} · ${t("minutes_n", { n: pick.minutes })}`),
      cur.curriculum ? h("div", { class: "pr-field" }, h("p", { class: "eyebrow" }, t("pr_from")),
        h("div", { class: "choice-row" }, chip("", t("pr_so_far")), recent.map(st => chip(st.id, stageName(st)))),
        others.length ? h("select", { class: "stage-select", "aria-label": t("pr_other_stage"), onchange: async (e) => { pick.stage = e.target.value; await refresh(); } },
          h("option", { value: "" }, t("pr_other_stage")), others.map(st => h("option", { value: st.id, selected: pick.stage === st.id }, stageName(st)))) : null) : null,
      h("div", { class: "pr-field" }, h("p", { class: "eyebrow" }, t("pr_length")),
        h("div", { class: "segmented", role: "group", "aria-label": t("pr_length") }, [5, 10, 20].map(m =>
          h("button", { type: "button", "aria-pressed": String(pick.minutes === m), onclick: () => { pick.minutes = m; paint(); } }, t("minutes_n", { n: m }))))),
      h("div", { class: "pr-estimate" },
        h("p", {}, t("pr_about", { n })),
        c ? h("ul", { class: "small muted" },
          c.due ? h("li", {}, t("pr_due_first", { n: Math.min(c.due, n) })) : null,
          c.new && c.due < n ? h("li", {}, t("pr_new_then")) : null) : h("p", { class: "small muted" }, t("pr_line"))),
      h("button", { class: "start", type: "button", onclick: () => startSession("choose", [], { what: pick.what, stage: pick.stage || null, minutes: pick.minutes }) }, t("pr_start")));
  }

  async function refresh() {
    try { counts = await api(`/api/practise${pick.stage ? `?stage=${encodeURIComponent(pick.stage)}` : ""}`); } catch { /* keep the old counts */ }
    if (empty(pick.what)) pick.what = "all";
    paint();
  }

  paint();
  app.replaceChildren(...appBar("practise"),
    h("section", { class: "pr-head" }, h("p", { class: "eyebrow" }, t("pr_eyebrow")), h("h1", {}, t("pr_title")), h("p", { class: "muted" }, t("pr_sub"))),
    h("div", { class: "pr-layout" }, tiles, aside));
}

async function renderWords() {
  // Every word as a card with its picture; search, filters, and practise the ones you pick.
  closePopover();
  let data;
  try { data = await api("/api/words"); } catch { return showError(); }
  const f = { q: "", status: "all", pics: false, stage: "", upcoming: false, shown: 60 };
  const selected = new Set();
  const grid = h("section", { class: "wd-grid", "aria-label": t("nav_words") });
  const count = h("p", { class: "small muted" });
  const more = h("button", { class: "link-button", type: "button", onclick: () => { f.shown += 120; paint(); } }, t("w_more"));
  const barText = h("span", {});
  const bar = h("div", { class: "wd-bar", hidden: true }, barText,
    h("button", { class: "primary", type: "button", onclick: () => startSession("practice", [...selected]) }, t("pr_start")));
  const fold = (x) => x.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  const open = data.words.filter(w => w.open);
  const learned = open.filter(w => w.status === "secure" || w.status === "known").length;
  const learning = open.filter(w => w.status === "learning").length;
  const withPic = data.words.filter(w => w.picture).length;

  function updateBar() {
    bar.hidden = selected.size === 0;
    barText.textContent = t("wd_bar", { n: selected.size });
  }

  function card(w) {
    const box = h("input", { type: "checkbox", class: "wd-check", "aria-label": t("wd_select", { word: w.el }), disabled: !w.open,
      onchange: (e) => { if (e.target.checked) selected.add(w.key); else selected.delete(w.key); updateBar(); } });
    box.checked = selected.has(w.key);
    const visual = w.picture
      ? h("img", { src: w.picture, alt: w.meaning || "", width: "200", height: "200", loading: "lazy" })
      : h("span", { class: "wd-plain", lang: "el" }, w.el.replace(/^(ο|η|το|οι|τα|ο\/η) /, ""));
    const state = w.open ? t(STATUS_KEYS[w.status] || w.status) : t("w_locked");
    return h("article", { class: `wd-card st-${w.open ? w.status : "locked"}` },
      h("div", { class: "wd-visual" }, visual, box),
      h("div", { class: "wd-body" },
        h("div", { class: "wd-row" }, h("strong", { lang: "el" }, w.el), speakButton(w.say || w.el, true)),
        h("span", { class: "small muted wd-meaning" }, meaningText(w.meaning, w.meaning_lang)),
        h("span", { class: "wd-state" }, w.open ? null : icon("lock"), state)));
  }

  function paint() {
    const q = fold(f.q.trim());
    const rows = data.words.filter(w => (f.upcoming || w.open)
      && (f.status === "all" || w.status === f.status || (f.status === "secure" && w.status === "known"))
      && (!f.pics || w.picture)
      && (!f.stage || w.stage === f.stage)
      && (!q || fold(w.el).includes(q) || fold(w.meaning || "").includes(q)));
    count.textContent = t("w_count", { n: rows.length, total: data.words.length });
    grid.replaceChildren(...rows.slice(0, f.shown).map(card));
    more.hidden = rows.length <= f.shown;
  }

  const chip = (label, on, onclick) => h("button", { type: "button", class: "choice", "aria-pressed": String(on), onclick }, label);
  const filters = h("div", { class: "choice-row" });
  function paintFilters() {
    filters.replaceChildren(
      ...["all", "new", "learning", "secure"].map(v => chip(v === "all" ? t("w_all") : t(STATUS_KEYS[v]), f.status === v, () => { f.status = v; f.shown = 60; paintFilters(); paint(); })),
      chip(t("wd_pics"), f.pics, () => { f.pics = !f.pics; f.shown = 60; paintFilters(); paint(); }));
  }
  paintFilters();
  const search = h("label", { class: "wd-search" }, icon("search"),
    h("input", { type: "search", placeholder: t("w_search"), "aria-label": t("w_search"), oninput: (e) => { f.q = e.target.value; f.shown = 60; paint(); } }));
  const stageSel = data.stages.length ? h("select", { class: "stage-select", "aria-label": t("pr_stage"), onchange: (e) => { f.stage = e.target.value; paint(); } },
    h("option", { value: "" }, t("w_every_stage")), data.stages.map(st => h("option", { value: st.id }, tr(st.title)))) : null;
  const upcoming = h("label", { class: "small muted convert" }, h("input", { type: "checkbox", onchange: (e) => { f.upcoming = e.target.checked; paint(); } }), t("w_upcoming"));
  const counter = (n, label, frac) => h("div", { class: "wd-counter" }, ropeRing(frac, "", 40), h("span", {}, h("strong", {}, n.toLocaleString(state.lang === "tr" ? "tr-TR" : "en-GB")), h("br"), h("span", { class: "small muted" }, label)));
  const total = Math.max(1, open.length);
  app.replaceChildren(...appBar("words"),
    h("section", { class: "wd-head" },
      h("div", {}, h("p", { class: "eyebrow" }, t("nav_words")), h("h1", {}, t("wd_title", { n: data.words.length.toLocaleString(state.lang === "tr" ? "tr-TR" : "en-GB"), p: withPic }))),
      h("div", { class: "wd-counters" }, counter(learned, t("wd_learned"), learned / total), counter(learning, t("wd_learning"), learning / total),
        counter(open.length - learned - learning, t("wd_unseen"), 0))),
    h("section", { class: "wd-filters", "aria-label": t("wd_find") }, search, filters, stageSel, upcoming),
    count, grid, more, bar);
  paint();
}

const PERSONS = ["1sg", "2sg", "3sg", "1pl", "2pl", "3pl"];

async function renderVerbs() {
  closePopover();
  let data;
  try { data = await api("/api/verbs"); } catch { return showError(); }
  const rows = data.verbs.map(v => {
    const ORDER = ["present", "future", "aorist", "imperfect", "subjunctive", "imperative", "perfect"];
    const tenses = [...new Set(v.forms.map(f => f.tense))].sort((x, y) => (ORDER.indexOf(x) + 99) % 99 - (ORDER.indexOf(y) + 99) % 99);
    const table = h("table", { class: "verb-table" },
      h("thead", {}, h("tr", {}, h("th", {}), tenses.map(tn => h("th", {}, tenseName(tn))))),
      h("tbody", {}, PERSONS.filter(pn => v.forms.some(f => f.person === pn)).map(pn => h("tr", {},
        h("th", { scope: "row" }, t(`person_${pn}`)),
        tenses.map(tn => {
          const f = v.forms.find(x => x.person === pn && x.tense === tn);
          if (!f) return h("td", {});
          return h("td", { class: `vf ${f.open ? f.status : "locked"}`, lang: "el", title: f.open ? t(STATUS_KEYS[f.status]) : t("w_locked") },
            f.open ? f.form : icon("lock"));
        })))));
    const practise = v.open ? h("button", { class: "link-button small", type: "button", onclick: () => startSession("choose", [], { what: "verbs", lemma: v.lemma, minutes: 5 }) }, t("v_practise")) : null;
    return h("details", { class: `verb${v.open ? "" : " locked"}` },
      h("summary", {}, h("span", { class: "el", lang: "el" }, v.lemma), " ",
        h("span", { class: "muted small" }, v.open ? t("v_known", { n: v.known, total: v.forms.length }) : t("w_locked"))),
      h("div", { class: "table-wrap" }, table), practise);
  });
  // Lesson by lesson: the lessons reached come first, each under its name; the verbs of later
  // lessons wait in one folded group, so the page is not a long list of greyed-out rows.
  const stages = data.stages || [];
  const current = data.current ?? -1;
  const groups = new Map();
  data.verbs.forEach((v, i) => {
    const key = v.first_stage < stages.length ? v.first_stage : -1;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(rows[i]);
  });
  const reached = [], later = [];
  for (const [idx, list] of groups) {
    const st = stages[idx];
    const head = h("h2", { class: "verb-group" }, st ? t("v_lesson", { n: idx + 1, title: tr(st.title) }) : t("v_group_none"),
      h("span", { class: "muted small" }, ` · ${list.length}`));
    (idx >= 0 && idx > current ? later : reached).push(head, ...list);
  }
  const laterCount = data.verbs.filter(v => v.first_stage < stages.length && v.first_stage > current).length;
  const laterFold = later.length ? h("details", { class: "verb-later" },
    h("summary", {}, t("v_group_later", { n: laterCount })), later) : null;
  app.replaceChildren(...appBar("verbs"),
    h("section", { class: "summary verbs-page" }, h("h1", {}, t("nav_verbs")), h("p", { class: "muted small" }, t("v_line")),
      reached, laterFold));
}

// ---------- the chapter reader: read first, then practise (phase 5c) ----------

function inlineText(text, tag = "p") {
  // **bold**, *italic*, [[Greek]] (tappable and spoken). Nothing else is markup.
  const el = h(tag, {});
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|\[\[[^\]]+\]\])/g;
  for (const part of String(text).split(re)) {
    if (!part) continue;
    if (part.startsWith("**") && part.endsWith("**")) el.append(h("strong", {}, part.slice(2, -2)));
    else if (part.startsWith("[[") && part.endsWith("]]")) el.append(greekText(part.slice(2, -2), { cls: "el inline-el" }));
    else if (part.startsWith("*") && part.endsWith("*") && part.length > 2) el.append(h("em", {}, part.slice(1, -1)));
    else el.append(document.createTextNode(part));
  }
  return el;
}

function paragraphs(text) {
  return String(text).split(/\n{2,}|\n/).filter(x => x.trim()).map(x => inlineText(x));
}

async function speakAll(lines) {
  // lines: strings or {text, role}; a dialogue is read line by line, each in its speaker's voice
  if (!canSpeak() || !lines.length) return;
  stopSpeaking();
  const run = speakRun;
  for (const ln of lines) {
    if (run !== speakRun) return;
    const { text, role } = typeof ln === "string" ? { text: ln, role: "f" } : ln;
    await say(text, 0.85, role, run);
  }
}

const CHAPTER_BLOCKS = {
  prose: (b) => h("div", { class: "ch-prose" }, paragraphs(tr(b))),

  dialogue: (b) => {
    const lines = b.lines.map(ln => h("div", { class: "ch-line" },
      h("span", { class: "who", lang: "el" }, ln.who),
      h("div", { class: "said" },
        h("div", { class: "said-el" }, greekText(ln.el, { cls: "el" }), speakButton(ln.el, true, ln.role)),
        h("p", { class: "translation", hidden: true }, tr(ln)))));
    const toggle = h("button", { class: "link-button small", type: "button" }, t("ch_show_tr"));
    toggle.addEventListener("click", () => {
      const show = toggle.textContent === t("ch_show_tr");
      lines.forEach(l => { l.querySelector(".translation").hidden = !show; });
      toggle.textContent = show ? t("ch_hide_tr") : t("ch_show_tr");
    });
    const play = h("button", { class: "secondary small-btn play-all", type: "button", onclick: () => speakAll(b.lines.map(l => ({ text: l.el, role: l.role }))) }, `▶ ${t("ch_play_all")}`);
    play.hidden = !canSpeak();
    return h("div", { class: "ch-dialogue" },
      scenePicture(b.picture, b.picture_alt ? tr(b.picture_alt) : (b.setting ? tr(b.setting) : "")),
      b.setting ? h("p", { class: "setting" }, tr(b.setting)) : null,
      h("div", { class: "ch-tools" }, play, toggle),
      lines);
  },

  table: (b) => h("figure", { class: "ch-table" },
    b.caption ? h("figcaption", {}, inlineText(tr(b.caption), "span")) : null,
    h("div", { class: "table-wrap" }, h("table", {},
      // a cell is Greek (a string) or an explanation in both languages ({tr, en})
      h("thead", {}, h("tr", {}, b.head.map(c => h("th", {}, typeof c === "string" ? greekText(c, { tappable: false }) : inlineText(tr(c), "span"))))),
      // a row headed in Greek has a ▶ (`says`: a letter is read as its alphabet card says it, "άλφα. ταξί")
      h("tbody", {}, b.rows.map((row, i) => h("tr", {}, row.map((c, j) => h(j === 0 ? "th" : "td", j === 0 ? { scope: "row" } : {},
        typeof c === "string" ? greekText(c, { cls: "el" }) : inlineText(tr(c), "span"),
        j === 0 && b.says?.[i] ? speakButton(b.says[i], true) : null))))))),
    b.note ? h("p", { class: "muted small" }, inlineText(tr(b.note), "span")) : null),

  examples: (b) => h("ul", { class: "ch-examples" }, b.items.map(e => h("li", {},
    h("div", { class: "said-el" }, greekText(e.el, { cls: "el" }), speakButton(e.el, true)),
    h("p", { class: "translation" }, tr(e)),
    e.note ? h("p", { class: "muted small" }, inlineText(tr(e.note), "span")) : null))),

  words: (b) => h("ul", { class: "word-list ch-words" }, (b.words || []).map(w => h("li", { class: "word-row" },
    speakButton(w.say || w.el, true), h("span", { class: "el", lang: "el" }, w.el), h("span", { class: "muted" }, meaningText(w.meaning, w.meaning_lang)),
    statusChip(w.status)))),

  tip: (b) => h("aside", { class: `ch-tip ${b.kind}` }, h("p", { class: "tip-label" }, t(`ch_tip_${b.kind}`)), paragraphs(tr(b))),

  check: (b, ctx) => {
    const box = h("div", { class: "ch-check" });
    const idle = () => box.replaceChildren(
      h("p", { class: "check-title" }, t("ch_check_title", { n: b.items.length })),
      h("button", { class: "primary", type: "button", onclick: () => startInlineChecks(ctx.stage, b.items, box, idle) }, t("ch_check_start")),
      h("p", { class: "muted small" }, t("ch_check_note")));
    if (!b.items.length) return null;
    idle();
    return box;
  },
};

function sectionFlag(stage, index) {
  const btn = h("button", { class: "flag ch-flag", type: "button", title: t("ch_flag"), "aria-label": t("ch_flag") }, icon("flag"));
  btn.addEventListener("click", async () => {
    const note = window.prompt(t("ch_flag"));
    if (note === null) return;
    try {
      await api(`/api/chapters/${encodeURIComponent(stage)}/flag`, { section: index, note });
      btn.textContent = "✓";
      btn.title = t("ch_flag_thanks");
      btn.disabled = true;
    } catch { /* the flag is optional */ }
  });
  return btn;
}

async function renderChapter(stageId) {
  resetScreens();
  let ch;
  const podsP = podcastsByStage();
  try { ch = await api(`/api/chapters/${encodeURIComponent(stageId)}`); } catch {
    app.replaceChildren(...appBar("book"), h("div", { class: "center-note" }, t("ch_none")));
    return;
  }
  const seen = new Set(ch.read?.sections || []);
  const bar = h("span", { style: `width:${Math.round((seen.size / ch.sections.length) * 100)}%` });
  const ctx = { stage: stageId };
  const sections = ch.sections.map((sec, i) => h("section", { class: `ch-sec kind-${sec.kind}`, id: `sec-${i}`, "data-i": i },
    h("div", { class: "ch-sec-head" }, h("h2", {}, sec.title ? tr(sec.title) : t(`ch_kind_${sec.kind}`)), sectionFlag(stageId, i)),
    sec.blocks.map(b => (CHAPTER_BLOCKS[b.type] || (() => null))(b, ctx))));
  const contents = h("details", { class: "ch-contents" }, h("summary", {}, t("ch_contents")),
    h("ol", {}, ch.sections.map((sec, i) => h("li", {}, h("a", { href: `#sec-${i}`, onclick: (e) => {
      e.preventDefault();
      document.getElementById(`sec-${i}`)?.scrollIntoView({ behavior: "smooth" });
    } }, sec.title ? tr(sec.title) : t(`ch_kind_${sec.kind}`))))));
  const markRead = async () => {
    try { await api(`/api/chapters/${encodeURIComponent(stageId)}/progress`, { finished: true }); } catch { /* fine */ }
  };
  // A lesson not reached yet can be read ahead; its practice opens when the learner gets there.
  const ahead = ch.state === "locked";
  const end = h("section", { class: "ch-end" },
    h("p", { class: "muted" }, t(ahead ? "ch_end_ahead" : "ch_end_line")),
    ahead
      ? h("button", { class: "start", type: "button", onclick: async () => { await markRead(); go(ch.next_chapter ? "lesson" : "book", ch.next_chapter?.id ?? null); } },
          t(ch.next_chapter ? "ch_done_next" : "ch_done_book"))
      : h("button", { class: "start", type: "button", onclick: () => startChapterPractice(stageId) }, t("ch_done_practise")),
    ahead ? null : h("div", { class: "actions" }, h("button", { class: "link-button", type: "button", onclick: async () => {
      await markRead();
      go("home");
    } }, t("ch_later"))),
    h("nav", { class: "ch-pager", "aria-label": t("nav_book") },
      ch.prev_chapter ? navLink("lesson", `← ${tr(ch.prev_chapter.title)}`, ch.prev_chapter.id, "pager-prev") : h("span", {}),
      navLink("book", t("nav_book"), null, "pager-index"),
      ch.next_chapter ? navLink("lesson", `${tr(ch.next_chapter.title)} →`, ch.next_chapter.id, "pager-next") : h("span", {})));
  const pods = await podsP;
  const podLine = pods[stageId] ? h("p", { class: "ch-pod" }, podListenLink(pods[stageId])) : null;
  app.replaceChildren(
    ...appBar("book"),
    h("div", { class: "reader-progress", role: "progressbar", "aria-valuemin": 0, "aria-valuemax": 100 }, bar),
    crumb("book", t("nav_book")),
    h("article", { class: "reader" },
      h("p", { class: "kicker" }, `${tr(ch.stage_title)} · ${t("ch_meta", { level: ch.level, minutes: ch.minutes })}`),
      h("h1", { class: "ch-title" }, tr(ch.title)),
      podLine, contents, sections, end));
  window.scrollTo(0, 0);
  // A section counts as seen once most of it has been on screen.
  if ("IntersectionObserver" in window) {
    const obs = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (!e.isIntersecting) continue;
        const i = Number(e.target.dataset.i);
        obs.unobserve(e.target);
        if (seen.has(i)) continue;
        seen.add(i);
        bar.style.width = `${Math.round((seen.size / ch.sections.length) * 100)}%`;
        api(`/api/chapters/${encodeURIComponent(stageId)}/progress`, { section: i }).catch(() => {});
      }
    }, { threshold: 0.35 });
    app.querySelectorAll(".ch-sec").forEach(el => obs.observe(el));
  }
}

async function startChapterPractice(stageId) {
  resetScreens();
  app.replaceChildren(h("div", { class: "center-note" }, t("loading")));
  try {
    const s = await api(`/api/chapters/${encodeURIComponent(stageId)}/practice`, { has_voice: canSpeak() });
    if (!s.cards.length) {
      app.replaceChildren(...appBar(null), h("div", { class: "center-note" }, t("nothing")));
      return;
    }
    state.session = { ...s, index: 0 };
    renderCard();
  } catch { showError(); }
}

// "Try it" inside the chapter: the normal card renderers, drawn into the block.

async function startInlineChecks(stageId, items, box, idle) {
  if (state.inline) state.inline.idle();
  if ("speechSynthesis" in window) speechSynthesis.cancel();
  let s;
  try { s = await api(`/api/chapters/${encodeURIComponent(stageId)}/checks`, { items }); } catch { return; }
  state.session = { ...s, index: 0 };
  state.inline = { box, idle, right: 0 };
  state.cardRoot = box;
  renderInlineCard();
}

function renderInlineCard() {
  closePopover();
  const s = state.session;
  const card = s.cards[s.index];
  state.card = { data: card, answered: false, started: performance.now(), audioPlays: 0, lookups: 0, tf: [], picks: {} };
  const body = (RENDERERS[card.type] || RENDERERS.mcq)(card);
  body.prepend(h("p", { class: "muted small" }, t("ch_check_n", { n: s.index + 1, total: s.cards.length })));
  state.cardRoot.replaceChildren(body);
}

async function inlineNext() {
  const s = state.session;
  const inline = state.inline;
  if (!s || !inline) return;
  if (s.index < s.cards.length - 1) {
    s.index += 1;
    renderInlineCard();
    inline.box.scrollIntoView({ behavior: "smooth", block: "nearest" });
    return;
  }
  state.session = null;
  state.card = null;
  state.cardRoot = null;
  state.inline = null;
  let sum = null;
  try { sum = await api(`/api/session/${s.session_id}/end`, {}); } catch { /* the answers are saved already */ }
  inline.box.replaceChildren(
    sum && sum.done ? h("p", { class: sum.right === sum.done ? "check-title good-line" : "check-title" },
      t("ch_check_result", { right: sum.right, total: sum.done })) : null,
    h("button", { class: "link-button", type: "button", onclick: () => inline.idle() }, t("ch_check_again")));
}

// ---------- exam readiness ----------

const UNIT_KEYS = { history: "unit_history", listening: "unit_listening", reading: "unit_reading", writing: "unit_writing", speaking: "unit_speaking" };
const unitName = (u) => t(UNIT_KEYS[u] || u);
const num = (x) => (x === null || x === undefined ? "–" : (Math.round(x * 10) / 10).toLocaleString(state.lang === "tr" ? "tr-TR" : "en-GB"));
let homeExam = null;

function chosenExam(ids) {
  try { const saved = localStorage.getItem("gc-exam"); if (ids.includes(saved)) return saved; } catch { /* private mode */ }
  const target = state.home?.target_exam;
  return ids.includes(target) ? target : ids.includes("b1-keg") ? "b1-keg" : ids[0];
}

function readinessBar(u) {
  // The scale is the unit's points; the pass line is marked; the estimate is a range, not a dot.
  const pct = (x) => `${Math.max(0, Math.min(100, (x / u.points) * 100))}%`;
  const bar = h("span", { class: `rbar ${u.state}` },
    h("span", { class: "passline", style: `left:${pct(u.pass_line)}`, title: t("pass_line", { n: num(u.pass_line) }) }));
  if (u.state !== "no_evidence") {
    bar.append(h("span", { class: "range", style: `left:${pct(u.low)};width:calc(${pct(u.high)} - ${pct(u.low)})` }),
      h("span", { class: "est", style: `left:${pct(u.estimate)}` }));
  }
  return bar;
}

function unitLine(u) {
  if (u.state === "no_evidence") {
    return u.marked_by === "coach" && u.evidence === 0 ? t("r_not_scored")
      : u.reason === "major_task_missing" ? t("r_task_missing")
      : t("r_not_enough", { n: u.evidence, need: u.evidence_needed });
  }
  return t("r_estimate", { est: num(u.estimate), low: num(u.low), high: num(u.high), points: num(u.points), line: num(u.pass_line) });
}

function verdictText(v, short) {
  // The verdict, then which units decide it: below the line, too close, or without evidence.
  const parts = [t(`verdict_${v.state}`, { exam: short })];
  if (v.state === "no_evidence") return parts[0];
  const list = (units) => (units || []).map(unitName).join(", ");
  if (v.below?.length) parts.push(t("verdict_below", { units: list(v.below) }));
  if (v.unclear?.length) parts.push(t("verdict_close", { units: list(v.unclear) }));
  if (v.no_evidence?.length) parts.push(t("verdict_none", { units: list(v.no_evidence) }));
  return parts.join(" ");
}

function examTile(home) {
  // A short "would you pass today?": the verdict, one small bar per part, and the way to the exam screen.
  const brief = home.readiness;
  if (!brief) return null;
  const ids = Object.keys(brief);
  homeExam = homeExam && ids.includes(homeExam) ? homeExam : chosenExam(ids);
  const r = brief[homeExam];
  const sw = h("div", { class: "lang-switch exam-switch", role: "group", "aria-label": t("exam") },
    ...ids.map(id => h("button", { type: "button", "aria-pressed": String(id === homeExam), onclick: () => {
      homeExam = id;
      try { localStorage.setItem("gc-exam", id); } catch { /* fine */ }
      rerender();
    } }, brief[id].short)));
  const rows = r.units.map(u => h("div", { class: "area runit mini" },
    h("span", { class: "area-name" }, unitName(u.unit)), readinessBar(u)));
  return h("section", { class: "tile exam-tile" },
    h("div", { class: "tile-top" }, h("p", { class: "eyebrow" }, icon("target"), t("exam_today")), sw),
    h("p", { class: "weakest" }, verdictText({ state: r.verdict, ...Object.fromEntries(["below", "unclear", "no_evidence"].map(st => [st, r.units.filter(u => u.state === st).map(u => u.unit)])) }, r.short)),
    h("div", { class: "areas" }, rows),
    navLink("exam", [t("home_exam_link"), icon("arrow")], null, "tile-link"));
}

function techniqueBlock(u) {
  const lines = (state.lang === "tr" && u.technique.tr?.length ? u.technique.tr : u.technique.en);
  return h("details", { class: "technique" }, h("summary", {}, `${unitName(u.id)} · ${t("minutes_n", { n: u.minutes })} · ${num(u.points)} ${t("points")}`),
    h("ul", {}, lines.map(l => h("li", {}, l))), u.note ? h("p", { class: "muted small" }, tr(u.note)) : null);
}

function planSection(data) {
  const p = data.plan;
  const blocks = [h("h2", {}, t("plan_title"))];
  if (!p) {
    blocks.push(h("p", { class: "muted" }, t("plan_none")));
  } else {
    blocks.push(h("p", { class: `plan-verdict ${p.verdict.realistic}` }, (state.lang === "tr" && p.verdict.tr) || p.verdict.en));
    if (p.stale) blocks.push(h("p", { class: "warn" }, t("plan_stale", { date: fmtDate(p.made_at) })));
    if (p.short_weeks) blocks.push(h("p", { class: "warn" }, t("plan_behind", { n: p.short_weeks })));
    const cur = p.weeks_so_far.find(w => w.state === "current");
    const show = [...(cur ? [cur] : []), ...p.next_weeks].slice(0, 5);
    blocks.push(h("ol", { class: "plan-weeks" }, show.map(w => h("li", { class: w.state || "next" },
      h("div", { class: "plan-week-head" }, h("strong", {}, t("week_of", { date: fmtDate(w.start) })),
        h("span", { class: "muted small" }, w.state === "current" ? t("plan_done_so_far", { done: Math.round(w.done_minutes), planned: w.minutes }) : t("plan_minutes", { n: w.minutes }))),
      h("p", {}, tr(w.content)),
      w.focus?.length ? h("p", { class: "muted small" }, w.focus.map(f => f === "foundations" ? t("foundations") : unitName(f)).join(" · ")) : null,
      w.checkpoint ? h("p", { class: "small" }, `✓ ${tr(w.checkpoint)}`) : null))));
    const past = p.weeks_so_far.filter(w => w.state !== "current").slice(-4);
    if (past.length) {
      blocks.push(h("p", { class: "muted small" }, t("plan_past"), " ",
        past.map(w => `${fmtDate(w.start)}: ${Math.round(w.done_minutes)}/${w.minutes} min`).join(" · ")));
    }
  }
  const pi = data.plan_inputs;
  const facts = pi.candidates.map(c => h("li", {}, t("candidate_line", {
    exam: data.exams.find(e => e.id === c.exam)?.short || c.exam, date: fmtDate(c.date), weeks: Math.round(c.weeks_left),
    closes: c.registration_closes ? fmtDate(c.registration_closes) : "–", hours: Math.round(c.hours_at_pace),
    need: `${c.hours_needed[0]}–${c.hours_needed[1]}` })));
  for (const id of pi.exams_without_announced_date) {
    facts.push(h("li", {}, t("candidate_none", { exam: data.exams.find(e => e.id === id)?.short || id })));
  }
  blocks.push(h("h3", {}, t("dates_title")), h("ul", { class: "facts" }, facts),
    h("p", { class: "muted small" }, t("pace_line", { pace: pi.pace.minutes_week == null ? "–" : Math.round(pi.pace.minutes_week),
      budget: pi.budget_minutes_week ?? "–", hours: num(pi.pace.hours_total) })));
  return h("section", { class: "panel" }, ...blocks);
}

function mocksSection(data) {
  const blocks = [h("h2", { id: "mocks" }, t("mocks_title"))];
  const defs = data.mocks.defined;
  const runs = data.mocks.runs;
  if (!defs.length) blocks.push(h("p", { class: "muted" }, t("mocks_none")));
  for (const d of defs) {
    const run = runs.find(r => r.mock_id === d.id && r.status === "running");
    const done = runs.find(r => r.mock_id === d.id && r.status !== "running");
    const exam = data.exams.find(e => e.id === d.blueprint);
    blocks.push(h("div", { class: "mock-row" },
      h("div", {}, h("strong", {}, tr(d.title) || `${exam?.short || d.blueprint} · ${fmtDate(d.created)}`),
        h("p", { class: "muted small" }, d.sections.map(s => `${unitName(s.unit)} ${s.minutes}′`).join(" · ")),
        d.problems.length ? h("p", { class: "warn small" }, d.problems.join("; ")) : null),
      d.ok && !done ? h("button", { class: run ? "primary" : "secondary", type: "button", onclick: async () => {
        try { const r = await api(`/api/mocks/${encodeURIComponent(d.id)}/start`, {}); renderMockRun(r.run_id); } catch { showError(); }
      } }, run ? t("mock_continue") : t("mock_start")) : null));
  }
  const past = runs.filter(r => r.status !== "running");
  if (past.length) {
    blocks.push(h("h3", {}, t("mock_results")), h("ul", { class: "facts" }, past.map(r => h("li", {},
      h("button", { class: "link-button", type: "button", onclick: () => go("mock", r.run_id) },
        `${data.exams.find(e => e.id === r.blueprint)?.short || r.blueprint} · ${fmtDate(r.started_at)}: ${num(r.total)}/${num(r.total_out_of)}`
        + (r.would_pass === true ? ` · ${t("mock_pass")}` : r.would_pass === false ? ` · ${t("mock_fail")}` : ""))))));
  }
  return h("section", { class: "panel" }, ...blocks);
}

async function renderExam() {
  closePopover();
  state.mock = null;
  let data, home;
  try { [data, home] = await Promise.all([api("/api/exam"), api("/api/home")]); } catch { return showError(); }
  const stats = home.stats;
  const progress = stats.answers_total ? h("section", { class: "progress-pair" },
    h("h2", { class: "section-title" }, t("progress_title")),
    h("div", { class: "pair" }, consistencyGrid(stats), standing(stats))) : null;
  const examCards = data.exams.map(e => {
    const r = e.readiness;
    const rows = r.units.map(u => {
      const spec = e.units.find(x => x.id === u.unit);
      const cov = e.coverage.tasks.filter(c => c.unit === u.unit);
      const mockLine = u.mock ? t("r_mock", { date: fmtDate(u.mock.date), points: num(u.mock.points), out_of: num(u.mock.out_of) })
        + (u.mock.closed_by === "time_away" ? ` · ${t("r_mock_away")}` : u.mock.unanswered ? ` · ${t("r_mock_unanswered", { n: u.mock.unanswered })}` : "")
        : t("r_untimed");
      return h("div", { class: `exam-unit ${u.state}` },
        h("div", { class: "area runit" }, h("span", { class: "area-name" }, unitName(u.unit)), readinessBar(u),
          h("span", { class: `chip state-${u.state}` }, t(`state_${u.state}`))),
        h("p", { class: "small" }, unitLine(u)),
        h("p", { class: "muted small" }, u.state === "no_evidence" ? "" : t("r_evidence", { n: u.evidence, timed: u.timed, date: u.last ? fmtDate(u.last) : "–" }), " ", mockLine),
        h("details", { class: "coverage" }, h("summary", { class: "small" }, t("coverage_title")),
          h("ul", { class: "small" }, cov.map(c => {
            const task = spec.tasks.find(x => x.id === c.id);
            return h("li", {}, `${tr(task.title)}: `, t("coverage_line", { tried: c.tried, available: c.available, unseen: c.unseen_at_level }),
              task.points_verified ? "" : ` (${t("points_unverified")})`);
          }))));
    });
    const beyond = e.coverage.beyond_a2.length
      ? h("details", { class: "coverage" }, h("summary", { class: "small" }, t("beyond_title")),
          h("ul", { class: "small" }, e.coverage.beyond_a2.map(b => h("li", { class: b.tried ? "" : "muted" },
            `${tr(b.title)}: `, b.tried ? t("beyond_tried", { n: b.tried, of: b.available }) : b.available ? t("beyond_unseen", { n: b.available }) : t("beyond_nothing")))))
      : null;
    const rings = r.units.map(u => {
      const frac = u.state === "no_evidence" ? 0 : Math.max(0, Math.min(1, u.estimate / u.points));
      return h("div", { class: `ex-ring ${u.state}` },
        ropeRing(frac, u.state === "no_evidence" ? "?" : String(Math.round(frac * 100)), 64),
        h("strong", {}, unitName(u.unit)),
        h("span", { class: "small ex-ring-state" }, t(`state_${u.state}`)));
    });
    return h("section", { class: "ex-card", "data-exam": e.id },
      h("div", { class: "ex-verdict" },
        h("div", { class: "ex-verdict-head" }, h("h2", {}, verdictText(r.verdict, e.short)),
          h("span", { class: "small muted" }, tr(e.pass_rule.text))),
        h("div", { class: "ex-rings" }, rings),
        h("div", { class: "tile-actions" },
          h("button", { class: "primary", type: "button", onclick: () => startSession("choose", [], { what: "tasks", minutes: 15 }) }, t("ex_practise")),
          h("a", { class: "secondary-link", href: "#mocks" }, t("ex_mock")))),
      h("details", { class: "ex-details" }, h("summary", {}, t("ex_details")), ...rows, beyond,
        h("details", { class: "coverage" }, h("summary", { class: "small" }, t("technique_title")), e.units.map(techniqueBlock))),
      e.sessions_note ? h("p", { class: "muted small" }, tr(e.sessions_note)) : null,
      h("p", { class: "muted small" }, t("checked_on", { date: fmtDate(e.checked_at) })));
  });
  const ids = data.exams.map(e => e.id);
  homeExam = homeExam && ids.includes(homeExam) ? homeExam : chosenExam(ids);
  examCards.forEach(c => { c.hidden = c.dataset.exam !== homeExam; });
  const exSwitch = ids.length > 1 ? h("div", { class: "lang-switch exam-switch", role: "group", "aria-label": t("exam") },
    ...data.exams.map(e => h("button", { type: "button", "aria-pressed": String(e.id === homeExam), onclick: (ev) => {
      homeExam = e.id;
      try { localStorage.setItem("gc-exam", e.id); } catch { /* fine */ }
      examCards.forEach(c => { c.hidden = c.dataset.exam !== homeExam; });
      ev.currentTarget.parentElement.querySelectorAll("button").forEach(b => b.setAttribute("aria-pressed", String(b === ev.currentTarget)));
    } }, e.short))) : null;
  app.replaceChildren(...appBar("exam"),
    h("section", { class: "ex-head" },
      h("div", {}, h("p", { class: "eyebrow" }, t("nav_exam")), h("h1", {}, t("exam_title")), h("p", { class: "muted" }, t("exam_honest"))),
      exSwitch),
    ...examCards, progress, planSection(data), mocksSection(data),
    h("p", { class: "muted small" }, t("exam_legal")));
}

// ---------- mock exams ----------

async function renderMockRun(runId) {
  closePopover();
  state.mock = null;
  let run;
  try { run = await api(`/api/mock-runs/${runId}`); } catch { return showError(); }
  let exam = null;
  try { exam = (await api("/api/exam")).exams.find(e => e.id === run.blueprint); } catch { /* names only */ }
  const open = run.sections.find(s => s.state === "open");
  const rows = run.sections.map(s => {
    const res = s.result;
    let status;
    if (s.state === "not_started") status = t("mock_not_started", { minutes: s.minutes });
    else if (s.state === "open") status = t("mock_open");
    else if (res?.points != null) status = t("mock_points_line", { points: num(res.points), out_of: num(res.out_of), line: num(s.pass_line) });
    else if (res?.status === "waiting_for_coach") status = t("mock_waiting");
    else status = t("mock_not_scored");
    const notes = [];
    if (s.closed_by === "time") notes.push(t("mock_closed_time"));
    if (s.closed_by === "time_away") notes.push(t("mock_closed_away"));
    if (res?.unanswered) notes.push(t("r_mock_unanswered", { n: res.unanswered }));
    if (res?.not_recorded) notes.push(t("mock_not_recorded", { n: res.not_recorded }));
    const can = run.status === "running" && (s.state === "open" || (s.state === "not_started" && !open));
    return h("li", { class: `mock-sec ${s.state}` },
      h("div", {}, h("strong", {}, unitName(s.unit)), h("p", { class: "small" }, status),
        notes.length ? h("p", { class: "muted small" }, notes.join(" · ")) : null),
      can ? h("button", { class: "primary", type: "button", onclick: () => s.state === "open" ? openMockSection(s.section_id) : mockIntro(run, s, exam) },
        s.state === "open" ? t("mock_continue") : t("mock_start_section")) : null);
  });
  const total = run.would_pass === null
    ? t(run.verdict_note === "unscored_parts_decide" ? "mock_total_undecided" : "mock_total_partial",
        { points: num(run.total), out_of: num(run.total_out_of) })
    : t(run.would_pass ? "mock_total_pass" : "mock_total_fail", { points: num(run.total), out_of: num(run.total_out_of) });
  app.replaceChildren(...appBar("exam"), crumb("exam", t("nav_exam")),
    h("section", { class: "summary" }, h("h1", {}, `${exam?.short || run.blueprint} · ${t("mock")}`),
      h("p", { class: "muted" }, t(run.status === "running" ? "mock_run_line" : "mock_run_done")),
      h("ol", { class: "mock-sections" }, rows),
      h("p", { class: "line" }, total),
      run.status === "running" ? h("p", {}, h("button", { class: "link-button small", type: "button", onclick: async () => {
        if (!confirm(t("mock_abandon_confirm"))) return;
        await api(`/api/mock-runs/${run.run_id}/abandon`, {}).catch(() => {});
        renderMockRun(run.run_id);
      } }, t("mock_abandon"))) : null));
}

function mockIntro(run, s, exam) {
  // Before the clock starts: how long, what the tasks are, and the technique for this section.
  const unit = exam?.units.find(u => u.id === s.unit);
  const lines = unit ? ((state.lang === "tr" && unit.technique.tr?.length) ? unit.technique.tr : unit.technique.en) : [];
  const start = h("button", { class: "start", type: "button", onclick: async () => {
    start.disabled = true;
    try {
      const view = await api(`/api/mock-runs/${run.run_id}/sections/${encodeURIComponent(s.unit)}`, {});
      enterMockSection(view);
    } catch { showError(); }
  } }, t("mock_begin", { minutes: s.minutes }));
  app.replaceChildren(topbarBack(() => renderMockRun(run.run_id)),
    h("section", { class: "summary" }, h("h1", {}, unitName(s.unit)),
      h("p", { class: "line" }, t("mock_intro", { minutes: s.minutes, items: s.items, points: num(s.points) })),
      unit ? h("ul", {}, unit.tasks.map(tk => h("li", {}, `${tr(tk.title)} · ${num(tk.points)} ${t("points")}`))) : null,
      lines.length ? h("div", { class: "coach-note" }, h("p", { class: "small" }, h("strong", {}, t("technique_title"))),
        h("ul", { class: "small" }, lines.map(l => h("li", {}, l)))) : null,
      h("p", { class: "muted small" }, t("mock_rules")),
      start));
}

async function openMockSection(sectionId) {
  let view;
  try { view = await api(`/api/mock-sections/${sectionId}`); } catch { return showError(); }
  enterMockSection(view);
}

function enterMockSection(view) {
  if (view.closed) return mockSectionResult(view);
  clearInterval(state.mock?.timer);
  state.mock = { ...view, index: 0, plays: {}, deadline: performance.now() + view.remaining_seconds * 1000 / 1, timer: null };
  // The server's clock decides; this countdown only shows it (and hands the section in at 0).
  state.mock.timer = setInterval(tickMock, 500);
  state.session = { session_id: view.session_id, cards: view.cards, index: 0, total: view.cards.length, done: 0 };
  renderCard();
}

function fmtClock(sec) {
  const s = Math.ceil(sec);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

function tickMock() {
  if (!state.mock) return;
  // With a speeded-up clock (development), real seconds count for `speed` exam seconds.
  const left = Math.max(0, (state.mock.deadline - performance.now()) / 1000);
  const el = document.getElementById("mock-clock");
  if (el) {
    el.textContent = fmtClock(left * (state.mock.speed || 1));
    el.classList.toggle("low", left * (state.mock.speed || 1) < 300);
  }
  if (left <= 0) closeMockSection("time");
}

function mockFrame(body) {
  const m = state.mock;
  const nav = h("div", { class: "mock-nav", role: "navigation", "aria-label": t("mock_questions") },
    m.cards.map((c, i) => h("button", { type: "button", class: `qn${i === m.index ? " current" : ""}${m.answers[c.item_key] ? " done" : ""}`,
      "aria-label": t("mock_question_n", { n: i + 1 }), onclick: () => gotoMock(i) }, String(i + 1))));
  const clock = h("span", { id: "mock-clock", class: "mock-clock", role: "timer", "aria-live": "off" },
    fmtClock(Math.max(0, (m.deadline - performance.now()) / 1000) * (m.speed || 1)));
  const last = m.index >= m.cards.length - 1;
  const foot = h("div", { class: "actions mock-foot" },
    m.index > 0 ? h("button", { class: "secondary", type: "button", onclick: () => gotoMock(m.index - 1) }, t("mock_prev")) : null,
    !last ? h("button", { class: "secondary", type: "button", onclick: () => gotoMock(m.index + 1) }, t("mock_next")) : null,
    h("button", { class: "primary", type: "button", onclick: () => {
      const missing = m.cards.filter(c => !m.answers[c.item_key]).length;
      if (confirm(missing ? t("mock_hand_in_missing", { n: missing }) : t("mock_hand_in_confirm"))) closeMockSection("learner");
    } }, t("mock_hand_in")));
  return [
    h("header", { class: "topbar" }, h("span", { class: "muted small" }, `${unitName(m.unit)} · ${t("progress", { done: m.index + 1, total: m.cards.length })}`), clock),
    nav, body, foot,
  ];
}

function gotoMock(i) {
  state.mock.index = i;
  state.session.index = i;
  renderCard();
}

function mockRestore(card, body) {
  // A saved answer is not shown again as clicks; a line says it is saved, and answering again replaces it.
  const saved = state.mock.answers[card.item_key];
  const slot = body.querySelector(".slot");
  if (!saved) return;
  if (card.type === "write" && saved.text) {
    const input = body.querySelector("textarea");
    if (input) { input.convert = false; input.value = saved.text; input.dispatchEvent(new Event("input")); input.convert = true; }
  }
  if (Number.isInteger(saved.choice)) body.querySelector(`.option[data-index="${saved.choice}"]`)?.classList.add("chosen");
  if (slot) slot.replaceChildren(h("p", { class: "saved-note small" }, t("mock_saved_already")));
}

async function mockSave(response, ui = {}) {
  const m = state.mock;
  const card = state.card.data;
  try {
    await api(`/api/mock-sections/${m.section_id}/answer`, { item_key: card.item_key, response });
  } catch {
    // 409: time ran out on the server. Show what happened instead of an error.
    return openMockSection(m.section_id);
  }
  m.answers[card.item_key] = response;
  document.querySelectorAll(".mock-nav .qn")[m.index]?.classList.add("done");
  if (ui.quiet) return;
  const slot = app.querySelector(".slot");
  const last = m.index >= m.cards.length - 1;
  if (slot) {
    slot.replaceChildren(h("p", { class: "saved-note small" }, t("mock_saved")),
      !last ? h("div", { class: "actions" }, h("button", { class: "primary", type: "button", id: "next", onclick: () => gotoMock(m.index + 1) }, t("mock_next"))) : null);
    document.getElementById("next")?.focus();
  }
  if (card.type === "mcq" || card.type === "vocab") {
    app.querySelectorAll(".option").forEach((b, i) => b.classList.toggle("chosen", i === ui.pickedIndex));
  }
}

async function closeMockSection(by) {
  const m = state.mock;
  if (!m || m.closing) return;
  m.closing = true;
  clearInterval(m.timer);
  // A writing draft still being typed is saved first.
  const ta = app.querySelector(".card.write textarea");
  if (ta && ta.value.trim()) await mockSave({ text: ta.value }, { quiet: true }).catch(() => {});
  let view;
  try { view = await api(`/api/mock-sections/${m.section_id}/close`, { by }); } catch { return showError(); }
  mockSectionResult(view);
}

function mockSectionResult(view) {
  clearInterval(state.mock?.timer);
  state.mock = null;
  state.session = null;
  state.card = null;
  const r = view.result || {};
  const lines = [];
  if (view.closed_by === "time") lines.push(h("p", {}, t("mock_closed_time")));
  if (view.closed_by === "time_away") lines.push(h("p", { class: "warn" }, t("mock_closed_away")));
  if (r.points != null) lines.push(h("p", { class: "line" }, t("mock_points", { points: num(r.points), out_of: num(r.out_of) })));
  else if (r.submissions?.length) lines.push(h("p", { class: "line" }, t("mock_waiting")));
  for (const [id, tk] of Object.entries(r.tasks || {})) {
    lines.push(h("p", { class: "muted small" }, `${id.split(".").pop()}: ${num(tk.points)}/${num(tk.out_of)}`));
  }
  if (r.unanswered) lines.push(h("p", { class: "muted" }, t("r_mock_unanswered", { n: r.unanswered })));
  if (r.not_recorded) lines.push(h("p", { class: "muted" }, t("mock_not_recorded", { n: r.not_recorded })));
  const back = h("button", { class: "primary", type: "button", onclick: () => renderMockRun(view.run_id) }, t("mock_back_to_run"));
  app.replaceChildren(h("header", { class: "topbar" }, wordmark()),
    h("section", { class: "summary" }, h("h1", {}, `${unitName(view.unit)}: ${t("mock_section_done")}`), ...lines,
      h("p", { class: "muted small" }, t("mock_review_hint")), h("div", { class: "actions" }, back)));
  back.focus();
}

// ---------- keyboard shortcuts ----------

document.addEventListener("keydown", (e) => {
  if (!state.card || e.altKey || e.ctrlKey || e.metaKey) return;
  if (e.target.matches?.("input, textarea")) return;
  if (!state.card.answered && /^[1-9]$/.test(e.key)) {
    const b = cardRoot().querySelector(`.option[data-index="${Number(e.key) - 1}"]`);
    if (b && !b.disabled) { e.preventDefault(); b.click(); }
  } else if (state.card.answered && e.key === "Enter") {
    const next = document.getElementById("next");
    if (next && document.activeElement !== next) { e.preventDefault(); next.click(); }
  }
});

// ---------- podcast lessons (learner/podcasts/, served by src/oknos/podcast.py; docs/PODCASTS.md) ----------

const POD_RATES = [0.8, 1, 1.25];

function podTime(s) {
  s = Math.max(0, Math.round(s || 0));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

function podTitle(ep) {
  return tr(ep.title) || ep.id;
}

function podStore(key, value) {
  // Where the learner stopped and the speed: a convenience of this device only.
  try {
    if (value === undefined) return JSON.parse(localStorage.getItem(`oknos-pod-${key}`) || "null");
    localStorage.setItem(`oknos-pod-${key}`, JSON.stringify(value));
  } catch { /* private mode: it starts from the beginning */ }
  return null;
}

async function podcastsByStage() {
  // stage id -> the episode to offer with that chapter; empty when there are none (or on any error).
  try { return (await api("/api/podcasts")).by_stage || {}; } catch { return {}; }
}

function podListenLink(id, cls = "tile-link") {
  return navLink("podcast", [icon("headphones"), t("pod_listen")], id, cls);
}

function podCard(ep, current, stage = null) {
  // A chapter's episode says which lesson it belongs to; a personal one says its day. The card opens
  // the episode's page; its buttons play it right here (in the dock) and unfold its text.
  const kind = stage ? stageName(stage) : ep.kind === "chapter" ? t("pod_kind_chapter") : t(`pod_kind_${ep.kind}`);
  const minutes = t("pod_minutes", { n: Math.max(1, Math.round((ep.seconds || 0) / 60)) });
  const line = stage ? [minutes, stage.id === state.podHere ? t("bk_here") : null]
    : [minutes, t(`pod_lang_${ep.lang}`), fmtDate(ep.date || ep.rendered?.slice(0, 10))];
  const inner = [
    h("span", { class: "eyebrow" }, icon("headphones"), kind),
    h("strong", {}, podTitle(ep)),
    h("span", { class: "small muted" }, line.filter(Boolean).join(" · "))];
  const here = stage && stage.id === state.podHere;
  const link = navLink("podcast", inner, ep.id, "pod-card-link");
  if (current) link.setAttribute("aria-current", "page");
  const play = h("button", { type: "button", class: "pod-act pod-play", "data-pod": ep.id, "aria-pressed": "false",
    onclick: () => podPlay(ep) }, icon("play"), t("pod_play"));
  const panel = h("div", { class: "pod-text", "data-pod": ep.id });
  panel.hidden = true;
  const card = h("div", { class: `pod-card${current ? " here" : ""}${here ? " pod-now" : ""}` });
  const show = h("button", { type: "button", class: "pod-act", "aria-expanded": "false",
    onclick: () => podToggleText(ep, card, panel, show) }, icon("lines"), t("pod_show_text"));
  card.append(link, h("div", { class: "pod-card-actions" }, play, show), panel);
  return card;
}

// ---------- playing an episode from its card: one dock at the bottom of the window ----------
// Any <audio data-pod> (the episode page's player or the dock) keeps the cards' Play buttons and the
// open texts in step; starting one pauses the others.

const podDock = { el: null, audio: null, title: null, ep: null };
const podTexts = new Map();  // episode id -> its lines, fetched once

function podAudioFor(id) {
  return [...document.querySelectorAll("audio[data-pod]")].find(a => a.dataset.pod === id) || null;
}

function podSyncButtons() {
  for (const b of document.querySelectorAll(".pod-play[data-pod]")) {
    const a = podAudioFor(b.dataset.pod);
    const on = !!a && !a.paused;
    if (b.getAttribute("aria-pressed") === String(on) && b.firstChild) continue;
    b.classList.toggle("on", on);
    b.setAttribute("aria-pressed", String(on));
    b.replaceChildren(icon(on ? "pause" : "play"), t(on ? "pod_pause" : "pod_play"));
  }
}

function podFollowText(audio) {
  // Mark the line being spoken in an open text of this episode, and keep it in view inside the text.
  for (const panel of document.querySelectorAll(".pod-text[data-pod]")) {
    if (panel.dataset.pod !== audio.dataset.pod || panel.hidden) continue;
    const rows = panel.querySelectorAll("li[data-t]");
    let cur = null;
    for (const li of rows) if (Number(li.dataset.t) <= audio.currentTime + 0.1) cur = li;
    if (cur && !cur.classList.contains("now")) {
      for (const li of rows) li.classList.toggle("now", li === cur);
      if (!audio.paused) panel.scrollTo({ top: Math.max(0, cur.offsetTop - panel.clientHeight / 3), behavior: "smooth" });
    }
  }
}

for (const type of ["play", "pause", "ended", "timeupdate"]) {
  // Media events do not bubble, but the capture phase on the document sees them all.
  document.addEventListener(type, (e) => {
    const a = e.target;
    if (!(a instanceof HTMLAudioElement) || !a.dataset.pod) return;
    if (type === "play") for (const other of document.querySelectorAll("audio")) if (other !== a) other.pause();
    if (type === "timeupdate") podFollowText(a);
    else podSyncButtons();
  }, true);
}

function podDockClose() {
  if (!podDock.el) return;
  podDock.audio.pause();
  podDock.audio.removeAttribute("src");
  podDock.audio.removeAttribute("data-pod");
  podDock.audio.load();
  podDock.el.hidden = true;
  podDock.ep = null;
  document.body.classList.remove("pod-docked");
  podSyncButtons();
}

function podDockLoad(ep) {
  if (!podDock.el) {
    const audio = h("audio", { controls: "", preload: "metadata" });
    let lastSave = 0;
    const save = () => podDock.ep && podStore(podDock.ep.id, { t: audio.currentTime, rendered: podDock.ep.rendered });
    audio.addEventListener("loadedmetadata", () => {
      const ep = podDock.ep;
      const rate = Number(podStore("rate")) || 1;
      audio.playbackRate = POD_RATES.includes(rate) ? rate : 1;
      // Start where the learner stopped, unless a line of the text asked for another place.
      const saved = ep && podStore(ep.id);
      if (audio.currentTime < 1 && saved && saved.rendered === ep.rendered && saved.t > 5 && saved.t < audio.duration - 10) {
        audio.currentTime = saved.t;
      }
    });
    audio.addEventListener("timeupdate", () => {
      if (Math.abs(audio.currentTime - lastSave) > 5) { lastSave = audio.currentTime; save(); }
    });
    audio.addEventListener("pause", save);
    audio.addEventListener("ended", () => podDock.ep && podStore(podDock.ep.id, { t: 0, rendered: podDock.ep.rendered }));
    podDock.title = h("div", { class: "pod-dock-title" });
    podDock.el = h("div", { class: "pod-dock", role: "region", "aria-label": t("pod_title") },
      h("div", { class: "pod-dock-in" }, podDock.title,
        h("button", { type: "button", class: "pod-dock-close", "aria-label": t("pod_close"), title: t("pod_close"), onclick: podDockClose },
          icon("close")),
        audio));
    podDock.audio = audio;
    document.body.append(podDock.el);
  }
  if (podDock.ep?.id !== ep.id) {
    podDock.audio.pause();
    podDock.ep = ep;
    podDock.audio.dataset.pod = ep.id;
    podDock.audio.src = `/podcasts/${encodeURIComponent(ep.id)}.mp3`;
    podDock.title.replaceChildren(icon("headphones"), navLink("podcast", podTitle(ep), ep.id));
    if ("mediaSession" in navigator && "MediaMetadata" in window) {
      navigator.mediaSession.metadata = new MediaMetadata({ title: podTitle(ep), artist: "Oknos", album: t("pod_title") });
    }
  }
  podDock.el.hidden = false;
  document.body.classList.add("pod-docked");
  return podDock.audio;
}

function podPlay(ep, at = null) {
  // Play or pause this episode where it already is (the page's player or the dock), else in the dock;
  // with `at`, play from that second.
  const a = podAudioFor(ep.id) || podDockLoad(ep);
  if (at !== null) {
    a.currentTime = Math.max(0, at);
    a.play().catch(() => {});
  } else if (a.paused) a.play().catch(() => {});
  else a.pause();
}

function podLineItems(lines, jump) {
  return (lines || []).map(l => {
    const row = h("li", { class: `pod-line lang-${l.lang}` },
      h("button", { type: "button", class: "pod-time link-button", onclick: () => jump(l.t), "aria-label": t("pod_play_from", { time: podTime(l.t) }) }, podTime(l.t)),
      h("span", { lang: l.lang }, l.who ? h("span", { class: "pod-who" }, `${l.who}: `) : null, l.say,
        l.speed ? h("span", { class: "small muted" }, ` (${t("pod_slow")})`) : null));
    row.dataset.t = l.t;
    return row;
  });
}

async function podToggleText(ep, card, panel, btn) {
  // Unfold the episode's text under its card (the card takes the full width); a line's time plays from there.
  const open = panel.hidden;
  panel.hidden = !open;
  card.classList.toggle("open", open);
  btn.setAttribute("aria-expanded", String(open));
  btn.replaceChildren(icon("lines"), t(open ? "pod_hide_text" : "pod_show_text"));
  if (!open || panel.dataset.loaded) return;
  panel.replaceChildren(h("p", { class: "small muted" }, "…"));
  try {
    if (!podTexts.has(ep.id)) podTexts.set(ep.id, (await api(`/api/podcasts/${encodeURIComponent(ep.id)}`)).lines || []);
  } catch {
    panel.replaceChildren(h("p", { class: "small warn" }, t("pod_text_error")));
    return;
  }
  panel.dataset.loaded = "1";
  panel.replaceChildren(h("ol", {}, podLineItems(podTexts.get(ep.id), (secs) => podPlay(ep, secs))));
  const a = podAudioFor(ep.id);
  if (a) podFollowText(a);
}

function podSections(all, cur, playing) {
  // The chapters' episodes in the book's order, grouped by level like the Book; then the personal ones.
  const stages = cur?.stages || [];
  const order = new Map(stages.map((s, i) => [s.id, i]));
  const chapters = all.filter(e => e.kind === "chapter" && order.has(e.stage)
                                   && (!e.curriculum || !cur?.curriculum?.id || e.curriculum === cur.curriculum.id));
  const byStage = new Map();
  for (const e of chapters) if (!byStage.has(e.stage)) byStage.set(e.stage, e);  // newest first from the server
  const shown = new Set([...byStage.values()].map(e => e.id));
  const groups = [];
  stages.forEach(st => {
    const e = byStage.get(st.id);
    if (!e) return;
    let g = groups.find(x => x.level === st.level);
    if (!g) groups.push(g = { level: st.level, cards: [], n: 0 });
    g.n += 1;
    g.cards.push(podCard(e, playing && e.id === playing.id, st));
  });
  const out = groups.map(g => h("section", { class: "bk-group" },
    h("div", { class: "bk-group-head" }, h("h2", {}, `${g.level} · ${t(LEVEL_NAMES[g.level] || "lvl_other")}`),
      h("span", { class: "small muted" }, t("pod_n_episodes", { n: g.n }))),
    h("div", { class: "pod-grid" }, g.cards)));
  const personal = all.filter(e => !shown.has(e.id) && e.kind !== "chapter");
  const rest = all.filter(e => !shown.has(e.id) && e.kind === "chapter");
  if (personal.length) out.push(h("section", { class: "bk-group" },
    h("div", { class: "bk-group-head" }, h("h2", {}, t("pod_personal"))),
    h("div", { class: "pod-grid" }, personal.map(e => podCard(e, playing && e.id === playing.id)))));
  if (rest.length) out.push(h("section", { class: "bk-group" },
    h("div", { class: "bk-group-head" }, h("h2", {}, t("pod_other"))),
    h("div", { class: "pod-grid" }, rest.map(e => podCard(e, playing && e.id === playing.id)))));
  return { sections: out, next: nextEpisode(stages, byStage, playing) };
}

function nextEpisode(stages, byStage, playing) {
  // After a chapter's episode, the next lesson's (if there is one).
  if (!playing || playing.kind !== "chapter") return null;
  const i = stages.findIndex(s => s.id === playing.stage);
  for (const st of stages.slice(i + 1)) if (byStage.has(st.id)) return [st, byStage.get(st.id)];
  return null;
}

async function renderPodcast(id) {
  // ?podcast: the episodes; ?podcast=<id>: one playing (parts, speed, the script), the others below.
  resetScreens();
  let data, cur;
  try {
    [data, cur] = await Promise.all([api("/api/podcasts"), api("/api/curriculum").catch(() => null)]);
  } catch { return showError(); }
  const all = data.episodes || [];
  state.podHere = cur?.current?.id || null;
  if (!all.length) {
    return app.replaceChildren(...appBar("podcast"), crumb("home", t("nav_home")),
      h("section", { class: "empty-state" }, donkey("resting", 72), h("p", {}, t("pod_none")),
        h("p", { class: "small muted" }, t("pod_none_how")), h("p", {}, navLink("home", t("nothing_back_home"), null, "secondary"))));
  }
  let ep = null;
  if (id) {
    try { ep = await api(`/api/podcasts/${encodeURIComponent(id)}`); } catch { ep = null; }
  }
  const epStage = ep?.kind === "chapter" ? (cur?.stages || []).find(s => s.id === ep.stage) : null;
  const head = h("section", { class: "bk-head pod-head" },
    h("div", { class: "bk-head-text" }, h("p", { class: "eyebrow" }, icon("headphones"), epStage ? stageName(epStage) : t("pod_eyebrow")),
      h("h1", {}, ep ? podTitle(ep) : t("pod_title")),
      h("p", { class: "muted" }, ep ? [t("pod_minutes", { n: Math.max(1, Math.round(ep.seconds / 60)) }), t(`pod_lang_${ep.lang}`)].join(" · ")
        : t("pod_lede"))));
  // Opening the page of the episode the dock is playing carries on here, from the same place.
  const carryOn = !!ep && podDock.ep?.id === ep.id && !podDock.audio.paused;
  if (ep && podDock.ep?.id === ep.id) podDockClose();
  const player = ep ? podPlayer(ep, carryOn) : null;
  const { sections, next } = podSections(all, cur, ep);
  const after = ep ? h("div", { class: "tile-actions pod-after" },
    epStage?.chapter ? navLink("lesson", [icon("book"), t("pod_read_chapter")], epStage.id, "secondary-link") : null,
    next ? navLink("podcast", [icon("headphones"), t("pod_next", { lesson: stageName(next[0]) })], next[1].id, "secondary-link") : null) : null;
  app.replaceChildren(...[...appBar("podcast"), crumb(ep ? "podcast" : "home", ep ? t("pod_title") : t("nav_home")), head, player, after,
    ep ? h("h2", { class: "films-more" }, t("pod_all")) : null, ...sections].filter(Boolean));
  podSyncButtons();
}

function podPlayer(ep, autoplay = false) {
  const audio = h("audio", { class: "pod-audio", "data-pod": ep.id, src: `/podcasts/${encodeURIComponent(ep.id)}.mp3`, preload: "metadata", controls: "" });
  const saved = podStore(ep.id);
  let rate = Number(podStore("rate")) || 1;
  if (!POD_RATES.includes(rate)) rate = 1;
  audio.addEventListener("loadedmetadata", () => {
    audio.playbackRate = rate;
    // Start where the learner stopped (unless it was the very end or the episode was made again since).
    if (saved && saved.rendered === ep.rendered && saved.t > 5 && saved.t < audio.duration - 10) audio.currentTime = saved.t;
    if (autoplay) audio.play().catch(() => {});
  });
  let lastSave = 0;
  const save = () => podStore(ep.id, { t: audio.currentTime, rendered: ep.rendered });
  audio.addEventListener("pause", save);
  audio.addEventListener("ended", () => podStore(ep.id, { t: 0, rendered: ep.rendered }));

  const jump = (secs) => {
    audio.currentTime = Math.max(0, secs);
    audio.play().catch(() => {});
  };
  const rates = h("div", { class: "pod-rates", role: "group", "aria-label": t("pod_speed") },
    POD_RATES.map(r => h("button", { type: "button", class: `chip-btn${r === rate ? " on" : ""}`, "aria-pressed": String(r === rate),
      onclick: (e) => {
        rate = r;
        audio.playbackRate = r;
        podStore("rate", r);
        for (const b of e.currentTarget.parentNode.children) {
          const on = b === e.currentTarget;
          b.classList.toggle("on", on);
          b.setAttribute("aria-pressed", String(on));
        }
      } }, `${String(r).replace(".", state.lang === "tr" ? "," : ".")}×`)));
  const skips = h("div", { class: "pod-skips" },
    h("button", { type: "button", class: "secondary small-btn", onclick: () => jump(audio.currentTime - 10) }, t("pod_back10")),
    h("button", { type: "button", class: "secondary small-btn", onclick: () => jump(audio.currentTime + 10) }, t("pod_fwd10")));

  const parts = (ep.parts || []).map((p, i) => {
    const li = h("li", {}, h("button", { type: "button", class: "pod-part", onclick: () => jump(p.t) },
      h("span", { class: "pod-time" }, podTime(p.t)), h("span", {}, p.title)));
    li.dataset.t = p.t;
    li.dataset.i = i;
    return li;
  });
  const partList = h("ol", { class: "pod-parts" }, parts);

  const lines = podLineItems(ep.lines, jump);
  const script = h("details", { class: "pod-script" }, h("summary", {}, t("pod_script")), h("ol", {}, lines));

  // Follow the playback: the current part and line are marked; the position is kept every few seconds.
  let curPart = -1;
  let curLine = -1;
  audio.addEventListener("timeupdate", () => {
    const now = audio.currentTime;
    if (Math.abs(now - lastSave) > 5) { lastSave = now; save(); }
    let p = -1;
    (ep.parts || []).forEach((x, i) => { if (x.t <= now + 0.2) p = i; });
    if (p !== curPart) {
      parts.forEach((li, i) => li.classList.toggle("now", i === p));
      curPart = p;
    }
    let l = -1;
    (ep.lines || []).forEach((x, i) => { if (x.t <= now + 0.1) l = i; });
    if (l !== curLine) {
      lines.forEach((li, i) => li.classList.toggle("now", i === l));
      curLine = l;
    }
  });

  if ("mediaSession" in navigator && "MediaMetadata" in window) {
    // The title on the phone's lock screen, and its skip buttons.
    navigator.mediaSession.metadata = new MediaMetadata({ title: podTitle(ep), artist: "Oknos", album: t("pod_title") });
    try {
      navigator.mediaSession.setActionHandler("seekbackward", () => jump(audio.currentTime - 10));
      navigator.mediaSession.setActionHandler("seekforward", () => jump(audio.currentTime + 10));
    } catch { /* not every browser has these */ }
  }

  return h("section", { class: "pod-player" },
    ep.stale ? h("p", { class: "small warn" }, t("pod_stale")) : null,
    audio,
    h("div", { class: "pod-controls" }, skips, rates),
    parts.length ? h("div", { class: "pod-parts-wrap" }, h("h2", {}, t("pod_parts")), partList) : null,
    script,
    h("p", { class: "small" }, h("a", { href: `/podcasts/${encodeURIComponent(ep.id)}.mp3`, download: `${ep.id}.mp3` }, t("pod_download"))));
}

// ---------- the films of the Oknos myth (docs/brand/animations/, served at /films/ by src/oknos/films.py) ----------

const FILM_TITLES_EL = ["Ὄκνος & το γαϊδούρι", "Ὄκνος & η γυναίκα του", "Το όνειρο"];

function filmFrame(film, embed, voice, onEnded = null) {
  // The film's own page in a frame: it plays by itself and tells us its height and when it has ended.
  const q = new URLSearchParams({ embed, lang: state.lang, voice: voice || "none" });
  const th = currentTheme();
  if (th !== "system") q.set("theme", th);
  const frame = h("iframe", { class: "film-frame", src: `/films/${film.id}.html?${q}`, title: t(`film_${film.n}`), allow: "autoplay" });
  const onMessage = (e) => {
    if (e.source !== frame.contentWindow || e.origin !== location.origin || e.data?.oknos !== "film") {
      if (!frame.isConnected && frame.dataset.loaded) window.removeEventListener("message", onMessage);
      return;
    }
    frame.dataset.loaded = "1";
    if (e.data.event === "size" && e.data.height > 0) frame.style.height = `${e.data.height}px`;
    if (e.data.event === "ended" && onEnded) onEnded();
  };
  window.addEventListener("message", onMessage);
  return frame;
}

function filmCard(film, current, pos, count) {
  const inner = [
    h("img", { class: "film-poster", src: film.poster, alt: "", loading: "lazy", width: "1200", height: "800" }),
    h("span", { class: "film-card-text" },
      h("span", { class: "eyebrow" }, icon("film"), `${pos} / ${count}`),
      h("strong", { lang: "el" }, FILM_TITLES_EL[film.n - 1]),
      h("span", { class: "small muted" }, t(`film_${film.n}`)),
      h("span", { class: "small film-card-line" }, t(`film_${film.n}_line`)))];
  if (!film.available) return h("article", { class: "film-card missing" }, ...inner);
  const a = navLink("films", inner, film.n, `film-card${current ? " here" : ""}`);
  if (current) a.setAttribute("aria-current", "page");
  return a;
}

async function renderFilms(arg) {
  // ?films: the films (film 2 is archived, not shown); ?films=<n>: one of them playing, the others below.
  resetScreens();
  let data;
  try { data = await api("/api/films"); } catch { return showError(); }
  const all = data.films || [];
  if (!all.some(f => f.available)) {
    return app.replaceChildren(...appBar(null), h("section", { class: "empty-state" }, donkey("resting", 72),
      h("p", {}, t("films_missing")), h("p", {}, navLink("home", t("nothing_back_home"), null, "secondary"))));
  }
  const film = all.find(f => f.n === Number(arg) && f.available) || null;
  const head = h("section", { class: "bk-head films-head" },
    h("div", { class: "bk-head-text" }, h("p", { class: "eyebrow" }, t("films_eyebrow")),
      h("h1", { lang: film ? "el" : null }, film ? FILM_TITLES_EL[film.n - 1] : t("films_title")),
      h("p", { class: "muted" }, film ? `${t(`film_${film.n}`)} · ${t(`film_${film.n}_line`)}` : t("films_lede"))));
  const player = film ? h("section", { class: "film-player" }, filmFrame(film, "page", data.voice),
    data.voice ? h("p", { class: "small muted film-tip" }, t("films_tip_sound")) : null) : null;
  app.replaceChildren(...[...appBar(null), crumb(film ? "films" : "home", film ? t("films_title") : t("nav_home")),
    head, player,
    film ? h("h2", { class: "films-more" }, t("films_all")) : null,
    h("div", { class: "film-grid" }, all.map((f, i) => filmCard(f, film && f.n === film.n, i + 1, all.length)))].filter(Boolean));
}

async function showWelcome() {
  // Film 1, once, the first time a new learner opens the app. Skip (or Escape) closes it at any time;
  // ending or skipping it is remembered (profile.json: welcome_film_seen). With reduced motion it waits for a tap.
  let data;
  try { data = await api("/api/films"); } catch { return; }
  const film = data.films?.[0];
  if (!film?.available || document.querySelector(".welcome")) return;
  let ended = false, told = false;
  const remember = (how) => { if (!told) { told = true; api("/api/films/welcome", { how }).catch(() => {}); } };
  const onKey = (e) => { if (e.key === "Escape") close(); };
  const close = () => {
    remember(ended ? "ended" : "skipped");
    document.removeEventListener("keydown", onKey);
    dlg.remove();
    document.getElementById("start")?.focus();
  };
  const skip = h("button", { class: "secondary welcome-skip", type: "button", onclick: close }, t("welcome_skip"));
  const body = h("div", { class: "welcome-film" });
  const play = () => body.replaceChildren(filmFrame(film, "welcome", data.voice, () => {
    ended = true;
    remember("ended");
    skip.textContent = t("welcome_start");
    skip.className = "primary welcome-skip";
    skip.focus();
  }));
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
    body.replaceChildren(h("button", { class: "welcome-poster", type: "button", onclick: play },
      h("img", { src: film.poster, alt: "" }), h("span", { class: "welcome-play" }, icon("film"), t("welcome_watch"))));
  } else play();
  const dlg = h("div", { class: "welcome", role: "dialog", "aria-modal": "true", "aria-labelledby": "welcome-title" },
    h("div", { class: "welcome-box" },
      h("div", { class: "welcome-head" },
        h("div", {}, h("h2", { id: "welcome-title" }, t("welcome_title")), h("p", { class: "small muted" }, t("welcome_line"))),
        skip),
      body));
  document.body.append(dlg);
  document.addEventListener("keydown", onKey);
  skip.focus();
}

// ---------- boot ----------

(async function boot() {
  applyTheme(currentTheme());
  let lang = navigator.language?.toLowerCase().startsWith("tr") ? "tr" : "en";
  let homeAtBoot = null;
  try {
    const home = await api("/api/home");
    homeAtBoot = home;
    if (LANGS.includes(home.ui_lang)) lang = home.ui_lang;
  } catch { /* renderHome reports it */ }
  await loadStrings(lang);
  // ?practice=pack/item,pack/item opens a practice session of those items (used by the coach).
  const params = new URLSearchParams(location.search);
  const practice = params.get("practice");
  if (practice) return startSession("practice", practice.split(",").filter(Boolean));
  // Every other screen has its own address: ?book, ?lesson=<stage>, ?stage=<id>, ?practise,
  // ?words, ?verbs, ?exam, ?writing, ?submission=<id>, ?mock=<run id> (the coach links to them).
  const r = parseRoute();
  const welcome = params.has("welcome") || (r.name === "home" && homeAtBoot?.welcome_film);
  history.replaceState(r, "", location.search ? urlFor(r.name, r.arg) : location.pathname);
  state.route = r;
  await rerender();
  // The first time a new learner opens the app: film 1, once, skippable (?welcome shows it again).
  if (welcome) showWelcome();
})();


// ---------- the voice: which provider reads the Greek (phase 10, docs/VOICE.md) ----------

const VOICE_INFO = {  // what each one costs, from the listening test of 2026-11-22
  azure: {
    pros: { en: "Microsoft's neural voices, Athina and Nestoras: the most natural in our test. Official, with your own Azure key; the free tier (500,000 characters a month) covers the whole book.",
            tr: "Microsoft'un nöral sesleri Athina ve Nestoras: testimizde en doğal sesler. Kendi Azure anahtarınla, resmî yoldan; ücretsiz katman (ayda 500.000 karakter) bütün kitaba yeter." },
    cons: { en: "Needs an Azure account and a Speech resource. The free tier makes 20 clips a minute, so the free Microsoft route below fills in the rest with the same voices.",
            tr: "Azure hesabı ve bir Speech kaynağı gerekir. Ücretsiz katman dakikada 20 klip yapar; kalanını aşağıdaki ücretsiz Microsoft yolu aynı seslerle tamamlar." },
    setup: { en: ["Sign in at azure.microsoft.com/free with a Microsoft account (a card for verification, no charge).", "Create a resource: Speech, region West Europe, pricing tier Free F0.", "Keys and Endpoint: copy KEY 1 and the region.", "Add AZURE_SPEECH_KEY=… and AZURE_SPEECH_REGION=… to learner/secrets.env."],
             tr: ["azure.microsoft.com/free adresinde Microsoft hesabınla giriş yap (kart sadece doğrulama için, ücret yok).", "Bir kaynak oluştur: Speech, bölge West Europe, fiyat katmanı Free F0.", "Keys and Endpoint: KEY 1'i ve bölgeyi kopyala.", "learner/secrets.env dosyasına AZURE_SPEECH_KEY=… ve AZURE_SPEECH_REGION=… satırlarını ekle."] },
  },
  edge: {
    pros: { en: "The same Athina and Nestoras, free, no account.", tr: "Aynı Athina ve Nestoras, bedava, hesap gerekmez." },
    cons: { en: "Unofficial (the Edge browser's read-aloud service): Microsoft can slow it or close it, and the clips are for this computer only, never to share. Clips already made keep working.",
            tr: "Resmî değil (Edge tarayıcısının sesli okuma servisi): Microsoft yavaşlatabilir ya da kapatabilir; klipler yalnızca bu bilgisayar içindir, paylaşılmaz. Yapılmış klipler çalışmaya devam eder." },
    setup: { en: ["Say yes to it once (your agent asks; it is kept as edge_tts_ok in your profile).", "The agent makes the clips with: uv run oknos voice build"],
             tr: ["Bir kez evet de (ajanın sorar; profilinde edge_tts_ok olarak kalır).", "Klipleri ajan yapar: uv run oknos voice build"] },
  },
  google: {
    pros: { en: "Google's newest voices (Chirp 3 HD Kore and Orus), close behind Microsoft in our test. Your own key; 1 million characters free a month, and the whole book is about a tenth of that. The clips are yours.",
            tr: "Google'ın en yeni sesleri (Chirp 3 HD Kore ve Orus), testimizde Microsoft'un hemen ardından. Kendi anahtarınla; ayda 1 milyon karakter bedava, bütün kitap bunun onda biri. Klipler senin." },
    cons: { en: "Needs a Google Cloud project with billing turned on (the free trial covers it; no charge inside the free quota).",
            tr: "Faturalandırması açık bir Google Cloud projesi gerekir (ücretsiz deneme bunu karşılar; ücretsiz kota içinde ücret yok)." },
    setup: { en: ["console.cloud.google.com: start the free trial and create a project.", "Enable the Cloud Text-to-Speech API.", "Credentials → Create credentials → API key, restricted to Cloud Text-to-Speech API.", "Add GOOGLE_TTS_API_KEY=… to learner/secrets.env."],
             tr: ["console.cloud.google.com: ücretsiz denemeyi başlat ve bir proje oluştur.", "Cloud Text-to-Speech API'yi etkinleştir.", "Credentials → Create credentials → API key; yalnızca Cloud Text-to-Speech API ile sınırla.", "learner/secrets.env dosyasına GOOGLE_TTS_API_KEY=… satırını ekle."] },
  },
  gemini: {
    pros: { en: "Google's Gemini voices (Kore and Orus), the voice of the films since 2026-11-26. Your own Gemini API key; a few cents for the whole book.",
            tr: "Google'ın Gemini sesleri (Kore ve Orus); 2026-11-26'dan beri filmlerin sesi. Kendi Gemini API anahtarınla; bütün kitap birkaç sent." },
    cons: { en: "Needs an AI Studio project with billing and prepaid credit, and ffmpeg on this computer (it makes the clips mp3). The paid tier allows about 100 clips a day, so the book takes some days.",
            tr: "Faturalandırması ve ön ödemeli kredisi olan bir AI Studio projesi ve bu bilgisayarda ffmpeg gerekir (klipleri mp3 yapar). Ücretli katman günde yaklaşık 100 klip yapar; kitap birkaç gün sürer." },
    setup: { en: ["aistudio.google.com/apikey → Create API key, in a project with billing.", "Add prepaid credit to the project (a few dollars is plenty).", "Add GEMINI_API_KEY=… to learner/secrets.env."],
             tr: ["aistudio.google.com/apikey → Create API key; faturalandırması açık bir projede.", "Projeye ön ödemeli kredi ekle (birkaç dolar fazlasıyla yeter).", "learner/secrets.env dosyasına GEMINI_API_KEY=… satırını ekle."] },
  },
  elevenlabs: {
    pros: { en: "ElevenLabs v4 with native Greek voices from its library (Crhysa, Christos): the most natural voice we have heard, and the podcasts' voice. Your own key and plan.",
            tr: "ElevenLabs v4, kütüphanesinden ana dili Yunanca olan seslerle (Crhysa, Christos): duyduğumuz en doğal ses, podcast'lerin sesi. Kendi anahtarın ve planınla." },
    cons: { en: "A paid plan (from $6 a month; library voices are not available on the free plan). Its clips are for your own use only: ElevenLabs' terms do not let them be shared openly.",
            tr: "Ücretli plan gerekir (ayda 6 dolardan başlar; ücretsiz planda kütüphane sesleri yok). Klipleri yalnızca senin kullanımın içindir: ElevenLabs'in koşulları açıkça paylaşılmasına izin vermez." },
    setup: { en: ["elevenlabs.io: choose a paid plan (Starter or higher).", "Profile → API Keys → Create, with Text to Speech, Voices (read) and User (read).", "Add ELEVENLABS_API_KEY=… to learner/secrets.env."],
             tr: ["elevenlabs.io: ücretli bir plan seç (Starter ya da üstü).", "Profile → API Keys → Create; Text to Speech, Voices (read) ve User (read) açık.", "learner/secrets.env dosyasına ELEVENLABS_API_KEY=… satırını ekle."] },
  },
  openai: {
    pros: { en: "Clear Greek (gpt-4o-mini-tts), and the clips are yours. Pay as you go: about a dollar or two for the whole book.",
            tr: "Anlaşılır Yunanca (gpt-4o-mini-tts), klipler senin. Kullandıkça öde: bütün kitap bir iki dolar." },
    cons: { en: "An English voice speaking Greek: a slight accent, last of the online voices in our test. Needs an API balance (separate from ChatGPT Plus).",
            tr: "Yunanca konuşan İngilizce bir ses: hafif aksan; testimizde çevrimiçi sesler içinde sonuncu. API bakiyesi gerekir (ChatGPT Plus'tan ayrı)." },
    setup: { en: ["platform.openai.com/api-keys → Create new secret key (Restricted, with Audio on).", "Add OPENAI_API_KEY=… to learner/secrets.env."],
             tr: ["platform.openai.com/api-keys → Create new secret key (Restricted, Audio açık).", "learner/secrets.env dosyasına OPENAI_API_KEY=… satırını ekle."] },
  },
};

async function renderVoice() {
  resetScreens();
  let st;
  try { st = await api("/api/voice"); } catch { return showError(); }
  const lang = state.lang;
  const num = (n) => n.toLocaleString(lang === "tr" ? "tr-TR" : "en-GB");
  const order = [...st.order];
  const rows = [...st.providers].sort((a, b) => (a.position ?? 99) - (b.position ?? 99));
  const save = async (next) => {
    try { await api("/api/voice/order", { providers: next }); } catch { /* the list stays as it was */ }
    renderVoice();
  };
  const move = (name, d) => {
    const i = order.indexOf(name), j = i + d;
    if (i < 0 || j < 0 || j >= order.length) return;
    [order[i], order[j]] = [order[j], order[i]];
    save(order);
  };
  const toggle = (name) => save(order.includes(name) ? order.filter(n => n !== name) : [...order, name]);

  const cards = rows.map(p => {
    const info = VOICE_INFO[p.name] || {};
    const on = order.includes(p.name);
    const pill = p.problem ? h("span", { class: "pill warn" }, t("voice_needs"))
      : on ? h("span", { class: "pill ok" }, `#${p.position} · ${t("voice_in_use")}`)
      : h("span", { class: "pill" }, t("voice_ready_off"));
    const sample = (role) => {
      const label = role === "m" ? t("voice_sample_m") : t("voice_sample_f");
      const btn = h("button", { class: "secondary small-btn", type: "button" }, `▶ ${label}`);
      btn.addEventListener("click", async () => {
        stopSpeaking();
        let url = p.sample[role] ? `/voice-sample/${p.name}-${role}.mp3` : null;
        if (!url) {
          btn.disabled = true; btn.textContent = t("voice_making");
          try { url = (await api("/api/voice/sample", { provider: p.name, role })).url; }
          catch { btn.textContent = t("voice_sample_failed"); btn.disabled = false; return; }
          btn.disabled = false; btn.textContent = `▶ ${label}`;
          p.sample[role] = true;
        }
        const a = new Audio(`${url}?v=${Date.now()}`); playing = a; a.play().catch(() => {});
      });
      btn.disabled = !!p.problem && !p.sample[role];
      return btn;
    };
    const quota = p.free ? h("div", { class: "quota" }, ropeBar(Math.min(p.used, p.free), p.free),
      h("span", { class: "small muted" }, t("voice_quota", { used: num(p.used), free: num(p.free) }))) : null;
    return h("article", { class: `voice-card${on ? " on" : ""}` },
      h("div", { class: "voice-head" },
        h("div", { class: "voice-name" }, h("strong", {}, p.label), pill),
        h("div", { class: "voice-tools" },
          on ? h("button", { class: "icon-btn", type: "button", "aria-label": t("voice_up"), title: t("voice_up"), disabled: p.position === 1, onclick: () => move(p.name, -1) }, icon("up")) : null,
          on ? h("button", { class: "icon-btn", type: "button", "aria-label": t("voice_down"), title: t("voice_down"), disabled: p.position === order.length, onclick: () => move(p.name, 1) }, icon("down")) : null,
          h("button", { class: "secondary small-btn", type: "button", onclick: () => toggle(p.name) }, on ? t("voice_remove") : t("voice_add")))),
      p.problem ? h("p", { class: "small warn-text" }, t(/consent|yes/.test(p.problem) ? "voice_problem_yes" : /KEY|REGION/.test(p.problem) ? "voice_problem_key" : "voice_problem_install")) : null,
      h("div", { class: "voice-samples" }, sample("f"), sample("m")),
      quota,
      h("dl", { class: "voice-pc" },
        h("dt", {}, t("voice_for")), h("dd", {}, info.pros?.[lang] || ""),
        h("dt", {}, t("voice_against")), h("dd", {}, info.cons?.[lang] || "")),
      info.setup ? h("details", { class: "voice-setup" }, h("summary", {}, t("voice_how")),
        h("ol", {}, info.setup[lang].map(x => h("li", {}, x)))) : null);
  });
  const total = st.texts || 0, made = total - (st.missing || 0);
  const covered = total ? Math.round(100 * made / total) : 0;
  app.replaceChildren(
    ...appBar(null),
    crumb("home", t("nav_home")),
    h("section", { class: "voice-page" },
      h("h1", {}, t("voice_title")),
      h("p", { class: "lede" }, t("voice_lede")),
      h("div", { class: "voice-cover" }, ropeBar(made, total || 1),
        h("span", { class: "small muted" }, t("voice_covered", { pct: covered, made: num(made), total: num(total) }))),
      ...cards,
      h("article", { class: "voice-card browser" },
        h("div", { class: "voice-head" }, h("div", { class: "voice-name" }, h("strong", {}, t("voice_browser")), h("span", { class: "pill" }, t("voice_always")))),
        h("p", { class: "small muted" }, t("voice_browser_text"))),
      h("p", { class: "small muted voice-foot" }, t("voice_foot"))));
}
