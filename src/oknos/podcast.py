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
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from oknos import casting, greek, lint, paths, voice

ID = re.compile(r"^[a-z0-9][a-z0-9.\-]{0,79}$")
RATE = 24_000          # the episode's sample rate (mono); the voice services send 24 kHz
GAP = 0.45             # the breath after each line of speech, in seconds
ECHO_EXTRA = 1.0       # an echo gap is the last line's length × its factor, plus this
SILENCE_DB = -50       # below this, the start and end of a clip count as silence and are trimmed
# For the estimate before anything is made (fitted to the pilot: Azure Athina and Emel, clips trimmed).
CHARS_PER_SECOND = {"el": 10.5, "tr": 14.0, "en": 14.0}


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

    def voice_role(self, cast: dict[str, "CastMember"] | None = None) -> str:
        if self.role:
            return self.role
        if cast and self.who in cast:
            return cast[self.who].gender
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


class CastMember(Strict):
    """One voice of the episode (format v2, docs/PODCASTS.md "The cast"): a host, a guest or a character.
    A speech segment's `who` names its id; the voice session maps the cast to the voices in the pool."""

    id: str = Field(pattern=r"^[a-z][a-z0-9\-]{0,30}$")
    name: str = Field(min_length=1, max_length=40)
    role: Literal["host", "cohost", "guest", "character", "narrator"]
    lang: list[Literal["el", "tr", "en"]] = Field(min_length=1)
    gender: Literal["f", "m"]
    age: str | None = None
    manner: str | None = Field(default=None, max_length=200)
    # The voice for one casting family, chosen by the script (docs/PODCASTS.md "The voices"),
    # e.g. {"google": "Leda"}; without it the casting (src/oknos/casting.json) chooses.
    voice: dict[str, str] | None = None


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
    # Personal episodes (daily, weekly): the day the episode is for (a weekly one: the first day of its
    # week), and what it drilled (Greek words and points), so the next episode does not repeat them.
    date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    focus: list[str] = []
    cast: list[CastMember] = []
    sources: list[Source] = []
    segments: list[Segment] = Field(min_length=3)


def cast_of(script: "Script") -> dict[str, CastMember]:
    return {c.id: c for c in script.cast}


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
    cast = cast_of(script)
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
            elif greek.has_greek(seg.say) and seg.who in cast and "el" in cast[seg.who].lang:
                notes.append(f"{where}: Greek inside a {seg.lang} line, said by {cast[seg.who].name} in one breath; "
                             f"only a voice that speaks mixed lines (gemini) can make it: {seg.say[:60]!r}")
            elif greek.has_greek(seg.say):
                bad.append(f"{where}: Greek letters inside a {seg.lang} line (the {seg.lang} voice would mangle them; "
                           f"put the Greek in its own segment): {seg.say[:60]!r}")
        if isinstance(seg, Echo) and not isinstance(previous, Say):
            bad.append(f"{where}: an echo gap must follow a line of speech")
        previous = seg
    if len(cast) != len(script.cast):
        bad.append("two cast members share an id")
    if cast:
        for i, seg in enumerate(script.segments):
            if isinstance(seg, Say) and seg.who:
                member = cast.get(seg.who)
                if member is None:
                    bad.append(f"segment {i}: {seg.who!r} is not in the cast")
                elif seg.lang not in member.lang:
                    bad.append(f"segment {i}: {member.name} does not speak {seg.lang} (cast lang: {member.lang})")
    if script.kind != "chapter":
        if not script.date:
            bad.append(f"a {script.kind} episode needs its date (the day it is for)")
        elif not script.id.startswith(f"{script.kind}."):
            bad.append(f"a {script.kind} episode's id starts with '{script.kind}.' (oknos podcast material prints it)")
        if not any(s.what == "report" for s in script.sources):
            notes.append("a personal episode usually names the report among its sources")
    if not any(isinstance(s, Say) and s.lang == script.lang for s in script.segments):
        notes.append(f"no line in the script's own language ({script.lang})")
    return bad, notes


