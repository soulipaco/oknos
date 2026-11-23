"""The three films of the Oknos myth in the app (docs/brand/animations/).

The films stay where they are made, in docs/brand/animations/, and the server serves that folder
at /films/ (one source of truth, no copies in web/). The app shows them on the films page (?films)
and plays film 1 once as a welcome the first time a new learner opens the app.

Voice: voice-local/ (the maintainer's own Azure clips, not tracked) is played when it is there,
else the tracked Google clips in voice/; without either the films play silently.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from oknos import paths

FILMS = ("1-oknos-and-the-donkey", "2-oknos-and-his-wife", "3-the-dream")
WELCOME = FILMS[0]
PROFILE_KEY = "welcome_film_seen"  # the date the welcome film ended or was skipped

# What /films/ may serve: the pages, the player, and the pictures and sounds in their folders.
TOP_FILES = {*(f"{f}.html" for f in FILMS), "film.js", "anim.css"}
FOLDERS = {"frames": {".webp"}, "voice": {".mp3"}, "voice-local": {".mp3"}, "ambience": {".mp3"}}
MEDIA_TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
               ".css": "text/css; charset=utf-8", ".webp": "image/webp", ".mp3": "audio/mpeg"}


def films_dir() -> Path:
    return paths.FILMS_DIR


def file_for(name: str) -> Path | None:
    """The file behind /films/<name>, or None if it is not one the app serves."""
    parts = name.split("/")
    if len(parts) == 1 and parts[0] in TOP_FILES:
        pass
    elif len(parts) == 2 and parts[0] in FOLDERS and Path(parts[1]).suffix in FOLDERS[parts[0]]:
        pass
    else:
        return None
    base = films_dir().resolve()
    target = (base / name).resolve()
    if base not in target.parents or not target.is_file():
        return None
    return target


def available(film: str) -> bool:
    """A film can play when its page, the player and its first picture are there."""
    d = films_dir()
    n = film.split("-", 1)[0]
    return all((d / p).is_file() for p in (f"{film}.html", "film.js", "anim.css", f"frames/f{n}-01.webp"))


def voice_folder() -> str | None:
    """Which set of clips to play: voice-local/ when it is there, else voice/, else none."""
    d = films_dir()
    for folder in ("voice-local", "voice"):
        if (d / folder / "f1-01.mp3").is_file():
            return folder
    return None


def listing() -> dict:
    return {
        "films": [{"n": i + 1, "id": f, "available": available(f),
                   "poster": f"/films/frames/f{i + 1}-01.webp"} for i, f in enumerate(FILMS)],
        "voice": voice_folder(),
    }


def is_new_learner(conn: sqlite3.Connection) -> bool:
    """Nothing answered and no chapter opened yet: the app is being opened for the first time."""
    if conn.execute("SELECT 1 FROM attempts LIMIT 1").fetchone():
        return False
    return conn.execute("SELECT 1 FROM chapter_reads LIMIT 1").fetchone() is None


def welcome_due(conn: sqlite3.Connection, profile: dict) -> bool:
    """Show the welcome film? Only once, only to a new learner, and only if the film is there."""
    return not profile.get(PROFILE_KEY) and available(WELCOME) and is_new_learner(conn)
