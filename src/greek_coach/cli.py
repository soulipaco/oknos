"""Command line: greek-coach start | stop | health | validate | import | schema | shortcut."""

from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

from greek_coach import __version__, db, health, paths

START_TIMEOUT_S = 60
LOG_MAX_BYTES = 1_000_000


def _utf8_console() -> None:
    # Windows consoles default to a legacy code page; Greek must never crash a print.
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


def _url(port: int) -> str:
    return f"http://{paths.HOST}:{port}/"


def fetch_health(port: int, timeout: float = 2.0) -> dict | None:
    try:
        with urllib.request.urlopen(f"{_url(port)}health", timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def running_port() -> int | None:
    """The port of the server serving *this* learner folder, if one is running."""
    try:
        port = int(paths.port_file().read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        return None
    info = fetch_health(port)
    if info and info.get("app") == "greek-coach" and info.get("learner_dir") == str(paths.learner_dir()):
        return port
    return None


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((paths.HOST, port))
        except OSError:
            return False
    return True


def choose_port(preferred: int = paths.DEFAULT_PORT) -> int:
    for port in range(preferred, preferred + 20):
        if _port_is_free(port):
            return port
    raise SystemExit(f"No free port between {preferred} and {preferred + 19}.")


def _open_browser(port: int) -> None:
    webbrowser.open(_url(port))


def serve_foreground(port: int | None, open_browser: bool) -> int:
    import uvicorn

    from greek_coach.server import create_app

    paths.ensure_learner_dir()
    port = port or choose_port()
    app = create_app()
    paths.port_file().write_text(str(port), encoding="utf-8")
    server = uvicorn.Server(uvicorn.Config(app, host=paths.HOST, port=port, log_level="info"))

    if open_browser:
        def wait_then_open():
            for _ in range(200):
                if fetch_health(port, timeout=0.5):
                    _open_browser(port)
                    return
                time.sleep(0.1)

        threading.Thread(target=wait_then_open, daemon=True).start()

    print(f"Greek Coach is running at {_url(port)}", flush=True)
    try:
        server.run()
    finally:
        try:
            if paths.port_file().read_text(encoding="utf-8").strip() == str(port):
                paths.port_file().unlink()
        except OSError:
            pass
    return 0


def _server_python() -> str:
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe" and (exe.parent / "python.exe").exists():
        return str(exe.parent / "python.exe")
    return str(exe)


def spawn_background(port: int | None) -> subprocess.Popen:
    """Start the server as a detached background process that outlives this one."""
    log_dir = paths.log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "server.log"
    if log_file.exists() and log_file.stat().st_size > LOG_MAX_BYTES:
        log_file.unlink()
    cmd = [_server_python(), "-m", "greek_coach", "start", "--foreground", "--no-browser"]
    if port:
        cmd += ["--port", str(port)]
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    log = open(log_file, "a", encoding="utf-8")
    log.write(f"\n--- {db.now()} starting Greek Coach {__version__} ---\n")
    log.flush()
    common = dict(cwd=str(paths.REPO_ROOT), env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
    try:
        if os.name == "nt":
            flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
            try:
                # Leave the parent's job object, so closing an agent's shell does not kill the app.
                return subprocess.Popen(cmd, creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB, **common)
            except OSError:
                return subprocess.Popen(cmd, creationflags=flags, **common)
        return subprocess.Popen(cmd, start_new_session=True, **common)
    finally:
        log.close()


def _tail(path: Path, lines: int = 15) -> str:
    try:
        return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])
    except OSError:
        return ""


def cmd_start(args) -> int:
    if args.foreground:
        return serve_foreground(args.port, open_browser=not args.no_browser)
    port = running_port()
    if port:
        print(f"Greek Coach is already running at {_url(port)}")
    else:
        proc = spawn_background(args.port)
        deadline = time.monotonic() + START_TIMEOUT_S
        while time.monotonic() < deadline:
            port = running_port()
            if port:
                break
            if proc.poll() is not None:
                break
            time.sleep(0.25)
        if not port:
            print("Greek Coach did not start. The last lines of its log were:", file=sys.stderr)
            print(_tail(paths.log_dir() / "server.log"), file=sys.stderr)
            return 1
        print(f"Greek Coach is running at {_url(port)}")
    if not args.no_browser:
        _open_browser(port)
    return 0


def cmd_stop(args) -> int:
    port = running_port()
    if not port:
        print("Greek Coach is not running.")
        return 0
    info = fetch_health(port) or {}
    pid = info.get("pid")
    if not isinstance(pid, int):
        print("Could not find the running app's process.", file=sys.stderr)
        return 1
    os.kill(pid, signal.SIGTERM)
    for _ in range(40):
        if not fetch_health(port, timeout=0.5):
            break
        time.sleep(0.25)
    else:
        print("Greek Coach did not stop.", file=sys.stderr)
        return 1
    try:
        paths.port_file().unlink()
    except OSError:
        pass
    print("Greek Coach stopped.")
    return 0


def cmd_health(args) -> int:
    from greek_coach import packs

    catalog = packs.load_all()
    rep = health.report(catalog)
    voice = health.greek_voice()
    port = running_port()
    server: dict = {"running": bool(port)}
    if port:
        info = fetch_health(port) or {}
        server.update(
            url=_url(port),
            ok=bool(info.get("ok")),
            greek_over_http=info.get("greek_sample") == db.GREEK_SAMPLE,
        )
    ok = rep["ok"] and (not port or (server["ok"] and server["greek_over_http"])) and (port or not args.server)

    if args.json:
        print(json.dumps({"ok": ok, "install": rep, "server": server, "greek_voice": voice}, ensure_ascii=False, indent=2))
        return 0 if ok else 1

    def line(good: bool | None, text: str) -> None:
        mark = {True: " ok ", False: "FAIL", None: " -- "}[good]
        print(f"  {mark}  {text}")

    print("Greek Coach health check")
    line(True, f"Python {rep['python']}, Greek Coach {rep['version']}")
    if rep["database"]:
        line(True, f"Database ready (schema {rep['schema_version']}) in {paths.db_path()}")
    else:
        line(False, f"Database could not be opened: {rep.get('database_error')}")
    line(rep["greek_roundtrip"], f"Greek text survives the database: {rep.get('greek_sample', '')}")
    line(rep["items"] > 0, f"Content: {rep['packs']} pack(s), {rep['items']} exercise(s)")
    for problem in rep["content_problems"]:
        line(None, f"Content note: {problem}")
    if port:
        line(server["ok"], f"App running at {server['url']}")
        line(server["greek_over_http"], "Greek text survives the web layer too")
    elif args.server:
        line(False, "App is not running (start it with: uv run greek-coach start)")
    else:
        line(None, "App is not running right now (that is fine; start it with: uv run greek-coach start)")
    if voice["found"] is True:
        line(True, f"Greek voice installed: {', '.join(voice['voices'])}")
    elif voice["found"] is False:
        line(None, "No Greek voice installed; the speaker button stays hidden until one is added")
    else:
        line(None, "Greek voice: cannot tell on this system; the app hides the speaker button if there is none")
    print("All good." if ok else "Something is not right; see the FAIL lines above.")
    return 0 if ok else 1


def cmd_validate(args) -> int:
    from greek_coach import packs

    target = Path(args.path).resolve()
    if (target / "pack.json").exists():
        pack_dirs = [target]
    elif target.is_dir():
        pack_dirs = sorted(p for p in target.iterdir() if (p / "pack.json").exists())
    else:
        pack_dirs = []
    if not pack_dirs:
        print(f"No pack found at {target} (a pack is a folder with a pack.json).")
        return 1
    expected = None
    for visibility, root in paths.content_roots():
        if root.resolve() in target.parents or root.resolve() == target:
            expected = visibility
    bad = False
    for pack_dir in pack_dirs:
        pack, problems, later = packs.load_pack(pack_dir, expected)
        if pack:
            print(f"{pack.id}: {len(pack.items)} item(s) loaded" + (f", {later} of a type built in a later phase" if later else ""))
        for problem in problems:
            print(f"  problem: {problem}")
        bad = bad or bool(problems) or pack is None
    print("Some problems need fixing." if bad else "Everything is valid.")
    return 1 if bad else 0


def cmd_import(args) -> int:
    from greek_coach import packs
    from greek_coach.importer import core, mapping as mapping_mod

    mapping_path = Path(args.mapping)
    if not mapping_path.is_file():
        builtin = Path(__file__).parent / "importer" / "mappings" / f"{args.mapping}.json"
        if builtin.is_file():
            mapping_path = builtin
        else:
            print(f"There is no mapping file at {args.mapping}.")
            return 1
    try:
        m = mapping_mod.load(mapping_path)
        out, report = core.run(m, Path(args.source), Path(args.out) if args.out else None)
    except core.ImportError_ as e:
        print(f"The import stopped: {e}")
        return 1
    except Exception as e:  # pydantic errors in the mapping, unreadable files
        print(f"The import stopped: {e.__class__.__name__}: {e}")
        return 1
    print(f"Imported into {out}")
    for key, value in report.counts.items():
        print(f"  {key}: {value}")
    pack, problems, _ = packs.load_pack(out)
    if problems:
        print(f"The pack has {len(problems)} problem(s); the first ones:")
        for problem in problems[:10]:
            print(f"  - {problem}")
    else:
        print(f"The pack loads cleanly: {len(pack.items) if pack else 0} items.")
    print(f"Read {out / 'IMPORT_REPORT.md'} for the details. If the app is running, it picks this up on the next restart or content reload.")
    return 0 if not problems else 2


def cmd_schema(args) -> int:
    from greek_coach import packs

    out = paths.REPO_ROOT / "schemas"
    out.mkdir(exist_ok=True)
    for name, schema in packs.json_schemas().items():
        (out / f"{name}.schema.json").write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote schemas/{name}.schema.json")
    return 0


def cmd_shortcut(args) -> int:
    from greek_coach import shortcut

    try:
        created = shortcut.create()
    except Exception as e:
        print(f"Could not create the shortcut: {e}", file=sys.stderr)
        return 1
    for path in created:
        print(f"Created {path}")
    return 0 if created else 1


def main(argv: list[str] | None = None) -> int:
    _utf8_console()
    parser = argparse.ArgumentParser(prog="greek-coach", description="Greek Coach, a local Greek learning app.")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("start", help="start the app (in the background) and open the browser")
    p.add_argument("--foreground", action="store_true", help="run the server in this window (for development)")
    p.add_argument("--no-browser", action="store_true", help="do not open the browser")
    p.add_argument("--port", type=int, default=None, help=f"port to use (default {paths.DEFAULT_PORT} or the next free one)")
    p.set_defaults(func=cmd_start)

    p = sub.add_parser("stop", help="stop the running app")
    p.set_defaults(func=cmd_stop)

    p = sub.add_parser("health", help="check that the install works")
    p.add_argument("--server", action="store_true", help="also require the app to be running")
    p.add_argument("--json", action="store_true", help="print the result as JSON")
    p.set_defaults(func=cmd_health)

    p = sub.add_parser("validate", help="check a content pack and explain any problems")
    p.add_argument("path")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("import", help="import someone's own material as a private content pack")
    p.add_argument("mapping", help="a mapping file, or the name of a built-in one (greek-helper)")
    p.add_argument("--source", required=True, help="the folder that holds the material")
    p.add_argument("--out", default=None, help="output folder (default content/private/<pack id>)")
    p.set_defaults(func=cmd_import)

    p = sub.add_parser("schema", help="write the content pack JSON Schemas to schemas/")
    p.set_defaults(func=cmd_schema)

    p = sub.add_parser("shortcut", help="put a Greek Coach shortcut on the desktop")
    p.set_defaults(func=cmd_shortcut)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
