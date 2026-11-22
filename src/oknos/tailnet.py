"""Tailscale Serve, read only: which local port it passes the learner's devices to.

The learner may open the app from their phone through Tailscale Serve (docs/HOSTING.md). Serve
points at one port; if the app starts on another one, the phone silently stops reaching it. This
module only reads `tailscale serve status --json`, so `oknos start` and `oknos health` can say so
and give the one command that fixes it. It never changes Tailscale's settings, and everything
works the same when Tailscale is not installed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

STATUS_TIMEOUT_S = 5
LOCAL_HOSTS = {"127.0.0.1", "localhost", "[::1]", ""}


def _exe() -> str | None:
    found = shutil.which("tailscale")
    if found:
        return found
    if os.name == "nt":
        default = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Tailscale" / "tailscale.exe"
        if default.exists():
            return str(default)
    return None


def serve_status() -> dict | None:
    """Serve's settings as Tailscale prints them, or None if Tailscale is missing or not running."""
    exe = _exe()
    if not exe:
        return None
    extra = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    try:
        done = subprocess.run([exe, "serve", "status", "--json"], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=STATUS_TIMEOUT_S, **extra)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    try:
        status = json.loads(done.stdout.strip() or "{}")
    except ValueError:
        return None
    return status if isinstance(status, dict) else None


def _local_port(target: object) -> int | None:
    """8643 from "http://127.0.0.1:8643", "127.0.0.1:8643", "localhost:8643" or "8643"."""
    if not isinstance(target, str) or not target.strip():
        return None
    rest = target.strip().split("://", 1)[-1].split("/", 1)[0]
    host, _, port = rest.rpartition(":")
    if host.lower() not in LOCAL_HOSTS or not port.isdigit():
        return None
    return int(port)


def served_ports(status: dict) -> list[int]:
    """The local ports Serve passes to (web proxies and plain TCP forwards)."""
    ports: set[int] = set()
    for site in (status.get("Web") or {}).values():
        for handler in ((site or {}).get("Handlers") or {}).values():
            if isinstance(handler, dict) and (port := _local_port(handler.get("Proxy"))):
                ports.add(port)
    for listener in (status.get("TCP") or {}).values():
        if isinstance(listener, dict) and (port := _local_port(listener.get("TCPForward"))):
            ports.add(port)
    return sorted(ports)


def funnel_on(status: dict) -> bool:
    return any(bool(v) for v in (status.get("AllowFunnel") or {}).values())


def notes(port: int | None, status: dict | None) -> dict:
    """What `start` and `health` say about Tailscale, for the app's port (None: not running)."""
    if status is None:
        return {"installed": False, "serve_ports": [], "funnel": False, "problems": []}
    ports = served_ports(status)
    problems: list[str] = []
    if funnel_on(status):
        target = port or (ports[0] if ports else "<port>")
        problems.append(
            "Tailscale Funnel is on, so the app may be open to the whole internet. Turn it off with: "
            f"tailscale serve reset   (then point Serve at the app again: tailscale serve --bg {target})")
    if port and ports and port not in ports:
        where = ", ".join(str(p) for p in ports)
        problems.append(
            f"Tailscale Serve passes your phone to port {where}, but Oknos is on port {port} now, "
            f"so the phone cannot reach it. To fix it, run: tailscale serve --bg {port}")
    return {"installed": True, "serve_ports": ports, "funnel": funnel_on(status), "problems": problems}


def check(port: int | None) -> dict:
    return notes(port, serve_status())
