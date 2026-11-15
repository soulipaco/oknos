"""Desktop launcher per operating system (docs/SPEC.md §8).

The launcher runs this checkout's virtual-environment interpreter directly
(`python -m greek_coach start`), so it does not depend on where uv lives.
Only the Windows branch has been tested so far; macOS and Linux follow the spec.
"""

from __future__ import annotations

import os
import platform
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from greek_coach import paths

NAME = "Greek Coach"


def _venv() -> Path:
    return Path(sys.prefix)


def _windows() -> list[Path]:
    target = _venv() / "Scripts" / "pythonw.exe"
    if not target.exists():
        raise RuntimeError(f"{target} does not exist; run `uv sync` in {paths.REPO_ROOT} first")
    script = (
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8;"
        "$desktop = [Environment]::GetFolderPath('Desktop');"
        f"$lnk = Join-Path $desktop '{NAME}.lnk';"
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk);"
        "$s.TargetPath = $env:GC_TARGET;"
        "$s.Arguments = '-m greek_coach start';"
        "$s.WorkingDirectory = $env:GC_WORKDIR;"
        f"$s.Description = '{NAME}: study Greek';"
        "$s.Save();"
        "Write-Output $lnk"
    )
    env = dict(os.environ, GC_TARGET=str(target), GC_WORKDIR=str(paths.REPO_ROOT))
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True, env=env, timeout=60,
    )
    out = result.stdout.decode("utf-8", errors="replace").strip()
    if result.returncode != 0 or not out:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip() or "PowerShell failed")
    link = Path(out.splitlines()[-1].lstrip("﻿"))
    if not link.exists():
        raise RuntimeError(f"the shortcut was not found at {link} after creating it")
    return [link]


def _macos() -> list[Path]:
    python = _venv() / "bin" / "python"
    desktop = Path.home() / "Desktop"
    desktop.mkdir(exist_ok=True)
    link = desktop / f"{NAME}.command"
    link.write_text(
        "#!/bin/bash\n"
        f"cd {shlex.quote(str(paths.REPO_ROOT))} && exec {shlex.quote(str(python))} -m greek_coach start\n",
        encoding="utf-8",
    )
    link.chmod(0o755)
    return [link]


def _linux_desktop_dir() -> Path | None:
    if shutil.which("xdg-user-dir"):
        out = subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True, text=True, encoding="utf-8").stdout.strip()
        if out and Path(out).is_dir() and Path(out) != Path.home():
            return Path(out)
    fallback = Path.home() / "Desktop"
    return fallback if fallback.is_dir() else None


def _linux() -> list[Path]:
    python = _venv() / "bin" / "python"
    entry = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={NAME}\n"
        "Comment=Study Greek\n"
        f'Exec="{python}" -m greek_coach start\n'
        f"Path={paths.REPO_ROOT}\n"
        "Terminal=false\n"
        "Categories=Education;\n"
    )
    targets = [Path.home() / ".local" / "share" / "applications" / "greek-coach.desktop"]
    desktop = _linux_desktop_dir()
    if desktop:
        targets.append(desktop / "greek-coach.desktop")
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(entry, encoding="utf-8")
        target.chmod(0o755)
        if shutil.which("gio"):
            subprocess.run(["gio", "set", str(target), "metadata::trusted", "true"], capture_output=True)
    return targets


def create() -> list[Path]:
    system = platform.system()
    if system == "Windows":
        return _windows()
    if system == "Darwin":
        return _macos()
    return _linux()
