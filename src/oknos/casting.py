"""Who speaks with which voice in a podcast episode (docs/PODCASTS.md, "The voices").

An episode's speakers come from its script: the cast it lists (format v2), plus speakers implied by
older scripts (a Turkish line with no `who` is the host, a Greek line with no `who` the Greek guest,
a Greek line with a name is that character). The show's own people keep one voice in every episode
(src/oknos/casting.json, "show"); a story character gets a voice of their gender from the pool, in an
order fixed by their name, so they sound the same in every episode, and two people of one episode
never share a voice.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from oknos import greek, voice


@dataclass
class Member:
    id: str
    name: str
    role: str                      # host, cohost, guest, character, narrator
    gender: str                    # f or m
    lang: set[str] = field(default_factory=set)
    age: str | None = None
    manner: str | None = None
    voice: dict[str, str] = field(default_factory=dict)  # family -> voice name, the script's own choice


# The show's people when a script does not list them (scripts written before format v2).
IMPLIED = {
    "ada": Member("ada", "Ada", "host", "f", {"tr", "en"}, "35", "warm, curious language teacher"),
    "mert": Member("mert", "Mert", "cohost", "m", {"tr", "en", "el"}, "32", "easy-going, the learner"),
    "katerina": Member("katerina", "Katerina", "guest", "f", {"el"}, "45", "native Greek from Thessaloniki, warm, patient, clear"),
}
ROLE_WORDS = {
    "host": "the show's host, a warm language teacher",
    "cohost": "the co-host, a learner of Greek",
    "guest": "a native Greek guest who says the examples clearly",
    "character": "a character in a short Greek scene",
    "narrator": "the narrator",
}
LANG_NAMES = {"tr": "Turkish", "en": "English"}


@lru_cache(maxsize=1)
def table() -> dict:
    return json.loads(Path(__file__).with_name("casting.json").read_text(encoding="utf-8"))


def family_of(provider: str) -> str | None:
    """The casting family of a provider (its pool of named voices), or None if it has no pool."""
    for name, fam in table()["families"].items():
        if provider in fam["providers"]:
            return name
    return None


def speakers(script) -> tuple[dict[str, Member], dict[int, str]]:
    """The episode's members, and the member id of each speech segment (by segment index)."""
    from oknos.podcast import Say  # the script's classes live in podcast.py

    members: dict[str, Member] = {}
    for c in script.cast:
        members[c.id] = Member(c.id, c.name, c.role, c.gender, set(c.lang), c.age, c.manner, dict(c.voice or {}))
    host = next((m.id for m in members.values() if m.role in ("host", "narrator")), None)
    cohost = next((m.id for m in members.values() if m.role == "cohost"), None)
    guest = next((m.id for m in members.values() if m.role == "guest"), None)

    def implied(mid: str) -> str:
        members.setdefault(mid, IMPLIED[mid])
        return mid

    who_of: dict[int, str] = {}
    for i, seg in enumerate(script.segments):
        if not isinstance(seg, Say):
            continue
        if seg.who and seg.who in members:
            who_of[i] = seg.who
        elif seg.who:  # a name (scripts before v2): a character of the scene
            mid = "c-" + hashlib.sha1(greek.fold(seg.who).encode("utf-8")).hexdigest()[:8]
            members.setdefault(mid, Member(mid, seg.who, "character", seg.role or voice.role_of(seg.who), {"el"}))
            who_of[i] = mid
        elif seg.lang == "el":
            who_of[i] = (cohost or implied("mert")) if seg.role == "m" else (guest or implied("katerina"))
        else:
            who_of[i] = (cohost or implied("mert")) if seg.role == "m" else (host or implied("ada"))
    return members, who_of


def entry(family: str, name: str) -> dict:
    """A pool voice as {gender, lang, age, about, id}: Google's are [gender, description] (every
    language, no age); ElevenLabs' are written out, with a native language and the library's id."""
    v = table()["families"][family]["voices"][name]
    if isinstance(v, dict):
        return v
    return {"gender": v[0], "about": v[1], "lang": None, "age": None, "id": name}


def voice_id(family: str, name: str) -> str:
    """What the service is asked for: the voice's id in its library (its name for Google)."""
    voices = table()["families"][family]["voices"]
    return entry(family, name)["id"] if name in voices else name


def age_band(age: str | None) -> str | None:
    """A cast member's age ("50", "30s") as the library's band: young, middle or old."""
    digits = "".join(c for c in (age or "") if c.isdigit())[:2]
    if not digits:
        return None
    n = int(digits)
    return "young" if n < 35 else "middle" if n < 60 else "old"


def assign(members: dict[str, Member], family: str | None) -> dict[str, str]:
    """member id -> voice name in the family's pool ({} for a provider without a pool)."""
    if family is None:
        return {}
    fam = table()["families"][family]
    show, pool = fam["show"], fam["voices"]
    out: dict[str, str] = {}
    for m in members.values():
        if family in m.voice and m.voice[family] in pool:
            out[m.id] = m.voice[family]
        elif m.id in show:
            out[m.id] = show[m.id]
    taken = set(out.values()) | set(show.values())  # a character never sounds like the show's people
    for m in members.values():
        if m.id in out:
            continue
        mine = [n for n in pool if entry(family, n)["gender"] == m.gender and n not in show.values()]
        band = age_band(m.age)

        def rank(n: str) -> tuple:
            # A voice of the person's language first (a Greek character, a Greek voice), then of
            # their age band when the pool says ages, then an order fixed by the name: the first
            # free voice in it is this person's.
            e = entry(family, n)
            return (e["lang"] is not None and e["lang"] not in m.lang,
                    0 if not band or e["age"] == band else 1 if e["age"] is None else 2,
                    hashlib.sha1(f"{greek.fold(m.name)}|{n}".encode("utf-8")).hexdigest())

        mine.sort(key=rank)
        free = [n for n in mine if n not in taken]
        out[m.id] = (free or mine)[0]  # more people than voices of a gender: share (only then)
        taken.add(out[m.id])
    return out


def style(m: Member, script_lang: str) -> str:
    """How a member speaks, for an engine that takes a described style (Gemini)."""
    who = m.name + (f", {m.age}," if m.age else "")
    what = m.manner or ROLE_WORDS.get(m.role, "")
    return (f"A {LANG_NAMES.get(script_lang, 'Turkish')}-language podcast for learners of Greek. Greek is spoken as native "
            f"Modern Greek, Turkish as natural Istanbul Turkish, English as natural English. {who} {ROLE_WORDS.get(m.role, '')}: "
            f"{what}. Natural, lively, relaxed pace, warm; talking, never reading aloud.")
