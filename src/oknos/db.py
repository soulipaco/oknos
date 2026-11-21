"""SQLite access: connection, migrations and the Greek round-trip check."""

from __future__ import annotations

import sqlite3
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Callable

from oknos import paths

# Covers accents, final sigma, diaeresis with accent and an em dash.
GREEK_SAMPLE = unicodedata.normalize("NFC", "Καλημέρα! Ένας καφές, παρακαλώ — ς ΐ ΰ")


_clock: Callable[[], datetime] | None = None


def set_clock(clock: Callable[[], datetime] | None) -> None:
    """Replace the clock (simulations and tests). None restores the real one."""
    global _clock
    _clock = clock


def current() -> datetime:
    return (_clock() if _clock else datetime.now()).astimezone()


def now() -> str:
    """Local time with offset, so "today" means the learner's today."""
    return current().isoformat(timespec="seconds")


def today() -> date:
    return current().date()


def connect(path: Path | None = None) -> sqlite3.Connection:
    path = path or paths.db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    if is_new:
        conn.execute("PRAGMA encoding = 'UTF-8'")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def schema_version(conn: sqlite3.Connection) -> int:
    has_meta = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='meta'"
    ).fetchone()
    if not has_meta:
        return 0
    row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    return int(row["value"]) if row else 0


def migrate(conn: sqlite3.Connection) -> int:
    """Apply numbered migrations (0001_*.sql, 0002_*.sql, ...) newer than the DB."""
    current = schema_version(conn)
    for file in sorted(paths.MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql")):
        number = int(file.name[:4])
        if number <= current:
            continue
        sql = file.read_text(encoding="utf-8")
        conn.executescript(
            "BEGIN;\n"
            + sql
            + f"\nINSERT OR REPLACE INTO meta(key, value) VALUES ('schema_version', '{number}');"
            + "\nCOMMIT;"
        )
        current = number
    return current


def open_db() -> sqlite3.Connection:
    """Connect and make sure the schema is current."""
    conn = connect()
    migrate(conn)
    return conn


def greek_roundtrip(conn: sqlite3.Connection) -> tuple[bool, str]:
    """Write a Greek test string into the database, read it back, compare."""
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES ('health_greek', ?)",
            (GREEK_SAMPLE,),
        )
    row = conn.execute("SELECT value FROM meta WHERE key='health_greek'").fetchone()
    value = row["value"] if row else ""
    return value == GREEK_SAMPLE, value
