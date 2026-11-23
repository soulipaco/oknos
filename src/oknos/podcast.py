"""Podcast lessons (phase 11, docs/PODCASTS.md).

An episode is written as text first: learner/podcasts/<id>/script.json, a list of segments (a part
mark, a line of speech in Greek, Turkish or English, a pause, a gap to repeat). The agent writes it
(the `podcast` skill); this module checks it, makes the missing clips through the voice chain
(voice.make: the same services, order and quotas as the rest of the app) and joins everything with
ffmpeg into one learner/podcasts/<id>/episode.mp3, with episode.json beside it (length, the time of
each part and line, the characters spent).

Everything here lives in learner/ and is never tracked: an episode of the private book or of the
learner's record is private. Listening is not answering, so nothing here touches the database.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import wave
from datetime import datetime
from pathlib import Path
from typing import Callable, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from oknos import greek, lint, paths, voice

ID = re.compile(r"^[a-z0-9][a-z0-9.\-]{0,79}$")
RATE = 24_000          # the episode's sample rate (mono); the voice services send 24 kHz
GAP = 0.35             # the breath after each line of speech, in seconds
ECHO_EXTRA = 1.0       # an echo gap is the last line's length × its factor, plus this
CHARS_PER_SECOND = {"el": 11.0, "tr": 14.0, "en": 14.0}  # for the estimate before anything is made


class PodcastError(Exception):
    """A script that cannot be used, or an episode that cannot be made; the message says why."""


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Part(Strict):
    """A chapter mark: the player lists them and jumps to them."""

    part: str = Field(min_length=1, max_length=80)


class Say(Strict):
    """One clip of speech. Greek lines may name a speaker (`who`) for their voice; speed < 1 is slower."""

    lang: Literal["el", "tr", "en"]
    say: str = Field(min_length=1, max_length=900)
    who: str | None = None
    role: Literal["f", "m"] | None = None
    speed: float = Field(default=1.0, ge=0.6, le=1.0)

    def voice_role(self) -> str:
        if self.role:
            return self.role
        return voice.role_of(self.who) if self.lang == "el" else "f"


class Pause(Strict):
    pause: float = Field(ge=0.2, le=20)


class Echo(Strict):
    """A gap to repeat after the speaker: the last line's length × echo, plus a second."""

    echo: float = Field(ge=0.5, le=3)


Segment = Union[Part, Say, Pause, Echo]


class Source(Strict):
    what: Literal["chapter", "open-chapter", "glossary", "report", "idea"]
    ref: str | None = None
    url: str | None = None
    note: str | None = None


class Title(Strict):
    tr: str = Field(min_length=1)
    en: str = Field(min_length=1)


class Script(Strict):
    id: str
    kind: Literal["chapter", "daily", "weekly"]
    curriculum: str | None = None
    stage: str | None = None
    lang: Literal["tr", "en"]
    title: Title
    version: int = 1
    written: str
    sources: list[Source] = []
    segments: list[Segment] = Field(min_length=3)


_SCRIPT = TypeAdapter(Script)


# ---------- where things are ----------

def podcasts_dir() -> Path:
    return paths.learner_dir() / "podcasts"


def episode_dir(pid: str) -> Path:
    if not ID.match(pid or ""):
        raise PodcastError(f"not an episode id: {pid!r}")
    return podcasts_dir() / pid


def audio_file(pid: str) -> Path | None:
    """The episode's mp3, or None (unknown id, or not rendered yet)."""
    try:
        f = episode_dir(pid) / "episode.mp3"
    except PodcastError:
        return None
    return f if f.is_file() else None


# ---------- reading and checking a script ----------

