"""Where things live on disk.

The app always runs from a checkout of the repository, so paths are resolved
relative to the repo root. Tests point the learner folder elsewhere with the
GREEK_COACH_LEARNER_DIR environment variable.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = REPO_ROOT / "web"
CONTENT_DIR = REPO_ROOT / "content"
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"

DEFAULT_PORT = 8642
HOST = "127.0.0.1"


def learner_dir() -> Path:
    override = os.environ.get("GREEK_COACH_LEARNER_DIR")
    path = Path(override) if override else REPO_ROOT / "learner"
    return path.resolve()


def db_path() -> Path:
    return learner_dir() / "greek-coach.db"


def profile_path() -> Path:
    return learner_dir() / "profile.json"


def port_file() -> Path:
    return learner_dir() / ".port"


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