def lines(script: Script) -> list[tuple[str, str, str]]:
    """Every (text, role, lang) the episode speaks, each once."""
    seen: set[tuple[str, str, str]] = set()
    out = []
    cast = cast_of(script)
    for s in script.segments:
        if isinstance(s, Say):
            k = (voice.norm(s.say), s.voice_role(cast), s.lang)
            if k not in seen:
                seen.add(k)
                out.append((s.say.strip(), s.voice_role(cast), s.lang))
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
    """The podcast's voices: `podcast.providers` in the profile (e.g. ["gemini", "google"]), else the
    app's own order (the Voice screen)."""
    known = voice.podcast_providers()
    chosen = (profile.get("podcast") or {}).get("providers") or voice.order(profile)
    return [known[p] for p in chosen if p in known]


def _cast_path(chain: list[voice.Provider], profile: dict, keys: dict) -> bool:
    """Episodes are cast (a voice per person, exchanges, the jingle) when the first ready service has
    named voices; otherwise each line is a clip of the app's female or male voice, as before."""
    first = next((p for p in chain if not p.ready(keys, profile) and p.name != "edge"), None)
    return bool(first and first.named)


def cost(script: Script) -> dict:
    """What a render would spend: the clips still to make and their characters, per language and per
    service (the first ready one that speaks that language; edge never: these are the agent's texts)."""
    profile, keys = voice.read_profile(), voice.secrets()
    chain = _chain(profile, keys)
    used = voice.usage()
    if _cast_path(chain, profile, keys):
        return _cast_cost(script, chain, profile, keys, used)
    todo = [(t, r, lang) for t, r, lang in lines(script) if voice.find(t, r, lang) is None]
    by_lang: dict[str, dict] = {}
    by_provider: dict[str, int] = {}
    nobody = 0
    for t, r, lang in todo:
        row = by_lang.setdefault(lang, {"clips": 0, "chars": 0})
        row["clips"] += 1
        row["chars"] += len(t)
        who = next((p.name for p in chain if not p.ready(keys, profile) and p.name != "edge" and not p.podcast_only
                    and p.speaks(lang)), None)
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
    """The clip as raw 16-bit mono frames at RATE: the services' silence at both ends trimmed (the
    script's own pauses and gaps set the rhythm, and an echo gap is measured on the speech alone),
    then slowed with atempo (the pitch stays)."""
    trim = f"silenceremove=start_periods=1:start_threshold={SILENCE_DB}dB:start_silence=0.05"
    filters = [trim, "areverse", trim, "areverse"]
    if speed < 0.999:
        filters.append(f"atempo={speed:.3f}")
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
    if _cast_path(chain, profile, keys):
        return _render_cast(pid, script, exe, chain, profile, keys, progress)
    mixed = [s.say for s in script.segments if isinstance(s, Say) and s.lang != "el" and greek.has_greek(s.say)]
    if mixed:
        raise PodcastError(f"a line has Greek inside a {script.lang} sentence, which only a cast episode with a "
                           f"voice that speaks mixed lines (gemini) can make: {mixed[0][:60]!r}")
    chain = [p for p in chain if not p.podcast_only]
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
    cast = cast_of(script)
    with tempfile.TemporaryDirectory(prefix="oknos-podcast-") as tmp:
        tmpdir = Path(tmp)
        for seg in script.segments:
            if isinstance(seg, Part):
                timeline_parts.append({"t": round(t, 2), "title": seg.part})
            elif isinstance(seg, Say):
                role = seg.voice_role(cast)
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
            "written": script.written, "date": script.date, "rendered": datetime.now().isoformat(timespec="seconds"),
            "seconds": round(t, 1), "script": script_hash(pid), "parts": timeline_parts, "lines": timeline_lines,
            "made": made, "chars": spent}
    (out_dir / "episode.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return meta


# ---------- cast episodes: a voice per person, exchanges acted together, the jingle ----------
#
# When the first ready service has named voices (gemini, google), an episode is cast: each person of
# the script gets their own voice (oknos.casting), consecutive lines between at most two people are
# made in one request by a service that acts dialogue (gemini), gaps follow the turn-taking, and a
# short jingle opens and closes the episode, with a sting between parts. Clips are kept in
# learner/voice/podcast/ and listed in episode.json, so a second render spends nothing.

# Gemini's Tier 1 allows 100 requests a day per model (2026-11-25: a 14-minute pilot made line by line
# needed 103), so a service that acts dialogue gets long requests: up to 24 lines or 2,400 characters
# (about three minutes of speech), an echoed or slowed line included. A service that reads line by
# line gets one request a line anyway.
MAX_TURNS = 24              # lines in one request
MAX_EXCHANGE_CHARS = 2400   # characters in one request
GEMINI_DAILY_REQUESTS = 100
AUDIO_TOKENS_PER_SECOND = 25  # Gemini bills audio by tokens, about 25 a second of speech


@dataclass
class Unit:
    """Lines spoken in one go: an exchange between two people, one person's run, or one line."""

    lines: list[tuple[Say, str]]  # (segment, member id)
    solo: bool = False            # made on its own (a service that reads line by line: slowed, or echoed)

    def ids(self) -> set[str]:
        return {mid for _, mid in self.lines}

    def chars(self) -> int:
        return sum(len(s.say) for s, _ in self.lines)


def plan(script: Script, who_of: dict[int, str], acts: bool = True) -> list:
    """The episode as parts, pauses, echo gaps and units of speech. For a service that acts dialogue
    (`acts`), a slowed line is asked to be slow in its style and an echoed line ends its unit (the gap
    is measured on its share); otherwise each of them is made on its own, slowed with atempo."""
    items: list = []
    cur: Unit | None = None
    segs = script.segments
    for i, seg in enumerate(segs):
        if not isinstance(seg, Say):
            items.append(seg)
            cur = None
            continue
        mid = who_of[i]
        solo = not acts and (seg.speed < 0.999 or (i + 1 < len(segs) and isinstance(segs[i + 1], Echo)))
        if (cur is not None and not solo and len(cur.ids() | {mid}) <= 2 and len(cur.lines) < MAX_TURNS
                and cur.chars() + len(seg.say) <= MAX_EXCHANGE_CHARS):
            cur.lines.append((seg, mid))
            continue
        cur = Unit([(seg, mid)], solo=solo)
        items.append(cur)
        if solo:
            cur = None
    return items


def _mixed(seg: Say) -> bool:
    return seg.lang != "el" and greek.has_greek(seg.say)


def _can(p: voice.Provider, unit: Unit, keys: dict, profile: dict) -> bool:
    if p.ready(keys, profile) or p.name == "edge":  # edge never: the scripts are the agent's own texts
        return False
    return all(p.speaks(seg.lang) and (p.mixed or not _mixed(seg)) for seg, _ in unit.lines)


def _requests(unit: Unit, p: voice.Provider, voices: dict[str, str], members: dict, lang: str) -> list[dict]:
    """What the service is asked for this unit: one request (an exchange, or one person's run) when it
    acts dialogue, else one per line."""
    def styled(seg, mid):
        if not p.dialogue:
            return None
        text = casting.style(members[mid], lang)
        if seg.speed < 0.999:
            text += (f" Say this line slowly and clearly, at about {round(seg.speed * 100)}% of normal pace, "
                     f"so a learner can repeat it.")
        return text

    lines_ = [{"who": mid, "voice": voices.get(mid), "role": members[mid].gender, "text": seg.say.strip(),
               "lang": seg.lang, "speed": seg.speed, "style": styled(seg, mid)}
              for seg, mid in unit.lines]
    if p.dialogue and len(lines_) > 1 and len(unit.ids()) == 2:
        return [{"mode": "exchange", "lines": lines_}]  # each line carries its own style, its pace included
    if p.dialogue and len(lines_) > 1:
        # One person's run is one text with one style: lines at another pace go in a request of their own.
        groups: list[list[dict]] = []
        for x in lines_:
            if groups and groups[-1][-1]["speed"] == x["speed"]:
                groups[-1].append(x)
            else:
                groups.append([x])
        return [{"mode": "run" if len(g) > 1 else "line", "lines": g} for g in groups]
    return [{"mode": "line", "lines": [x]} for x in lines_]


def _request_key(req: dict, p: voice.Provider) -> str:
    sig = [p.name, getattr(p, "MODEL", ""), req["mode"],
           [(x["voice"] or x["role"], x["style"] or "", x["text"], x["lang"]) for x in req["lines"]]]
    return hashlib.sha1(json.dumps(sig, ensure_ascii=False).encode("utf-8")).hexdigest()


def cast_clip(k: str) -> Path:
    return voice.voice_dir() / "podcast" / k[:2] / f"{k}.clip"  # mp3 or wav: ffmpeg reads either


def _ask(req: dict, p: voice.Provider, keys: dict, text_of=lambda x: x["text"]) -> bytes:
    ls = req["lines"]
    if req["mode"] == "exchange":
        return p.make_exchange([(x["who"], x["voice"], text_of(x), x["style"]) for x in ls], keys)
    x = ls[0]
    text = " ".join(text_of(y) for y in ls)
    if p.named:
        return p.make(text, x["role"], keys, lang=x["lang"], voice_name=x["voice"], style=x["style"])
    return p.make(text, x["role"], keys) if x["lang"] == "el" else p.make(text, x["role"], keys, lang=x["lang"])


def _cast_cost(script: Script, chain, profile, keys, used) -> dict:
    members, who_of = casting.speakers(script)
    _, units, chain = _planned(script, who_of, chain, keys, profile, members, script.lang)
    requests: dict[str, int] = {}
    by_lang: dict[str, dict] = {}
    by_provider: dict[str, int] = {}
    nobody = to_make = 0
    for u in units:
        p = next((p for p in chain if _can(p, u, keys, profile)), None)
        if p is None:
            nobody += len(u.lines)
            continue
        voices = casting.assign(members, casting.family_of(p.name))
        for req in _requests(u, p, voices, members, script.lang):
            if cast_clip(_request_key(req, p)).is_file():
                continue
            to_make += 1
            requests[p.name] = requests.get(p.name, 0) + 1
            for x in req["lines"]:
                row = by_lang.setdefault(x["lang"], {"clips": 0, "chars": 0})
                row["clips"] += 1
                row["chars"] += len(x["text"])
                by_provider[p.name] = by_provider.get(p.name, 0) + len(x["text"])
    known = voice.podcast_providers()
    providers = {}
    for name, chars in by_provider.items():
        providers[name] = {"chars": chars, "used_this_month": used.get(name, 0), "free": known[name].free_chars}
        providers[name]["requests"] = requests.get(name, 0)
        if name == "gemini":
            providers[name]["tokens"] = int(chars / CHARS_PER_SECOND["tr"] * AUDIO_TOKENS_PER_SECOND)
            providers[name]["daily_requests"] = GEMINI_DAILY_REQUESTS
            providers[name]["requests_today"] = voice.requests_today("gemini")
    first = next((p for p in chain if not p.ready(keys, profile) and p.name != "edge"), None)
    voices = casting.assign(members, casting.family_of(first.name)) if first else {}
    return {"lines": sum(len(u.lines) for u in units), "to_make": to_make, "chars": sum(by_provider.values()),
            "by_lang": by_lang, "by_provider": providers, "no_service": nobody,
            "cast": {mid: {"name": m.name, "voice": voices.get(mid, m.gender)} for mid, m in members.items()}}


def _turn_gap(prev: tuple[str, str] | None, cur: tuple[str, str]) -> float:
    """The silence between two turns: short in a dialogue, longer where the language changes."""
    if prev is None:
        return 0.0
    (pw, pl), (cw, cl) = prev, cur
    if pl != cl:
        return 0.6
    if pw == cw:
        return 0.25
    return 0.3 if cl == "el" else 0.35


# The show's sounds, made from numbers (original, like the films' ambience): a plucked motif in D.
_NOTE = "{a}*(sin(2*PI*{f}*(t-{s}))+0.35*sin(4*PI*{f}*(t-{s})))*exp(-{d}*(t-{s}))*gte(t\\,{s})"
SOUNDS = {
    "open": (2.6, [(0, 146.83, .08, 1.2), (0, 293.66, .14, 3.5), (.17, 349.23, .14, 3.5), (.34, 440.0, .14, 3.5),
                   (.51, 587.33, .16, 2.5)]),
    "sting": (1.1, [(0, 440.0, .12, 4.0), (.13, 587.33, .12, 3.5)]),
    "close": (2.8, [(0, 587.33, .14, 3.5), (.17, 440.0, .14, 3.5), (.34, 349.23, .14, 3.5), (.51, 293.66, .16, 2.0),
                    (.51, 146.83, .08, 1.2)]),
}


def _sound(exe: str, kind: str, tmpdir: Path) -> bytes:
    dur, notes = SOUNDS[kind]
    expr = "+".join(_NOTE.format(a=a, f=f, s=s, d=d) for s, f, a, d in notes)
    out = tmpdir / f"{kind}.wav"
    _run([exe, "-v", "error", "-y", "-f", "lavfi", "-i", f"aevalsrc=exprs={expr}:s={RATE}:d={dur}",
          "-af", f"afade=t=out:st={dur - 0.5:.2f}:d=0.5", "-ac", "1", "-ar", str(RATE), "-c:a", "pcm_s16le", str(out)])
    with wave.open(str(out), "rb") as w:
        return w.readframes(w.getnframes())


def _planned(script: Script, who_of: dict[int, str], chain, keys, profile,
             members: dict | None = None, lang: str = "tr") -> tuple[list, list[Unit], list]:
    """One service voices the whole episode: the first that can say all of it and, for Gemini, whose
    requests still to make fit what is left of the day's limit (else the next one makes the whole
    episode: an episode in the fallback's sound rather than none). A refusal halfway then stops the
    render (clips made so far are kept, so a second render goes on from there) instead of mixing two
    services' sounds in one episode."""
    fine = [u for u in plan(script, who_of, acts=False) if isinstance(u, Unit)]
    for p in chain:
        if not all(_can(p, u, keys, profile) for u in fine):
            continue
        items = plan(script, who_of, acts=p.dialogue)
        units = [u for u in items if isinstance(u, Unit)]
        if p.name == "gemini" and members is not None:
            voices = casting.assign(members, casting.family_of(p.name))
            needed = sum(1 for u in units for req in _requests(u, p, voices, members, lang)
                         if not cast_clip(_request_key(req, p)).is_file())
            if needed > GEMINI_DAILY_REQUESTS - voice.requests_today("gemini"):
                continue
        return items, units, [p]
    items = plan(script, who_of, acts=False)
    return items, [u for u in items if isinstance(u, Unit)], chain


def _render_cast(pid: str, script: Script, exe: str, chain, profile, keys, progress) -> dict:
    members, who_of = casting.speakers(script)
    items, units, chain = _planned(script, who_of, chain, keys, profile, members, script.lang)
    out_dir = episode_dir(pid)
    made: dict[str, int] = {}
    spent: dict[str, int] = {}
    tokens = 0
    used_keys: list[str] = []
    voices_used: dict[str, str] = {}
    frames: list[bytes] = []
    parts: list[dict] = []
    timeline: list[dict] = []
    t = last = 0.0
    prev: tuple[str, str] | None = None
    first_part = True
    done = 0
    with tempfile.TemporaryDirectory(prefix="oknos-podcast-") as tmp:
        tmpdir = Path(tmp)

        def add(data: bytes) -> float:
            nonlocal t
            frames.append(data)
            secs = len(data) / 2 / RATE
            t += secs
            return secs

        add(_sound(exe, "open", tmpdir) + _silence(0.4))
        for item in items:
            if isinstance(item, Part):
                if not first_part:
                    add(_silence(0.5) + _sound(exe, "sting", tmpdir) + _silence(0.3))
                first_part = False
                parts.append({"t": round(t, 2), "title": item.part})
                prev = None
            elif isinstance(item, Pause):
                add(_silence(item.pause))
                prev = None
            elif isinstance(item, Echo):
                add(_silence(last * item.echo + ECHO_EXTRA))
                prev = None
            else:
                for p, req, data, k in _voice_unit(item, chain, members, script.lang, keys, profile, exe, tmpdir):
                    add(_silence(_turn_gap(prev, (req["lines"][0]["who"], req["lines"][0]["lang"]))))
                    start = t
                    secs = add(data)
                    total = sum(len(x["text"]) for x in req["lines"]) or 1
                    at = start
                    for x in req["lines"]:  # lines within one request: placed by their share of the characters
                        line = {"t": round(at, 2), "lang": x["lang"], "say": x["text"], "who": x["who"]}
                        if x["speed"] < 0.999:
                            line["speed"] = x["speed"]
                        timeline.append(line)
                        last = secs * len(x["text"]) / total  # an echo gap after it is measured on this line
                        at += last
                        voices_used[x["who"]] = x["voice"] or x["role"]
                    prev = (req["lines"][-1]["who"], req["lines"][-1]["lang"])
                    used_keys.append(k)
                    if p is not None:
                        made[p.name] = made.get(p.name, 0) + 1
                        spent[p.name] = spent.get(p.name, 0) + total
                        tokens += getattr(p, "tokens", 0) if p.name == "gemini" else 0
                done += 1
                if progress:
                    progress("clips", done, len(units))
        add(_silence(0.8) + _sound(exe, "close", tmpdir))
        joined = tmpdir / "joined.wav"
        with wave.open(str(joined), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            for f in frames:
                w.writeframes(f)
        target = out_dir / "episode.mp3"
        partial = out_dir / "episode.part.mp3"
        _run([exe, "-v", "error", "-y", "-i", str(joined), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
              "-ar", str(RATE), "-ac", "1", "-c:a", "libmp3lame", "-b:a", "64k",
              "-metadata", f"title={script.title.tr if script.lang == 'tr' else script.title.en}",
              "-metadata", "artist=Oknos", "-f", "mp3", str(partial)])
        partial.replace(target)
    meta = {"id": script.id, "kind": script.kind, "lang": script.lang, "title": script.title.model_dump(),
            "curriculum": script.curriculum, "stage": script.stage, "version": script.version,
            "written": script.written, "date": script.date, "rendered": datetime.now().isoformat(timespec="seconds"),
            "seconds": round(t, 1), "script": script_hash(pid), "parts": parts, "lines": timeline,
            "made": made, "chars": spent,
            "cast": {mid: {"name": members[mid].name, "voice": v} for mid, v in voices_used.items()},
            "clips": sorted(set(used_keys)), "sounds": True}
    if tokens:
        meta["tokens"] = tokens
    (out_dir / "episode.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return meta


def _voice_unit(unit: Unit, chain, members, lang, keys, profile, exe, tmpdir) -> list[tuple]:
    """The unit's audio as (service, or None when the clip was kept; request; frames; key), from the
    first service that can make all of it; a service refusing a request passes the unit on."""
    why = "no service in the podcast's list can make it (keys, or podcast.providers in the profile)"
    if any(_mixed(seg) for seg, _ in unit.lines) and not any(p.mixed and not p.ready(keys, profile) for p in chain):
        why = "it has Greek inside a Turkish or English sentence, and no ready service speaks mixed lines (gemini)"
    speed = unit.lines[0][0].speed if unit.solo else 1.0
    for p in chain:
        if not _can(p, unit, keys, profile):
            continue
        voices = casting.assign(members, casting.family_of(p.name))
        out = []
        try:
            for req in _requests(unit, p, voices, members, lang):
                k = _request_key(req, p)
                clip = cast_clip(k)
                who = None
                if not clip.is_file():
                    data = _ask(req, p, keys)
                    clip.parent.mkdir(parents=True, exist_ok=True)
                    clip.write_bytes(data)
                    voice._add_usage(p.name, sum(len(x["text"]) for x in req["lines"]))
                    if p.name == "gemini" and getattr(p, "tokens", 0):
                        voice._add_usage("gemini_tokens", p.tokens)
                    who = p
                data = _to_wav(exe, clip, tmpdir / "piece.wav", speed)
                if len(data) < 0.15 * RATE * 2 and req["mode"] == "line":
                    # Chirp now and then answers a short word with silence: ask again, quoted (it sounds the same).
                    clip.write_bytes(_ask(req, p, keys, text_of=lambda x: f"«{x['text']}»"))
                    data = _to_wav(exe, clip, tmpdir / "piece.wav", speed)
                out.append((who, req, data, k))
            return out
        except voice.Refused as e:
            why = f"{p.name} refused: {e}; the clips made so far are kept, so rendering again goes on from here"
            continue
    raise PodcastError(f"no voice could make this part ({why}): {unit.lines[0][0].say[:60]!r}")


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
                                                     "written", "date", "rendered", "seconds", "stale")}
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



# ---------- personal episodes: today's, and keeping the folder small ----------

PERSONAL = ("daily", "weekly")
KEEP = {"daily": 14, "weekly": 8}  # the newest personal episodes kept; older ones (and their clips) go


def today_episode(today: str, lang: str | None = None) -> dict | None:
    """The personal episode to offer on the home screen: today's daily one, else this week's weekly one
    (rendered, in the learner's language when given). None if there is neither."""
    week_start = (datetime.fromisoformat(today) - timedelta(days=datetime.fromisoformat(today).weekday())).date().isoformat()
    best = None
    for m in listing():
        if m.get("kind") not in PERSONAL or not m.get("date") or (lang and m.get("lang") != lang):
            continue
        if m["kind"] == "daily" and m["date"] == today:
            return m
        if m["kind"] == "weekly" and week_start <= m["date"] <= today and (best is None or m["date"] > best["date"]):
            best = m
    return best


def prune(keep: dict[str, int] | None = None) -> dict:
    """Delete personal episodes beyond the newest KEEP of each kind, then the Turkish and English clips
    no remaining script speaks (they were made for one episode and are never heard again). Greek clips
    stay: the app uses them too. Chapter episodes are never deleted. Returns what went."""
    keep = keep or KEEP
    base = podcasts_dir()
    gone: list[str] = []
    if base.is_dir():
        for kind in PERSONAL:
            dirs = []
            for d in base.iterdir():
                if d.is_dir() and d.name.startswith(kind + ".") and ID.match(d.name):
                    try:
                        raw = json.loads((d / "script.json").read_text(encoding="utf-8-sig"))
                    except (OSError, ValueError):
                        continue
                    dirs.append((raw.get("date") or "", d))
            dirs.sort(reverse=True)
            for _, d in dirs[keep.get(kind, 0):]:
                shutil.rmtree(d)
                gone.append(d.name)
    wanted: set[str] = set()
    if base.is_dir():
        for d in base.iterdir():
            if d.is_dir() and (d / "script.json").is_file():
                try:
                    s = load(d.name)
                except PodcastError:
                    return {"episodes": gone, "clips": 0, "kept_clips_because": f"{d.name} cannot be read"}
                wanted |= {voice.key(t, r, lang) for t, r, lang in lines(s) if lang != "el"}
    removed = 0
    index = voice.read_index()
    for lang in ("tr", "en"):
        root = voice.voice_dir() / lang
        if not root.is_dir():
            continue
        for f in root.rglob("*.mp3"):
            if f.stem not in wanted:
                f.unlink()
                index.pop(f.stem, None)
                removed += 1
    if removed:
        voice._write_index(index)
    # A cast episode's clips (learner/voice/podcast/) go when no remaining episode lists them; a clip
    # made in the last three days stays, as it may belong to a render not finished yet.
    kept: set[str] = set()
    if base.is_dir():
        for d in base.iterdir():
            try:
                kept |= set(json.loads((d / "episode.json").read_text(encoding="utf-8")).get("clips", []))
            except (OSError, ValueError):
                continue
    root = voice.voice_dir() / "podcast"
    if root.is_dir():
        young = datetime.now().timestamp() - 3 * 86400
        for f in root.rglob("*.clip"):
            if f.stem not in kept and f.stat().st_mtime < young:
                f.unlink()
                removed += 1
    return {"episodes": gone, "clips": removed}
