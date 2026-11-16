// Greek Coach front end. Plain ES module, no build step.

const app = document.getElementById("app");
const LANGS = ["en", "tr"];

const state = {
  lang: "en",
  strings: {},
  home: null,
  session: null,   // {session_id, cards, index, total, done}
  card: null,      // per-card UI state
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

const packOf = (itemKey) => itemKey.split("/")[0];
const idOf = (itemKey) => itemKey.split("/").slice(1).join("/");

// ---------- Greek speech (browser voice, local only) ----------

let greekVoice = null;

function pickVoice() {
  if (!("speechSynthesis" in window)) return;
  const voices = speechSynthesis.getVoices();
  greekVoice = voices.find(v => v.lang.toLowerCase().startsWith("el") && v.localService) || null;
  document.querySelectorAll(".speak").forEach(b => { b.hidden = !greekVoice; });
}
if ("speechSynthesis" in window) {
  pickVoice();
  speechSynthesis.addEventListener("voiceschanged", pickVoice);
}

function speak(text, rate = 0.9) {
  if (!greekVoice) return false;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.voice = greekVoice;
  u.lang = greekVoice.lang;
  u.rate = rate;
  speechSynthesis.speak(u);
  if (state.card) state.card.audioPlays += 1;
  return true;
}

const SPEAKER_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 5 6 9H3v6h3l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M18.5 5.5a9 9 0 0 1 0 13"/></svg>';

function speakButton(text, small = false) {
  const b = h("button", {
    class: small ? "speak small" : "speak",
    type: "button",
    title: t("listen"),
    "aria-label": t("listen"),
    onclick: (e) => { e.stopPropagation(); speak(text); },
  });
  b.innerHTML = SPEAKER_SVG;
  b.hidden = !greekVoice;
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
        h("span", { class: "el", lang: "el" }, e.el), speakButton(e.el, true),
        h("span", { class: "pop-meaning" }, e.meaning)))
    : [h("p", { class: "muted" }, t("lookup_none", { word }))];
  if (res.match === "stem") rows.push(h("p", { class: "muted small" }, t("lookup_similar")));
  box.replaceChildren(h("div", { class: "pop-head" }, h("strong", { lang: "el" }, word), speakButton(word, true)), ...rows);
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

function translatable(greekEl, translation) {
  // A Greek line with a "Translate" toggle underneath it.
  if (!translation) return [greekEl];
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
          renderHome();
        },
      }, label)));
}

