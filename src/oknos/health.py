"""Install checks shared by GET /health and `oknos health`."""

from __future__ import annotations

import os
import platform
import subprocess

from oknos import __version__, db, paths
from oknos.packs import Catalog


def report(catalog: Catalog) -> dict:
    """Database, Greek round trip and content. Safe to call repeatedly."""
    out: dict = {
        "app": "oknos",
        "version": __version__,
        "pid": os.getpid(),
        "learner_dir": str(paths.learner_dir()),
        "python": platform.python_version(),
    }
    try:
        conn = db.open_db()
        try:
            out["schema_version"] = db.schema_version(conn)
            ok, value = db.greek_roundtrip(conn)
            out["greek_roundtrip"] = ok
            out["greek_sample"] = value
        finally:
            conn.close()
        out["database"] = True
    except Exception as e:  # report, never crash the health check
        out["database"] = False
        out["database_error"] = f"{type(e).__name__}: {e}"
        out["greek_roundtrip"] = False
    out["packs"] = len(catalog.packs)
    out["items"] = len(catalog.items)
    out["content_problems"] = catalog.problems
    out["ok"] = bool(out["database"] and out["greek_roundtrip"] and out["items"] > 0)
    return out


def greek_voice() -> dict:
    """Is a Greek system voice installed? Read-only; the browser uses it for the speaker button."""
    system = platform.system()
    try:
        if system == "Windows":
            import winreg

            names = []
            for key_path in (
                r"SOFTWARE\Microsoft\Speech_OneCore\Voices\Tokens",
                r"SOFTWARE\Microsoft\Speech\Voices\Tokens",
            ):
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
                except OSError:
                    continue
                i = 0
                while True:
                    try:
                        sub = winreg.EnumKey(key, i)
                    except OSError:
                        break
                    i += 1
                    if "elGR" in sub or "el-GR" in sub:
                        names.append(sub)
            return {"found": bool(names), "voices": sorted(set(names))}
        if system == "Darwin":
            listing = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, encoding="utf-8", timeout=10)
            voices = [line.split()[0] for line in listing.stdout.splitlines() if "el_GR" in line]
            return {"found": bool(voices), "voices": voices}
    except Exception as e:
        return {"found": None, "voices": [], "error": str(e)}
    return {"found": None, "voices": []}  # Linux: browser voices vary, cannot tell from here
