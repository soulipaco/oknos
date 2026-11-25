"""Spoken Greek made ahead of time (phase 10, docs/VOICE.md).

The app knows what it will say (words, example sentences, dialogue lines, listening passages, the
words a learner can tap), so the speech is made once, by the first provider in the learner's list
that works, and kept as files in learner/voice/. The app plays a file when there is one and falls
back to the browser's own voice when there is not.

Providers (each makes mp3 bytes from a text and a role, female or male):
  azure   Microsoft's neural voices (Athina, Nestoras) through Azure Speech, with the learner's key.
  edge    the same voices through edge-tts: free, unofficial, this computer only, and only with the
          learner's yes (profile `edge_tts_ok`, SPEC §9).
  google  Google Cloud Text-to-Speech (Chirp 3 HD), with the learner's key.
  openai  OpenAI gpt-4o-mini-tts, with the learner's key.

For the podcast lessons only (podcast_providers(), docs/PODCASTS.md):
  gemini  Google Gemini TTS, with the learner's own Gemini API key: two speakers acted together in
          one request, a described style per speaker, Greek inside a Turkish sentence.

Keys come from learner/secrets.env or the environment and are only ever sent to their own
provider. Only content text is sent, never learner data.

Shipped clips: the open content's texts come with clips made by Google (Chirp 3 HD Kore and Orus)
in content/open-voice/ (scripts/ship_voice.py). A clip is looked for in learner/voice/ first, then
there, then the browser's voice reads the text.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import http.client
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable, Iterable
from xml.sax.saxutils import escape

from oknos import greek, paths

ROLES = ("f", "m")  # female, male; the narrator is female
# Greek is what the app speaks; Turkish and English are the explanation languages of the podcast
# lessons (docs/PODCASTS.md). Each provider has a voice pair per language.
LANGS = ("el", "tr", "en")
LOCALES = {"el": "el-GR", "tr": "tr-TR", "en": "en-US"}
SECRET_NAMES = ("GOOGLE_TTS_API_KEY", "AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION", "OPENAI_API_KEY", "GEMINI_API_KEY")
USER_AGENT = "Oknos (local Greek learning app)"

# The test sentences of the "Choose your voice" screen (from the open book).
SAMPLES = ("Καλημέρα! Ναι, πίνω καφέ κάθε πρωί. Εσύ;",
           "Συγγνώμη, κυρία. Ποιο λεωφορείο πάει στο κέντρο, στον Λευκό Πύργο;")


# ---------- texts, keys and files ----------

def norm(text: str) -> str:
    """The form a text is cached under: NFC, single spaces, trimmed, case-folded (case does not change the sound)."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip().casefold()


def key(text: str, role: str, lang: str = "el") -> str:
    """The cache key. Greek keys carry no language (they predate the others and stay valid)."""
    prefix = role if lang == "el" else f"{lang}|{role}"
    return hashlib.sha1(f"{prefix}|{norm(text)}".encode("utf-8")).hexdigest()


def voice_dir() -> Path:
    return paths.learner_dir() / "voice"


def file_for(text: str, role: str = "f", base: Path | None = None, lang: str = "el") -> Path:
    """Greek clips: <base>/<role>/...; Turkish and English: <base>/<lang>/<role>/..."""
    role = role if role in ROLES else "f"
    k = key(text, role, lang)
    root = (base or voice_dir()) if lang == "el" else (base or voice_dir()) / lang
    return root / role / k[:2] / f"{k}.mp3"


# ---------- clips shipped with the open content (content/open-voice/, scripts/ship_voice.py) ----------

SHIPPED_FAMILY = "google"  # the shipped clips are Google's Kore and Orus


def shipped_dir() -> Path:
    return paths.CONTENT_DIR / "open-voice"