function wordmark() {
  return h("div", { class: "wordmark" }, h("span", { class: "alpha", lang: "el" }, "α"), t("app_name"));
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

function coachPanel(coach) {
  // What the coach left for the learner: its note, feedback ready, exam dates, and run problems.
  if (!coach) return null;
  const blocks = [];
  for (const p of coach.run_problems || []) {
    blocks.push(h("p", { class: "warn" }, t(p.problem === "failed" ? "run_failed" : "run_missing",
      { skill: p.skill, date: fmtDate(p.since) })));
  }
  if (coach.message) {
    const text = coach.message[state.lang] || coach.message.en || coach.message.tr;
    blocks.push(h("div", { class: "coach-note" },
      h("p", {}, text), h("p", { class: "muted small" }, t("coach_note_from", { date: fmtDate(coach.message.date) }))));
  }
  if (coach.feedback_ready?.length) {
    const first = coach.feedback_ready[0];
    blocks.push(h("button", { class: "secondary feedback-ready", type: "button", onclick: () => renderSubmission(first.id) },
      t(first.kind === "speaking" ? "feedback_ready_speaking" : "feedback_ready_writing")));
  }
  for (const e of coach.dates?.entries || []) {
    const what = (state.lang === "tr" && e.what_tr) || e.what;
    const reg = e.registration;
    const today = state.home.today;
    let line;
    if (reg?.opens && reg.opens > today) line = t("date_reg_opens", { what, date: fmtDate(reg.opens) });
    else if (reg?.closes && reg.closes >= today) line = t("date_reg_closes", { what, date: fmtDate(reg.closes) });
    else line = t("date_next", { what, date: fmtDate(e.date) });
    blocks.push(h("p", { class: "date-line" }, line));
  }
  const links = [h("span", { class: "muted small" }, t("tutor_line"))];
  if (coach.submissions_total) {
    links.push(h("button", { class: "link-button small", type: "button", onclick: renderWriting }, t("your_writing")));
  }
  blocks.push(h("p", { class: "coach-links" }, ...links));
  return h("section", { class: "panel coach" }, ...blocks);
}

async function renderHome() {
  state.session = null;
  state.card = null;
  closePopover();
  try {
    state.home = await api("/api/home");
  } catch { return showError(); }
  const { stats, minutes } = state.home;
  const [hello, helloT] = greeting();
  const status = stats.today.state;
  const startLabel = status === "resume" ? t("continue_daily", { left: stats.today.left })
    : status === "done" ? t("more5") : t("start_daily", { minutes });
  const first = stats.answers_total === 0;

  app.replaceChildren(
    h("header", { class: "topbar" }, wordmark(), langSwitch()),
    h("section", { class: "home" },
      h("h1", { class: "greeting", lang: "el" }, hello),
      h("p", { class: "greeting-tr" }, `${helloT} · ${t("tagline")}`),
      status === "done" ? h("p", { class: "done-today" }, t("done_today")) : null,
      h("button", { class: status === "done" ? "start secondary-start" : "start", type: "button", id: "start",
        onclick: () => startSession(status === "done" ? "extra" : "daily") }, startLabel),
      h("p", { class: "counts muted" }, first ? t("home_first") : todayLine(stats)),
    ),
    coachPanel(state.home.coach),
    ...(first ? [] : [consistencyGrid(stats), standing(stats)]),
  );
  document.getElementById("start").focus();
}

// ---------- session ----------

async function startSession(kind, items = []) {
  app.replaceChildren(h("div", { class: "center-note" }, t("loading")));
  try {
    const s = await api("/api/session", { kind, items, ui_lang: state.lang, has_voice: !!greekVoice });
    if (!s.cards.length) {
      app.replaceChildren(h("header", { class: "topbar" }, wordmark()), h("div", { class: "center-note" }, t("nothing")));
      return;
    }
    state.session = { ...s, index: 0 };
    renderCard();
  } catch { showError(); }
}

function sessionFrame(body) {
  const s = state.session;
  const card = s.cards[s.index];
  const done = (s.done || 0) + s.index;
  const total = s.total || s.cards.length;
  const pct = Math.round((done / total) * 100);
  return [
    h("header", { class: "topbar" },
      h("span", { class: "muted small" }, `${t(`segment_${card.segment || "review"}`)} · ${t("progress", { done: done + 1, total })}`),
      h("button", { class: "link-button", type: "button", onclick: finishSession }, t("enough")),
    ),
    h("div", { class: "progress", role: "progressbar", "aria-valuemin": 0, "aria-valuemax": 100, "aria-valuenow": pct },
      h("span", { style: `width:${pct}%` })),
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
    onclick: () => { menu.hidden = !menu.hidden; } }, "⚑");
  return h("div", { class: "flag-wrap" }, btn, menu);
}

const RENDERERS = {};

