"""Where things live on disk.

The app always runs from a checkout of the repository, so paths are resolved
relative to the repo root. Tests point the learner folder elsewhere with the
OKNOS_LEARNER_DIR environment variable.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = REPO_ROOT / ".cache" / "oknos"
WEB_DIR = REPO_ROOT / "web"
CONTENT_DIR = REPO_ROOT / "content"
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"

DEFAULT_PORT = 8642
HOST = "127.0.0.1"


# The app was called Greek Coach until 2026-11-21. Old environment variables, the old database
# name and the old cache folder still work; the files are renamed the first time they are used.
OLD_ENV_PREFIX = "GREEK_COACH_"
OLD_DB_NAME = "greek-coach.db"


def env(name: str, default: str | None = None) -> str | None:
    """OKNOS_<name>, or the old GREEK_COACH_<name>."""
    value = os.environ.get(f"OKNOS_{name}")
    if value is None:
        value = os.environ.get(OLD_ENV_PREFIX + name)
    return default if value is None else value


def _rename_old(old: Path, new: Path) -> None:
    if old.exists() and not new.exists():
        try:
            old.rename(new)
        except OSError:
            pass  # in use or read-only: the old one is read where it is (see db_path)


_rename_old(REPO_ROOT / ".cache" / "greek-coach", CACHE_DIR)


def learner_dir() -> Path:
    override = env("LEARNER_DIR")
    path = Path(override) if override else REPO_ROOT / "learner"
    return path.resolve()


def db_path() -> Path:
    new, old = learner_dir() / "oknos.db", learner_dir() / OLD_DB_NAME
    if old.exists() and not new.exists():
        for suffix in ("-wal", "-shm"):  # SQLite's side files go with it, or they are lost
            _rename_old(old.with_name(old.name + suffix), new.with_name(new.name + suffix))
        _rename_old(old, new)
        if not new.exists():
            return old
    return new


def profile_path() -> Path:
    return learner_dir() / "profile.json"


def port_file() -> Path:
    """The port of the server running now (removed when it stops)."""
    return learner_dir() / ".port"


def last_port_file() -> Path:
    """The port the app last ran on (kept), so the next start takes it again (Tailscale Serve and
    the phone's bookmark point at one port)."""
    return learner_dir() / ".last-port"


def audio_cache_dir() -> Path:
    """Listening audio the coach pre-generated for content items (derived content, never tracked)."""
    return learner_dir() / "audio"


def log_dir() -> Path:
    return learner_dir() / "logs"


def content_roots() -> list[tuple[str, Path]]:
    """Pack roots in load order, each with the visibility its packs must declare."""
    return [
        ("open", CONTENT_DIR / "open"),
        ("private", CONTENT_DIR / "private"),
        ("generated", learner_dir() / "generated"),
    ]


def ensure_learner_dir() -> Path:
    path = learner_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path