def load(pid: str) -> Script:
    f = episode_dir(pid) / "script.json"
    try:
        raw = json.loads(f.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise PodcastError(f"no script at {f}") from None
    except json.JSONDecodeError as e:
        raise PodcastError(f"{f.name} is not valid JSON: {e}") from None
    return parse(raw, pid)


def parse(raw: dict, pid: str | None = None) -> Script:
    try:
        script = _SCRIPT.validate_python(raw)
    except ValidationError as e:
        lines = [f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in e.errors()[:12]]
        raise PodcastError("the script does not fit the format:\n  " + "\n  ".join(lines)) from None
    if pid and script.id != pid:
        raise PodcastError(f"the script's id is {script.id!r}, but its folder is {pid!r}")
    if not ID.match(script.id):
        raise PodcastError(f"not an episode id: {script.id!r} (lower case letters, digits, '.' and '-')")
    return script


def problems(script: Script) -> tuple[list[str], list[str]]:
    """(problems, notes). A problem stops the render; a note is worth a look."""
    bad: list[str] = []
    notes: list[str] = []
    if not isinstance(script.segments[0], Part):
        bad.append("the first segment must be a part (a chapter mark)")
    previous = None
    for i, seg in enumerate(script.segments):
        where = f"segment {i}"
        if isinstance(seg, Say):
            if seg.lang == "el":
                if not greek.has_greek(seg.say):
                    bad.append(f"{where}: a Greek line with no Greek in it: {seg.say[:60]!r}")
                p, n = lint.check_text(seg.say)
                bad += [f"{where}: {x}: {seg.say[:60]!r}" for x in p]
                notes += [f"{where}: {x}" for x in n]
            elif greek.has_greek(seg.say):
                bad.append(f"{where}: Greek letters inside a {seg.lang} line (the {seg.lang} voice would mangle them; "
                           f"put the Greek in its own segment): {seg.say[:60]!r}")
        if isinstance(seg, Echo) and not isinstance(previous, Say):
            bad.append(f"{where}: an echo gap must follow a line of speech")
        previous = seg
    if not any(isinstance(s, Say) and s.lang == script.lang for s in script.segments):
        notes.append(f"no line in the script's own language ({script.lang})")
    return bad, notes


def lines(script: Script) -> list[tuple[str, str, str]]:
    """Every (text, role, lang) the episode speaks, each once."""
    seen: set[tuple[str, str, str]] = set()
    out = []
    for s in script.segments:
        if isinstance(s, Say):
            k = (voice.norm(s.say), s.voice_role(), s.lang)
            if k not in seen:
                seen.add(k)
                out.append((s.say.strip(), s.voice_role(), s.lang))
    return out


def estimate_seconds(script: Script) -> float:
    total, last = 0.0, 0.0
    for s in script.segments:
        if isinstance(s, Say):
            last = len(s.say) / CHARS_PER_SECOND[s.lang] / s.speed
            total += last + GAP
        elif isinstance(s, Pause):
            total += s.pause
        elif isinstance(s, Echo):
            total += last * s.echo + ECHO_EXTRA
    return total


def _chain(profile: dict, keys: dict) -> list[voice.Provider]:
    known = voice.providers()
    return [known[p] for p in voice.order(profile)]


def cost(script: Script) -> dict:
    """What a render would spend: the clips still to make and their characters, per language and per
    service (the first ready one that speaks that language; edge never: these are the agent's texts)."""
    profile, keys = voice.read_profile(), voice.secrets()
    chain = _chain(profile, keys)
    used = voice.usage()
    todo = [(t, r, lang) for t, r, lang in lines(script) if voice.find(t, r, lang) is None]
    by_lang: dict[str, dict] = {}
    by_provider: dict[str, int] = {}
    nobody = 0
    for t, r, lang in todo:
        row = by_lang.setdefault(lang, {"clips": 0, "chars": 0})
        row["clips"] += 1
        row["chars"] += len(t)
        who = next((p.name for p in chain if not p.ready(keys, profile) and p.name != "edge" and p.speaks(lang)), None)
        if who:
            by_provider[who] = by_provider.get(who, 0) + len(t)
        else:
            nobody += 1
    providers = {}
    for name, chars in by_provider.items():
        p = voice.providers()[name]
        providers[name] = {"chars": chars, "used_this_month": used.get(name, 0), "free": p.free_chars}
    return {"lines": len(lines(script)), "to_make": len(todo), "chars": sum(len(t) for t, _, _ in todo),
            "by_lang": by_lang, "by_provider": providers, "no_service": nobody}


def check(pid: str) -> dict:
    """Everything `oknos podcast check` prints: problems, notes, length and cost."""
    script = load(pid)
    bad, notes = problems(script)
    return {"id": script.id, "problems": bad, "notes": notes, "segments": len(script.segments),
            "parts": [s.part for s in script.segments if isinstance(s, Part)],
            "minutes": round(estimate_seconds(script) / 60, 1), "cost": cost(script)}


# ---------- making the audio ----------

def ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise PodcastError("ffmpeg is not installed (or not on PATH); it joins the clips into one file. "
                           "Install it (winget install Gyan.FFmpeg, brew install ffmpeg, apt install ffmpeg) and try again.")
    return exe


def _run(args: list[str]) -> None:
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise PodcastError(f"ffmpeg failed: {r.stderr.strip()[-400:]}")


def _to_wav(exe: str, clip: Path, out: Path, speed: float) -> bytes:
    """The clip as raw 16-bit mono frames at RATE, slowed with atempo (the pitch stays)."""
    filters = [f"atempo={speed:.3f}"] if speed < 0.999 else []
    filters.append(f"aresample={RATE}")
    _run([exe, "-v", "error", "-y", "-i", str(clip), "-af", ",".join(filters), "-ac", "1", "-ar", str(RATE),
          "-c:a", "pcm_s16le", str(out)])
    with wave.open(str(out), "rb") as w:
        return w.readframes(w.getnframes())


def _silence(seconds: float) -> bytes:
    return b"\x00\x00" * int(round(seconds * RATE))


def script_hash(pid: str) -> str:
    return hashlib.sha1((episode_dir(pid) / "script.json").read_bytes()).hexdigest()[:12]


def render(pid: str, *, wait: bool = False, progress: Callable[[str, int, int], None] | None = None) -> dict:
    """Make the missing clips, join the episode, write episode.mp3 and episode.json. Returns episode.json."""
    script = load(pid)
    bad, _ = problems(script)
    if bad:
        raise PodcastError("the script has problems (oknos podcast check):\n  " + "\n  ".join(bad[:12]))
    exe = ffmpeg()
    profile, keys = voice.read_profile(), voice.secrets()
    chain = _chain(profile, keys)
    index = voice.read_index()
    made: dict[str, int] = {}
    spent: dict[str, int] = {}
    todo = [(t, r, lang) for t, r, lang in lines(script) if voice.find(t, r, lang) is None]
    try:
        for i, (t, r, lang) in enumerate(todo, 1):
            who = voice.make(t, r, chain=chain, keys=keys, profile=profile, wait=wait, index=index, own=True, lang=lang)
            if who is None:
                raise PodcastError(f"no voice service could make this {lang} line (keys, quota, or the list on the "
                                   f"Voice screen): {t[:80]!r}")
            made[who] = made.get(who, 0) + 1
            spent[who] = spent.get(who, 0) + len(t)
            if progress:
                progress("clips", i, len(todo))
    finally:
        if made:
            voice._write_index(index)

    out_dir = episode_dir(pid)
    frames: list[bytes] = []
    timeline_parts: list[dict] = []
    timeline_lines: list[dict] = []
    t = 0.0
    last = 0.0
    says = sum(1 for s in script.segments if isinstance(s, Say))
    done = 0
    with tempfile.TemporaryDirectory(prefix="oknos-podcast-") as tmp:
        tmpdir = Path(tmp)
        for seg in script.segments:
            if isinstance(seg, Part):
                timeline_parts.append({"t": round(t, 2), "title": seg.part})
            elif isinstance(seg, Say):
                role = seg.voice_role()
                clip = voice.find(seg.say, role, seg.lang)
                if clip is None:  # made above; gone since?
                    raise PodcastError(f"the clip for {seg.say[:60]!r} is missing")
                data = _to_wav(exe, clip, tmpdir / "piece.wav", seg.speed)
                last = len(data) / 2 / RATE
                line = {"t": round(t, 2), "lang": seg.lang, "say": seg.say}
                if seg.who:
                    line["who"] = seg.who
                if seg.speed < 0.999:
                    line["speed"] = seg.speed
                timeline_lines.append(line)
                frames += [data, _silence(GAP)]
                t += last + GAP
                done += 1
                if progress:
                    progress("join", done, says)
            elif isinstance(seg, Pause):
                frames.append(_silence(seg.pause))
                t += seg.pause
            elif isinstance(seg, Echo):
                gap = last * seg.echo + ECHO_EXTRA
                frames.append(_silence(gap))
                t += gap
        joined = tmpdir / "joined.wav"
        with wave.open(str(joined), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            for f in frames:
                w.writeframes(f)
        target = out_dir / "episode.mp3"
        partial = out_dir / "episode.part.mp3"
        # One loudness pass over the whole (clips from different services differ a little), then mp3.
        _run([exe, "-v", "error", "-y", "-i", str(joined), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
              "-ar", str(RATE), "-ac", "1", "-c:a", "libmp3lame", "-b:a", "64k",
              "-metadata", f"title={script.title.tr if script.lang == 'tr' else script.title.en}",
              "-metadata", "artist=Oknos", "-f", "mp3", str(partial)])
        partial.replace(target)

    meta = {"id": script.id, "kind": script.kind, "lang": script.lang, "title": script.title.model_dump(),
            "curriculum": script.curriculum, "stage": script.stage, "version": script.version,
            "written": script.written, "rendered": datetime.now().isoformat(timespec="seconds"),
            "seconds": round(t, 1), "script": script_hash(pid), "parts": timeline_parts, "lines": timeline_lines,
            "made": made, "chars": spent}
    (out_dir / "episode.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return meta


# ---------- what the app shows ----------

def episode(pid: str) -> dict | None:
    """episode.json of a rendered episode, with `stale` when the script changed since; None if not rendered."""
    if audio_file(pid) is None:
        return None
    try:
        meta = json.loads((episode_dir(pid) / "episode.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    try:
        meta["stale"] = meta.get("script") != script_hash(pid)
    except FileNotFoundError:
        meta["stale"] = False
    return meta


def listing() -> list[dict]:
    """The rendered episodes, newest first (scripts not yet rendered are left out of the app)."""
    out = []
    base = podcasts_dir()
    if not base.is_dir():
        return out
    for d in base.iterdir():
        if d.is_dir() and ID.match(d.name):
            meta = episode(d.name)
            if meta:
                out.append({k: meta.get(k) for k in ("id", "kind", "lang", "title", "curriculum", "stage",
                                                     "written", "rendered", "seconds", "stale")}
                           | {"parts": len(meta.get("parts", []))})
    out.sort(key=lambda m: m.get("rendered") or "", reverse=True)
    return out


def scripts() -> list[dict]:
    """Every script in learner/podcasts/, rendered or not (`oknos podcast list`)."""
    out = []
    base = podcasts_dir()
    if not base.is_dir():
        return out
    for d in sorted(base.iterdir()):
        if d.is_dir() and (d / "script.json").is_file():
            row = {"id": d.name}
            try:
                s = load(d.name)
                row |= {"kind": s.kind, "lang": s.lang, "stage": s.stage, "minutes": round(estimate_seconds(s) / 60, 1)}
            except PodcastError as e:
                row["error"] = str(e).splitlines()[0]
            meta = episode(d.name)
            row["rendered"] = bool(meta)
            if meta:
                row |= {"seconds": meta["seconds"], "stale": meta["stale"]}
            out.append(row)
    return out