function renderCard() {
  closePopover();
  const s = state.session;
  const card = s.cards[s.index];
  state.card = { data: card, answered: false, started: performance.now(), audioPlays: 0, lookups: 0, tf: [], picks: {} };
  const body = (RENDERERS[card.type] || RENDERERS.mcq)(card);
  body.prepend(flagButton());
  app.replaceChildren(...sessionFrame(body));
  if (s.index === 0 && (state.home?.stats?.answers_total ?? 0) < 10) {
    app.append(h("p", { class: "hint muted small" }, t("keys_hint")));
  }
  const first = app.querySelector("input.typed, .option, .tf button, .pick");
  if (first) first.focus();
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

function rubricLine(rubric) {
  if (!rubric?.el) return null;
  return h("div", { class: "rubric" }, ...translatable(greekText(rubric.el, { cls: "el" }), tr(rubric)));
}

function checkRow(onCheck) {
  const btn = h("button", { class: "primary", type: "button", disabled: true, onclick: onCheck }, t("check"));
  return [h("div", { class: "actions check-row" }, btn), btn];
}

// Listening: file audio first, then audio the coach pre-generated, then the browser voice.
function listenBlock(card) {
  const st = card.stimulus;
  if (!st || !(st.audio || st.tts)) return null;
  const limit = st.plays || 2;
  let used = 0;
  let audio = null;
  const status = h("span", { class: "muted small" }, t("plays_left", { n: limit }));
  const play = h("button", { class: "primary listen", type: "button" }, `▶ ${t("play")}`);
  const sources = [];
  if (st.audio) sources.push(`/packs/${encodeURIComponent(packOf(card.item_key))}/${st.audio.split("/").map(encodeURIComponent).join("/")}`);
  sources.push(`/audio-cache/${encodeURIComponent(packOf(card.item_key))}/${encodeURIComponent(idOf(card.item_key))}`);
  async function getAudio() {
    for (const src of sources) {
      try {
        const r = await fetch(src, { method: "HEAD" });
        if (r.ok) return new Audio(src);
      } catch { /* try the next */ }
    }
    return null;
  }
  play.addEventListener("click", async () => {
    if (used >= limit && !state.card.answered) return;
    if (audio === null) audio = (await getAudio()) || false;
    if (audio) { audio.currentTime = 0; audio.play(); state.card.audioPlays += 1; }
    else if (!speak(st.tts, 0.85)) { status.textContent = t("no_voice"); return; }
    used += 1;
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

function stimulusBlock(card) {
  if (card.stimulus?.text) return h("div", { class: "notice" }, greekText(card.stimulus.text, { tag: "p" }));
  return listenBlock(card);
}

RENDERERS.vocab = (card) => {
  const dir = card.direction;
  const ask = { el_meaning: t("q_meaning"), meaning_el: t("q_greek"), audio_meaning: t("q_heard"), meaning_el_typed: t("q_type") }[dir];
  let promptEl;
  if (dir === "el_meaning") promptEl = h("div", { class: "prompt-row" }, greekText(card.prompt, { tag: "p", cls: "big-greek", tappable: false }), speakButton(card.speak));
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
  const opts = optionList(card.options, dir === "meaning_el", (i) => submit({ choice: card.options[i] }, { pickedIndex: i }));
  return h("article", { class: "card" }, question, opts, h("div", { class: "slot" }));
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
  const blocks = [rubricLine(card.rubric), cueLine, ...translatable(sentence, tr(card.translation))];
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
  return h("article", { class: "card" }, rubricLine(card.rubric), stimulusBlock(card), question, opts, h("div", { class: "slot" }));
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
  return h("article", { class: "card" }, rubricLine(card.rubric), stimulusBlock(card),
    h("div", { class: "statements" }, statements), row, h("div", { class: "slot" }));
};

RENDERERS.match = (card) => {
  // Tap a left item, then the right item that goes with it. Tap a paired left item to undo.
  const picks = state.card.picks;
  let active = 0;
  const [row, checkBtn] = checkRow(() => submit({ answers: card.left.map((_, i) => picks[i]) }));
  const leftEls = card.left.map((text, i) => h("button", { class: "pick left el", type: "button", lang: "el", "data-i": i,
    onclick: () => { if (state.card.answered) return; if (picks[i] !== undefined) delete picks[i]; active = i; paint(); } },
    h("span", { class: "badge" }, String.fromCharCode(65 + i)), h("span", {}, text)));
  const rightEls = card.right.map((text, j) => h("button", { class: "pick right el", type: "button", lang: "el", "data-j": j,
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
  return h("article", { class: "card" }, rubricLine(card.rubric),
    card.prompt?.el ? greekText(card.prompt.el, { tag: "p", cls: "prompt-greek" }) : null,
    h("div", { class: "match" }, h("div", { class: "col" }, leftEls), h("div", { class: "col" }, rightEls)),
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
  return h("article", { class: "card" }, rubricLine(card.rubric), listenBlock(card),
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
  return h("article", { class: "card" }, rubricLine(card.rubric), stimulusBlock(card),
    card.prompt?.el ? greekText(card.prompt.el, { tag: "p", cls: "prompt-greek" }) : null,
    h("div", { class: "cat-list" }, rows), row, h("div", { class: "slot" }));
};

function countWords(text) {
  return text.split(/\s+/).filter(w => /[\p{L}\p{N}]/u.test(w)).length;
}

function openTaskPrompt(card) {
  const prompt = greekText(card.prompt.el, { tag: "p", cls: "prompt-greek" });
  return h("div", { class: "question" }, ...translatable(prompt, tr(card.prompt)));
}

function skipButton() {
  return h("button", { class: "link-button", type: "button", onclick: () => submit({ skipped: true }, { skipped: true }) },
    t("skip_today"));
}

RENDERERS.write = (card) => {
  const [lo, hi] = card.words;
  const { input, board } = greekInput(() => {}, t("write_label"), { multiline: true });
  const counter = h("p", { class: "muted small word-count" }, t("word_count", { n: 0, lo, hi }));
  const save = h("button", { class: "primary", type: "button", disabled: true,
    onclick: () => submit({ text: input.value }, { typed: input }) }, t("write_save"));
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
  return h("article", { class: "card write" }, rubricLine(card.rubric), openTaskPrompt(card), checklist,
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
  return h("article", { class: "card speak-card" }, rubricLine(card.rubric), openTaskPrompt(card), useful, note,
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
  if (!c || c.answered) return;
  c.answered = true;
  closePopover();
  app.querySelectorAll(".option, .tf button, .check-row button, .typed, .keyboard .k, .speak-card .actions button")
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
  const slot = app.querySelector(".slot");
  const parts = [];
  if (state.card.revealTranscript) state.card.revealTranscript();

  if (card.type === "write" || card.type === "speak") {
    app.querySelector(".check-row")?.remove();
    const last = state.session.index >= state.session.cards.length - 1;
    const next = h("button", { class: "primary", type: "button", id: "next", onclick: nextCard }, last ? t("finish") : t("next"));
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
    const buttons = [...app.querySelectorAll(".option")];
    const rightIndex = card.type === "mcq" ? result.answer : card.options.indexOf(result.answer);
    buttons.forEach((b, i) => {
      if (i === rightIndex) b.classList.add("right");
      else if (i === ui.pickedIndex) b.classList.add("wrong");
    });
    if (!result.correct) {
      const answerText = card.type === "mcq" ? card.options[result.answer] : result.answer;
      parts.push(h("p", {}, t("answer_is", { answer: answerText })));
    }
    if (card.type === "vocab" && card.direction !== "el_meaning") {
      parts.push(h("div", { class: "example" }, speakButton(card.speak, true), greekText(card.speak, { cls: "el" })));
    }
  } else if (card.type === "form") {
    for (const [g, input] of Object.entries(ui.formInputs || {})) {
      const el = input.el || input;
      el.classList.add(result.parts.length && result.correct ? "right" : "wrong");
    }
    app.querySelectorAll(".option").forEach((b, i) => {
      const text = b.lastChild.textContent;
      if (Object.values(result.answer).includes(text)) b.classList.add("right");
      else if (i === ui.pickedIndex) b.classList.add("wrong");
    });
    const right = Object.values(result.answer).join(", ");
    parts.push(h("div", { class: "example" }, speakButton(card.text.replace(/\{(\w+)\}/g, (_, g) => result.answer[g]), true),
      greekText(card.text.replace(/\{(\w+)\}/g, (_, g) => result.answer[g]), { tag: "p", cls: "el" })));
    if (!result.correct) parts.push(h("p", {}, t("answer_is", { answer: right })));
  } else if (card.type === "true_false") {
    app.querySelectorAll(".statement").forEach((row, i) => {
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
    parts.push(h("p", {}, t("parts_score", { right: result.parts.filter(Boolean).length, total: result.parts.length })));
  }
  app.querySelector(".check-row")?.remove();

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
  const next = h("button", { class: "primary", type: "button", id: "next", onclick: nextCard }, last ? t("finish") : t("next"));
  slot.replaceChildren(
    h("div", { class: `feedback ${result.correct ? "good" : "bad"}`, role: "status" },
      h("p", { class: "verdict" }, result.correct ? (result.accent_note ? t("right_accent") : t("right")) : t("wrong")), ...parts),
    h("div", { class: "actions" }, next));
  next.focus();
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
  if (!s) return renderHome();
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
  if (sum.written) lines.push(h("p", { class: "line" }, t("summary_written")));
  if (!sum.done && !sum.written) {
    lines.push(h("p", { class: "line" }, t("summary_none")));
  } else if (!sum.done) {
    /* only writing or speaking this time */
  } else {
    lines.push(h("p", { class: "line" }, t("summary_line", { done: sum.done, minutes: sum.minutes, pct: Math.round(sum.accuracy * 100) })));
    for (const [area, v] of Object.entries(sum.by_area)) {
      lines.push(h("p", { class: "muted" }, t("summary_area", { area: areaName(area), right: v.right, done: v.done })));
    }
    if (sum.right === sum.done) lines.push(h("p", {}, t("summary_perfect")));
  }
  if (sum.left) lines.push(h("p", { class: "muted" }, t("summary_left", { n: sum.left })));
  lines.push(h("p", {}, t("summary_tomorrow", { n: sum.due_tomorrow })));
  const missed = sum.missed?.length
    ? [h("h2", {}, t("summary_missed")),
       h("ul", {}, sum.missed.map(w => h("li", {}, greekText(w.el, { cls: "el" }), speakButton(w.el, true), h("span", { class: "muted" }, w.meaning))))]
    : [];
  const done = h("button", { class: "primary", type: "button", onclick: renderHome }, t("done"));
  app.replaceChildren(
    h("header", { class: "topbar" }, wordmark()),
    h("section", { class: "summary" },
      h("h1", {}, t("summary_title")),
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
    h("button", { class: "sub-row", type: "button", onclick: () => renderSubmission(s.id) },
      h("span", { class: "muted small" }, `${fmtDate(s.ts)} · ${t(s.kind === "speaking" ? "kind_speaking" : "kind_writing")}`),
      h("span", { class: "el", lang: "el" }, (s.prompt?.el || "").slice(0, 90) + ((s.prompt?.el || "").length > 90 ? "…" : "")),
      h("span", { class: `badge ${s.status}` }, s.status === "marked" ? t("status_marked") : t("status_waiting")))));
  app.replaceChildren(topbarBack(renderHome),
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
  app.replaceChildren(topbarBack(renderWriting), h("section", { class: "summary writing" }, ...blocks));
}

// ---------- keyboard shortcuts ----------

document.addEventListener("keydown", (e) => {
  if (!state.card || e.altKey || e.ctrlKey || e.metaKey) return;
  if (e.target.matches?.("input, textarea")) return;
  if (!state.card.answered && /^[1-9]$/.test(e.key)) {
    const b = app.querySelector(`.option[data-index="${Number(e.key) - 1}"]`);
    if (b && !b.disabled) { e.preventDefault(); b.click(); }
  } else if (state.card.answered && e.key === "Enter") {
    const next = document.getElementById("next");
    if (next && document.activeElement !== next) { e.preventDefault(); next.click(); }
  }
});

// ---------- boot ----------

(async function boot() {
  let lang = navigator.language?.toLowerCase().startsWith("tr") ? "tr" : "en";
  try {
    const home = await api("/api/home");
    if (LANGS.includes(home.ui_lang)) lang = home.ui_lang;
  } catch { /* renderHome reports it */ }
  await loadStrings(lang);
  // ?practice=pack/item,pack/item opens a practice session of those items (used by the coach).
  const params = new URLSearchParams(location.search);
  const practice = params.get("practice");
  if (practice) return startSession("practice", practice.split(",").filter(Boolean));
  // ?submission=12 opens a piece of writing with its feedback (the coach links to it).
  if (/^\d+$/.test(params.get("submission") || "")) return renderSubmission(Number(params.get("submission")));
  renderHome();
})();