def shipped() -> dict:
    """The shipped clips' manifest: key -> {"r": role, "t": text}."""
    try:
        return json.loads((shipped_dir() / "index.json").read_text(encoding="utf-8")).get("clips", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def shipped_gaps(open_catalog) -> tuple[list[str], list[str]]:
    """Open texts with no shipped clip, and shipped clips no open text uses any more.

    Either is only a warning (`oknos validate content/open`, `scripts/ship_voice.py --check`): a text
    without a clip is read by the browser's voice until the script is run again with a Google key."""
    try:
        data = json.loads((shipped_dir() / "index.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    clips, browser = data.get("clips", {}), data.get("browser", {})
    wanted = {key(t, r): t for t, r in texts(open_catalog)}
    missing = sorted(t for k, t in wanted.items() if k not in clips and k not in browser)
    stale = sorted(c["t"] for k, c in clips.items() if k not in wanted)
    return missing, stale


def find(text: str, role: str = "f", lang: str = "el") -> Path | None:
    """The clip to play: the learner's own first, then the shipped one (Greek only); None means the browser's voice."""
    for base in (voice_dir(), shipped_dir()) if lang == "el" else (voice_dir(),):
        target = file_for(text, role, base, lang)
        if target.is_file():
            return target
    return None


def secrets() -> dict[str, str]:
    """Keys from learner/secrets.env, overridden by the environment. Never print the values."""
    found: dict[str, str] = {}
    f = paths.learner_dir() / "secrets.env"
    if f.is_file():
        for line in f.read_text(encoding="utf-8-sig").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                name, value = line.split("=", 1)
                if value.strip():
                    found[name.strip()] = value.strip()
    for name in SECRET_NAMES:
        if os.environ.get(name):
            found[name] = os.environ[name]
    return found


def read_profile() -> dict:
    try:
        return json.loads(paths.profile_path().read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


# ---------- who speaks ----------

_SPEAKERS: dict[str, str] | None = None


def role_of(speaker: str | None) -> str:
    """The voice for a dialogue speaker: the cast list first, then the Greek name's ending; unknown → female."""
    global _SPEAKERS
    if not speaker:
        return "f"
    if _SPEAKERS is None:
        data = json.loads((Path(__file__).with_name("speakers.json")).read_text(encoding="utf-8"))
        _SPEAKERS = {greek.fold(k): v for k, v in data["speakers"].items()}
    s = greek.fold(speaker)
    if s in _SPEAKERS:
        return _SPEAKERS[s]
    words = s.split() or [s]
    if words[0] in ("κυριοσ", "ο"):  # fold() turns the final ς into σ
        return "m"
    if words[0] in ("κυρια", "η"):
        return "f"
    if words[-1].endswith(("οσ", "ησ", "ασ", "ων")):
        return "m"
    return "f"


# ---------- providers ----------

class Refused(Exception):
    """The provider could not make this text now (an error, throttling, no key); try the next one."""


@dataclass
class Provider:
    name: str
    voices: dict[str, str]
    free_chars: int | None          # a month's free characters (None: no free quota or no limit)
    min_interval: float = 0.0       # seconds between requests (Azure's free tier allows 20 a minute)
    label: str = ""
    family: str = ""                # providers of one family share voices (Azure and edge: Athina, Nestoras)
    lang_voices: dict[str, dict[str, str]] = field(default_factory=dict)  # "tr"/"en" -> role -> voice
    _last: float = field(default=float("-inf"), repr=False)  # never used yet: not busy, whatever the clock says

    # What a podcast can ask of it (docs/PODCASTS.md, "The voices"):
    named = False         # speaks with a voice chosen by name from the casting pool (src/oknos/casting.json)
    dialogue = False      # acts two speakers together in one request (make_exchange)
    mixed = False         # says Greek words inside a Turkish or English sentence correctly
    podcast_only = False  # never makes the app's clips (its audio is not mp3; the podcast joins it)

    def ready(self, keys: dict, profile: dict) -> str | None:
        """None if it can be used, else why not (shown to the learner)."""
        raise NotImplementedError

    def make(self, text: str, role: str, keys: dict) -> bytes:
        raise NotImplementedError

    def speaks(self, lang: str) -> bool:
        return lang == "el" or lang in self.lang_voices

    def voice(self, role: str, lang: str = "el") -> str:
        return self.voices[role] if lang == "el" else self.lang_voices[lang][role]

    def busy(self) -> bool:
        return time.monotonic() - self._last < self.min_interval


def _post(url: str, body: bytes, headers: dict, timeout: float = 60, tries: int = 2) -> bytes:
    """POST and read the answer. A connection cut halfway through the answer (IncompleteRead and the
    like: it happened once in an hour of podcast clips) is tried again once before it counts as a
    refusal, so one bad moment does not hand the clip to another voice or stop a long render."""
    req = urllib.request.Request(url, data=body, headers={"User-Agent": USER_AGENT, **headers})
    for attempt in range(tries):
        try:
            return urllib.request.urlopen(req, timeout=timeout).read()
        except urllib.error.HTTPError as e:
            raise Refused(f"{e.code} {e.reason}") from None
        except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as e:
            if attempt + 1 < tries and not isinstance(e, urllib.error.URLError):
                time.sleep(2)
                continue
            raise Refused(f"no connection ({e.__class__.__name__})") from None
    raise Refused("no connection")


class Azure(Provider):
    def ready(self, keys, profile):
        return None if keys.get("AZURE_SPEECH_KEY") and keys.get("AZURE_SPEECH_REGION") else "needs AZURE_SPEECH_KEY and AZURE_SPEECH_REGION"

    def make(self, text, role, keys, lang="el"):
        ssml = (f"<speak version='1.0' xml:lang='{LOCALES[lang]}'><voice name='{self.voice(role, lang)}'>"
                f"{escape(text)}</voice></speak>")
        return _post(f"https://{keys['AZURE_SPEECH_REGION']}.tts.speech.microsoft.com/cognitiveservices/v1", ssml.encode("utf-8"),
                     {"Ocp-Apim-Subscription-Key": keys["AZURE_SPEECH_KEY"], "Content-Type": "application/ssml+xml",
                      "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3"})


def soften(text: str) -> str:
    """edge-tts refuses some words that carry both a diaeresis and an accent (Ζεϊνέπ); drop the accent in those words."""
    def fix(m):
        w = m.group(0)
        if any(c in w for c in "ϊϋΪΫ") and any(c in w for c in "άέήίόύώ"):
            return unicodedata.normalize("NFC", "".join(c for c in unicodedata.normalize("NFD", w) if c != "́"))
        return w
    return re.sub(r"\w+", fix, text)


class Edge(Provider):
    # edge-tts's own receive timeout did not stop a TLS read that hung for hours (2026-11-22);
    # a whole clip gets at most this long, then it fails and the next provider is tried.
    timeout: float = 45.0

    def ready(self, keys, profile):
        if not profile.get("edge_tts_ok"):
            return "needs the learner's yes (edge_tts_ok in profile.json)"
        try:
            import edge_tts  # noqa: F401
        except ImportError:
            return "needs edge-tts (uv sync)"
        return None

    def make(self, text, role, keys):
        import edge_tts

        async def once(t):
            chunks = []
            async for part in edge_tts.Communicate(t, self.voices[role]).stream():  # a rate setting makes it refuse some words
                if part["type"] == "audio":
                    chunks.append(part["data"])
            return b"".join(chunks)

        for attempt, t in enumerate((text, soften(text))):
            try:
                data = asyncio.run(asyncio.wait_for(once(t), self.timeout))
                if len(data) > 1000:
                    return data
            except Exception:  # edge-tts raises its own NoAudioReceived and network errors
                pass
            time.sleep(2 * (attempt + 1))
        raise Refused("edge sent no audio")


class Google(Provider):
    named = True  # Chirp 3 HD has the 30 voices of the casting pool, by name, in every language

    def ready(self, keys, profile):
        return None if keys.get("GOOGLE_TTS_API_KEY") else "needs GOOGLE_TTS_API_KEY"

    def make(self, text, role, keys, lang="el", voice_name=None, style=None):
        name = f"{LOCALES[lang]}-Chirp3-HD-{voice_name}" if voice_name else self.voice(role, lang)
        body = json.dumps({"input": {"text": text}, "voice": {"languageCode": LOCALES[lang], "name": name},
                           "audioConfig": {"audioEncoding": "MP3"}}).encode("utf-8")
        r = json.loads(_post("https://texttospeech.googleapis.com/v1/text:synthesize", body,
                             {"Content-Type": "application/json", "X-Goog-Api-Key": keys["GOOGLE_TTS_API_KEY"]}))
        return base64.b64decode(r["audioContent"])


class OpenAI(Provider):
    INSTRUCTIONS = ("Speak natural, standard Modern Greek like a native speaker from Athens: clear, calm and friendly, "
                    "at a moderate pace for a language learner.")
    TEACHER = {"tr": "Speak natural, standard Turkish like a warm, clear language teacher from Istanbul, at a calm pace.",
               "en": "Speak clear, natural English like a warm language teacher, at a calm pace."}

    def ready(self, keys, profile):
        return None if keys.get("OPENAI_API_KEY") else "needs OPENAI_API_KEY"

    def make(self, text, role, keys, lang="el"):
        body = json.dumps({"model": "gpt-4o-mini-tts", "voice": self.voice(role, lang), "input": text,
                           "instructions": self.INSTRUCTIONS if lang == "el" else self.TEACHER[lang],
                           "response_format": "mp3"}).encode("utf-8")
        return _post("https://api.openai.com/v1/audio/speech", body,
                     {"Content-Type": "application/json", "Authorization": f"Bearer {keys['OPENAI_API_KEY']}"})


class Gemini(Provider):
    """Gemini TTS through the Gemini API (the learner's own key, paid tier: the text is not used for
    training). Podcasts only. It answers with raw 16-bit PCM, which is returned as a WAV file."""

    MODEL = "gemini-3.8-flash-tts"
    named = dialogue = mixed = podcast_only = True
    tokens = 0  # audio tokens of the last request (about 25 a second of speech): what is billed

    def ready(self, keys, profile):
        return None if keys.get("GEMINI_API_KEY") else "needs GEMINI_API_KEY"

    def _speak(self, parts: list[dict], speech: dict, keys: dict) -> bytes:
        body = json.dumps({"contents": [{"role": "user", "parts": parts}],
                           "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": speech}}).encode("utf-8")
        r = json.loads(_post(f"https://generativelanguage.googleapis.com/v1beta/models/{self.MODEL}:generateContent", body,
                             {"Content-Type": "application/json", "X-Goog-Api-Key": keys["GEMINI_API_KEY"]}, timeout=300))
        try:
            data = r["candidates"][0]["content"]["parts"][0]["inlineData"]
        except (KeyError, IndexError):
            raise Refused(f"no audio in the answer ({r.get('candidates', [{}])[0].get('finishReason', '?')})") from None
        self.tokens = (r.get("usageMetadata") or {}).get("candidatesTokenCount", 0)
        audio = base64.b64decode(data["data"])
        if audio[:4] == b"RIFF":
            return audio
        rate = 24000
        if "rate=" in data.get("mimeType", ""):
            rate = int(data["mimeType"].split("rate=")[1].split(";")[0])
        return pcm_to_wav(audio, rate)

    def make(self, text, role, keys, lang="el", voice_name=None, style=None):
        # The style goes in the metadata: put in the text, a single speaker reads it aloud.
        part = {"text": text}
        if style:
            part["speechMetadata"] = {"style": style}
        name = voice_name or self.voice(role, lang)
        return self._speak([part], {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": name}}}, keys)

    def make_exchange(self, turns: list[tuple[str, str, str, str | None]], keys: dict) -> bytes:
        """Two speakers acted together: turns are (speaker, voice name, text, style)."""
        voices: dict[str, str] = {}
        for who, name, _, _ in turns:
            voices.setdefault(who, name)
        if len(voices) > 2:
            raise ValueError("Gemini acts at most two speakers in one request")
        parts = [{"text": text, "speechMetadata": {"speaker": who, **({"style": style} if style else {})}}
                 for who, _, text, style in turns]
        speech = {"multiSpeakerVoiceConfig": {"speakerVoiceConfigs": [
            {"speaker": who, "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": name}}} for who, name in voices.items()]}}
        return self._speak(parts, speech, keys)


def pcm_to_wav(pcm: bytes, rate: int = 24000) -> bytes:
    import io
    import wave

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


def providers() -> dict[str, Provider]:
    return {
        "azure": Azure("azure", {"f": "el-GR-AthinaNeural", "m": "el-GR-NestorasNeural"}, 500_000, min_interval=3.1,
                       label="Microsoft Athina / Nestoras (Azure)", family="microsoft",
                       lang_voices={"tr": {"f": "tr-TR-EmelNeural", "m": "tr-TR-AhmetNeural"},
                                    "en": {"f": "en-US-AvaNeural", "m": "en-US-AndrewNeural"}}),
        "edge": Edge("edge", {"f": "el-GR-AthinaNeural", "m": "el-GR-NestorasNeural"}, None, min_interval=0.8,
                     label="Microsoft Athina / Nestoras (edge-tts, this computer only)", family="microsoft"),
        "google": Google("google", {"f": "el-GR-Chirp3-HD-Kore", "m": "el-GR-Chirp3-HD-Orus"}, 1_000_000,
                         label="Google Chirp 3 HD Kore / Orus", family="google",
                         lang_voices={"tr": {"f": "tr-TR-Chirp3-HD-Kore", "m": "tr-TR-Chirp3-HD-Orus"},
                                      "en": {"f": "en-US-Chirp3-HD-Kore", "m": "en-US-Chirp3-HD-Orus"}}),
        "openai": OpenAI("openai", {"f": "coral", "m": "ash"}, None, label="OpenAI gpt-4o-mini-tts", family="openai",
                         lang_voices={"tr": {"f": "coral", "m": "ash"}, "en": {"f": "coral", "m": "ash"}}),
    }


def podcast_providers() -> dict[str, Provider]:
    """The app's providers plus those that make podcasts only (Gemini)."""
    return {**providers(),
            "gemini": Gemini("gemini", {"f": "Kore", "m": "Orus"}, None, label="Google Gemini TTS (podcasts only)",
                             family="google", lang_voices={"tr": {"f": "Kore", "m": "Orus"}, "en": {"f": "Kore", "m": "Orus"}})}


DEFAULT_ORDER = ["google"]  # a new learner: Google with their own key; else the browser voice


def order(profile: dict) -> list[str]:
    chosen = (profile.get("voice") or {}).get("providers") or DEFAULT_ORDER
    known = providers()
    return [p for p in chosen if p in known]


# ---------- the month's characters per provider ----------

def _usage_file() -> Path:
    return voice_dir() / "usage.json"


def usage() -> dict:
    try:
        data = json.loads(_usage_file().read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    month = date.today().strftime("%Y-%m")
    return data.get(month, {})


def _add_usage(provider: str, chars: int) -> None:
    f = _usage_file()
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    month = date.today().strftime("%Y-%m")
    data.setdefault(month, {})[provider] = data.get(month, {}).get(provider, 0) + chars
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")


QUOTA_SHARE = 0.9  # stop using a free quota at 90%, so a month never runs over


# ---------- the index of made files (which provider made what) ----------

def _index_file() -> Path:
    return voice_dir() / "index.json"


def read_index() -> dict:
    try:
        return json.loads(_index_file().read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write_index(index: dict) -> None:
    _index_file().parent.mkdir(parents=True, exist_ok=True)
    tmp = _index_file().with_suffix(".tmp")
    tmp.write_text(json.dumps(index, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    tmp.replace(_index_file())


# ---------- making one clip ----------

def make(text: str, role: str = "f", *, chain: list[Provider] | None = None, keys: dict | None = None,
         profile: dict | None = None, wait: bool = False, index: dict | None = None, own: bool = False,
         lang: str = "el") -> str | None:
    """Make the clip for a text with the first provider that works; return the provider's name, or None.

    own: the text comes from the learner's folder (the coach's packs). SPEC §9 keeps those away from
    the free edge route; a provider on the learner's own account (a key) may make them.
    lang: "el", or "tr"/"en" for a podcast's explanations, which are always the agent's own texts."""
    own = own or lang != "el"
    profile = read_profile() if profile is None else profile
    keys = secrets() if keys is None else keys
    if chain is None:
        known = providers()
        chain = [known[p] for p in order(profile)]
    used = usage()
    target = file_for(text, role, lang=lang)
    for p in chain:
        if p.ready(keys, profile) or (own and p.name == "edge") or not p.speaks(lang):
            continue
        if p.free_chars is not None and used.get(p.name, 0) + len(text) > QUOTA_SHARE * p.free_chars:
            continue
        if p.busy():
            # A short pause is waited out (edge's pacing); a long one (Azure's free tier, 20 a minute)
            # passes the clip to the next provider unless asked to wait.
            left = p.min_interval - (time.monotonic() - p._last)
            if left > 1.0 and not wait:
                continue
            time.sleep(max(0.0, left))
        p._last = time.monotonic()
        try:
            data = p.make(text, role, keys) if lang == "el" else p.make(text, role, keys, lang=lang)
        except Refused:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        _add_usage(p.name, len(text))
        if index is not None:
            entry = {"p": p.name, "v": p.voice(role, lang), "t": text[:80]}
            index[key(text, role, lang)] = entry if lang == "el" else {**entry, "l": lang}
        return p.name
    return None


# ---------- what the app says ----------

_texts_cache: tuple[int, list[tuple[str, str]]] | None = None
_own: set[str] = set()  # keys of texts found only in the learner's folder (the coach's packs)


def is_own(text: str, role: str) -> bool:
    return key(text, role) in _own


def texts(catalog) -> list[tuple[str, str]]:
    """Every (text, role) the app can speak, the most used first (cached per loaded catalog)."""
    global _texts_cache
    if _texts_cache is None or _texts_cache[0] != id(catalog):
        _texts_cache = (id(catalog), _collect(catalog))
    return _texts_cache[1]


def _collect(catalog) -> list[tuple[str, str]]:
    """Words, then sentences, then tappable words."""
    from oknos import wordscan
    from oknos.packs import SpeakItem, VocabItem

    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str]] = []
    learner = paths.learner_dir()
    own: set[str] = set()
    shared: set[str] = set()
    current = {"own": False}

    def add(text, role="f"):
        if text and greek.has_greek(text):
            k = (norm(text), role)
            (own if current["own"] else shared).add(key(text, role))
            if k not in seen:
                seen.add(k)
                out.append((text.strip(), role))

    def from_learner(pack) -> bool:
        try:
            return learner in Path(pack.path).resolve().parents
        except (OSError, TypeError):
            return False

    entries = list(catalog.items.values())
    items = [it for _, it in entries]
    for pack, it in entries:
        current["own"] = from_learner(pack)
        if isinstance(it, VocabItem):
            add(it.say or it.el)
    for pack, it in entries:
        current["own"] = from_learner(pack)
        if isinstance(it, VocabItem) and it.example:
            add(it.example.el)
        if isinstance(it, SpeakItem) and it.model and it.model.el:
            add(it.model.el)
        if it.stimulus and it.stimulus.tts:
            add(it.stimulus.tts)
    for pack, chapter in catalog.chapters.values():
        current["own"] = from_learner(pack)
        for line in chapter.greek_lines():
            add(line["el"], role_of(line.get("who")))
    for pack, it in entries:
        current["own"] = from_learner(pack)
        for w in wordscan.tappable(wordscan.item_texts(it)):
            add(w)
    for pack, chapter in catalog.chapters.values():
        current["own"] = from_learner(pack)
        for w in wordscan.tappable(wordscan.chapter_texts(chapter)):
            add(w)
    _own.clear()
    _own.update(own - shared)  # a text that is also in a content pack is content
    return out


def missing(pairs: Iterable[tuple[str, str]], skip_shipped: bool = False) -> list[tuple[str, str]]:
    ship = shipped() if skip_shipped else {}
    return [(t, r) for t, r in pairs if not file_for(t, r).is_file() and key(t, r) not in ship]


def build(catalog, *, limit: int | None = None, wait: bool = False, redo: str | None = None,
          progress: Callable[[int, int, str | None], None] | None = None, rounds: int = 3, pause: float = 30.0) -> dict:
    """Make every missing clip (or, with redo=<provider>, remake the ones that provider made). Returns counts."""
    profile, keys = read_profile(), secrets()
    known = providers()
    chain = [known[p] for p in order(profile)]
    index = read_index()
    pairs = texts(catalog)
    if redo:
        todo = [(t, r) for t, r in pairs if index.get(key(t, r), {}).get("p") == redo]
        chain = [p for p in chain if p.name != redo]
    first = next((p for p in chain if not p.ready(keys, profile)), None)
    if not redo:
        # A shipped clip is already Google's voice: it is made again only when the learner's first
        # ready provider speaks with other voices, so one speaker keeps one voice everywhere.
        todo = missing(pairs, skip_shipped=first is None or first.family == SHIPPED_FAMILY)
    if limit is not None:
        todo = todo[:limit]
    # The first ready provider's family makes everything it can, over a few rounds (a refusal is
    # often only throttling), so one speaker does not change voice; the rest of the list fills in
    # only what that family still could not make.
    family = [p for p in chain if first and p.family == first.family]
    passes = [family] * rounds + [chain] if family and family != chain else [chain] * max(1, rounds)
    made: dict[str, int] = {}
    left = list(todo)
    done_n = 0
    for i, providers_now in enumerate(passes):
        if not left:
            break
        if i:
            time.sleep(pause)
        still = []
        for text, role in left:
            who = make(text, role, chain=providers_now, keys=keys, profile=profile, wait=wait, index=index,
                       own=is_own(text, role))
            if who:
                made[who] = made.get(who, 0) + 1
                done_n += 1
                if done_n % 25 == 0:
                    _write_index(index)
            else:
                still.append((text, role))
            if progress:
                progress(done_n + len(still) if i == 0 else done_n, len(todo), who)
        left = still
    _write_index(index)
    return {"todo": len(todo), "made": made, "failed": len(left), "total": len(pairs)}


def status(catalog=None) -> dict:
    """What the app and `oknos voice status` show: each provider's state and the files made."""
    profile, keys = read_profile(), secrets()
    used = usage()
    chosen = order(profile)
    rows = []
    for name, p in providers().items():
        rows.append({"name": name, "label": p.label, "in_order": name in chosen,
                     "position": chosen.index(name) + 1 if name in chosen else None,
                     "problem": p.ready(keys, profile), "used": used.get(name, 0), "free": p.free_chars,
                     "voices": p.voices, "sample": {r: (voice_dir() / "samples" / f"{name}-{r}.mp3").is_file() for r in ROLES}})
    index = read_index()
    by: dict[str, int] = {}
    for v in index.values():
        by[v["p"]] = by.get(v["p"], 0) + 1
    ship = shipped()
    out = {"order": chosen, "providers": rows, "files": len(index), "by_provider": by, "shipped": len(ship)}
    if catalog is not None:
        pairs = texts(catalog)
        made = set(index) | set(ship)
        out["texts"] = len(pairs)
        out["missing"] = sum(1 for t, r in pairs if key(t, r) not in made)
    return out


def make_sample(name: str, role: str = "f") -> Path:
    """The screen's test sentences, made now with one provider (or Refused)."""
    p = providers()[name]
    keys, profile = secrets(), read_profile()
    why = p.ready(keys, profile)
    if why:
        raise Refused(why)
    data = b"".join(p.make(s, role, keys) for s in SAMPLES)
    target = voice_dir() / "samples" / f"{name}-{role}.mp3"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    _add_usage(name, sum(len(s) for s in SAMPLES))
    return target
