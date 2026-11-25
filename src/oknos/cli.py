"""Command line: oknos start | stop | health | report | validate | reload | import | raw | schema |
shortcut | transcribe | run | schedule."""

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
from datetime import date, timedelta
from pathlib import Path

from oknos import __version__, db, health, paths

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
    if info and info.get("app") in ("oknos", "greek-coach") and info.get("learner_dir") == str(paths.learner_dir()):
        return port
    return None


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((paths.HOST, port))
        except OSError:
            return False
    return True


def last_port() -> int | None:
    """The port recorded at the last start; a server that was not stopped (the laptop restarted)
    left only its .port file, which says the same."""
    for path in (paths.last_port_file(), paths.port_file()):
        try:
            port = int(path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            continue
        if 0 < port < 65536:
            return port
    return None


def remember_port(port: int) -> None:
    try:
        paths.last_port_file().write_text(str(port), encoding="utf-8")
    except OSError:
        pass


def choose_port() -> int:
    """The port the app last ran on if it is free, else the first free one from 8642."""
    first = paths.DEFAULT_PORT
    candidates = list(range(first, first + 20))
    previous = last_port()
    if previous:
        candidates = [previous] + [p for p in candidates if p != previous]
    for port in candidates:
        if _port_is_free(port):
            return port
    raise SystemExit(f"No free port between {first} and {first + 19}.")


def _tailscale_notes(port: int | None) -> dict:
    from oknos import tailnet

    return tailnet.check(port)


def _open_browser(port: int) -> None:
    webbrowser.open(_url(port))


def serve_foreground(port: int | None, open_browser: bool) -> int:
    import uvicorn

    from oknos.server import create_app

    paths.ensure_learner_dir()
    port = port or choose_port()
    app = create_app()
    paths.port_file().write_text(str(port), encoding="utf-8")
    remember_port(port)
    server = uvicorn.Server(uvicorn.Config(app, host=paths.HOST, port=port, log_level="info"))

    if open_browser:
        def wait_then_open():
            for _ in range(200):
                if fetch_health(port, timeout=0.5):
                    _open_browser(port)
                    return
                time.sleep(0.1)

        threading.Thread(target=wait_then_open, daemon=True).start()

    print(f"Oknos is running at {_url(port)}", flush=True)
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
    cmd = [_server_python(), "-m", "oknos", "start", "--foreground", "--no-browser"]
    if port:
        cmd += ["--port", str(port)]
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    log = open(log_file, "a", encoding="utf-8")
    log.write(f"\n--- {db.now()} starting Oknos {__version__} ---\n")
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
        print(f"Oknos is already running at {_url(port)}")
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
            print("Oknos did not start. The last lines of its log were:", file=sys.stderr)
            print(_tail(paths.log_dir() / "server.log"), file=sys.stderr)
            return 1
        print(f"Oknos is running at {_url(port)}")
    for problem in _tailscale_notes(port)["problems"]:
        print(f"Note: {problem}")
    if not args.no_browser:
        _open_browser(port)
    return 0


def cmd_stop(args) -> int:
    port = running_port()
    if not port:
        print("Oknos is not running.")
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
        print("Oknos did not stop.", file=sys.stderr)
        return 1
    remember_port(port)  # a server started by an older version did not record it
    try:
        paths.port_file().unlink()
    except OSError:
        pass
    print("Oknos stopped.")
    return 0


def cmd_health(args) -> int:
    from oknos import packs

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
    tailscale = _tailscale_notes(port)
    ok = (rep["ok"] and (not port or (server["ok"] and server["greek_over_http"])) and (port or not args.server)
          and not tailscale["problems"])

    if args.json:
        print(json.dumps({"ok": ok, "install": rep, "server": server, "greek_voice": voice, "tailscale": tailscale},
                         ensure_ascii=False, indent=2))
        return 0 if ok else 1

    def line(good: bool | None, text: str) -> None:
        mark = {True: " ok ", False: "FAIL", None: " -- "}[good]
        print(f"  {mark}  {text}")

    print("Oknos health check")
    line(True, f"Python {rep['python']}, Oknos {rep['version']}")
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
        line(False, "App is not running (start it with: uv run oknos start)")
    else:
        line(None, "App is not running right now (that is fine; start it with: uv run oknos start)")
    for problem in tailscale["problems"]:
        line(False, problem)
    if port and tailscale["serve_ports"] and not tailscale["problems"]:
        line(True, f"Tailscale Serve passes your devices to port {port}, the app's port")
    if voice["found"] is True:
        line(True, f"Greek voice installed: {', '.join(voice['voices'])}")
    elif voice["found"] is False:
        line(None, "No Greek voice installed; the speaker button stays hidden until one is added")
    else:
        line(None, "Greek voice: cannot tell on this system; the app hides the speaker button if there is none")
    print("All good." if ok else "Something is not right; see the FAIL lines above.")
    return 0 if ok else 1


def _is_learner_folder(path: Path) -> bool:
    return not (path / "pack.json").exists() and any(
        (path / name).exists() for name in ("profile.json", "generated", "coach", "oknos.db", paths.OLD_DB_NAME))


def cmd_validate(args) -> int:
    from oknos import coachfiles, lint, packs, wordscan

    target = Path(args.path).resolve()
    learner_files: list[str] | None = None
    expected: str | None = None
    if target.is_dir() and _is_learner_folder(target):
        learner_files = coachfiles.validate_learner(target)
        target = target / "generated"
        expected = "generated"
    else:
        for visibility, root in paths.content_roots():
            if root.resolve() in target.parents or root.resolve() == target:
                expected = visibility
    if (target / "pack.json").exists():
        pack_dirs = [target]
    elif target.is_dir():
        pack_dirs = sorted(p for p in target.iterdir() if (p / "pack.json").exists())
    else:
        pack_dirs = []
    if not pack_dirs and learner_files is None:
        print(f"No pack found at {target} (a pack is a folder with a pack.json).")
        return 1
    bad = False
    known = None
    full_catalog = None
    for pack_dir in pack_dirs:
        pack, problems, later = packs.load_pack(pack_dir, expected)
        greek_problems, notes = lint.lint_pack(pack_dir)
        chapter_greek, chapter_notes = lint.lint_chapter_files(pack_dir)
        problems = problems + greek_problems + chapter_greek
        notes += chapter_notes
        if pack:
            tag_problems, tag_notes = lint.lint_tags(pack)
            problems += tag_problems
            notes += tag_notes
            notes += lint.hidden_questions(pack)
            if pack.chapters:
                full = packs.load_all()
                if pack.id not in {p.id for p in full.packs}:  # a pack outside the content folders
                    full.packs.append(pack)
                    full.items.update({f"{pack.id}/{i}": (pack, it) for i, it in pack.items.items()})
                    full.chapters.update({(c.curriculum, c.stage): (pack, c) for c in pack.chapters.values()})
                ch_problems, ch_notes = lint.chapter_checks(pack, full)
                problems += ch_problems
                notes += ch_notes
            if not args.quick:
                if full_catalog is None:
                    full_catalog = packs.load_all()
                word_problems, word_notes = wordscan.lint_pack(pack, full_catalog)
                problems += word_problems
                notes = word_notes + notes
            print(f"{pack.id}: {len(pack.items)} item(s) loaded" + (f", {later} of a type built in a later phase" if later else "")
                  + (f", {len(pack.chapters)} chapter(s)" if pack.chapters else ""))
            if pack.manifest.visibility == "generated" and not args.quick:
                if known is None:
                    known = lint.known_words(packs.load_all(), exclude_pack=pack.id)
                unfamiliar = lint.unfamiliar_words(pack, known)
                if unfamiliar:
                    notes.append("words no other content uses (check spelling and level): "
                                 + ", ".join(unfamiliar[:40])
                                 + (f" and {len(unfamiliar) - 40} more" if len(unfamiliar) > 40 else ""))
        for problem in problems:
            print(f"  problem: {problem}")
        for note in notes[: args.notes]:
            print(f"  note: {note}")
        if len(notes) > args.notes:
            print(f"  ({len(notes) - args.notes} more notes; use --notes {len(notes)} to see them)")
        bad = bad or bool(problems) or pack is None
    if target == (paths.CONTENT_DIR / "open").resolve():
        for note in shipped_voice_notes():
            print(f"open voice: note: {note}")
    if learner_files is not None:
        print("coach files: " + ("all valid" if not learner_files else f"{len(learner_files)} problem(s)"))
        for problem in learner_files:
            print(f"  problem: {problem}")
        bad = bad or bool(learner_files)
    print("Some problems need fixing." if bad else "Everything is valid.")
    return 1 if bad else 0


def shipped_voice_notes() -> list[str]:
    """Warnings, never failures: a changed open text keeps CI green, and the browser's voice reads
    it until scripts/ship_voice.py makes its clip (docs/VOICE.md)."""
    from oknos import packs, voice

    missing, stale = voice.shipped_gaps(packs.load_all([("open", paths.CONTENT_DIR / "open")]))
    fix = "uv run python scripts/ship_voice.py --secrets <secrets.env>"
    notes = []
    if missing:
        notes.append(f"{len(missing)} open text(s) have no shipped clip, so the browser's voice reads them, "
                     f"e.g. {', '.join(missing[:5])}. To make them (Google key): {fix}")
    if stale:
        notes.append(f"{len(stale)} shipped clip(s) no open text uses any more, e.g. {', '.join(stale[:5])}. "
                     f"To delete them: {fix} --prune")
    return notes


def cmd_words(args) -> int:
    """Tappable words the lookup cannot explain, per pack; --write maps the inflected ones to their
    lemma (from the cached Wiktionary dump) in the pack's glossary.json."""
    from oknos import lookup, packs, wordscan
    from oknos.importer import enrich

    target = Path(args.path).resolve()
    if target.is_dir() and _is_learner_folder(target):
        target = target / "generated"
    if (target / "pack.json").exists():
        pack_dirs = [target]
    elif target.is_dir():
        pack_dirs = sorted(p for p in target.iterdir() if (p / "pack.json").exists())
    else:
        pack_dirs = []
    if not pack_dirs:
        print(f"No pack found at {target} (a pack is a folder with a pack.json).")
        return 1
    forms_index = enrich.load_forms_index()
    if forms_index is None:
        print("The Wiktionary dump is not downloaded (.cache/oknos/), so inflected forms cannot be mapped; "
              "only the counts are shown.")
    main_index = enrich.load_index() if args.json and forms_index else None
    leftovers_all: list[dict] = []
    for pack_dir in pack_dirs:
        catalog = packs.load_all()
        pack = next((p for p in catalog.packs if p.path.resolve() == pack_dir.resolve()), None)
        if pack is None:
            pack, problems, _ = packs.load_pack(pack_dir)
            if pack is None:
                print(f"{pack_dir.name}: could not be loaded: {'; '.join(problems)}")
                continue
            catalog.packs.append(pack)
            catalog.items.update({f"{pack.id}/{i}": (pack, it) for i, it in pack.items.items()})
        index = lookup.Index(wordscan.visible_to(catalog, pack.manifest.visibility))
        gaps = wordscan.scan([pack], index)
        print(f"{pack.id}: {gaps.total} tappable word(s), {len(gaps.unexplained)} find nothing "
              f"({gaps.share:.1%}); {len(gaps.unexplained) - len(gaps.without_reason)} of them left on purpose")
        if forms_index is None:
            continue
        forms, leftovers = wordscan.fill_forms(pack, index, forms_index, main_index)
        print(f"  {len(forms)} are forms of a word the lookup knows" + ("" if args.write else " (use --write to add them)"))
        if args.write and forms:
            new = wordscan.write_forms(pack_dir, forms)
            print(f"  wrote {new} new form(s) to {pack.id}/glossary.json")
        print(f"  {len(leftovers)} still need a meaning: "
              + ", ".join(x["word"] for x in leftovers[:args.show]) + (" …" if len(leftovers) > args.show else ""))
        for x in leftovers:
            x["pack"] = pack.id
        leftovers_all += leftovers
    if args.json:
        Path(args.json).write_text(json.dumps(leftovers_all, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"wrote {len(leftovers_all)} leftover word(s) to {args.json}")
    return 0


def cmd_import(args) -> int:
    from oknos import packs
    from oknos.importer import core, mapping as mapping_mod

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


def cmd_report(args) -> int:
    from oknos import packs, report

    try:
        days = report.parse_days(args.since)
    except ValueError as e:
        print(f"--since: {e}", file=sys.stderr)
        return 2
    paths.ensure_learner_dir()
    conn = db.open_db()
    try:
        catalog = packs.load_all()
        packs.sync_items(conn, catalog)
        data = report.build(conn, catalog, days=days, with_words=args.words)
    finally:
        conn.close()
    port = running_port()
    data["app_url"] = _url(port) if port else None
    print(json.dumps(data, ensure_ascii=False, indent=1 if args.pretty else None))
    return 0


def cmd_raw(args) -> int:
    root = paths.CONTENT_DIR / "private" / args.pack
    raw_file = root / "raw" / "exercises.json"
    if not raw_file.is_file():
        print(f"There is no raw/exercises.json in content/private/{args.pack}.")
        return 1
    entries = json.loads(raw_file.read_text(encoding="utf-8"))
    units = json.loads((root / "units.json").read_text(encoding="utf-8")) if (root / "units.json").is_file() else []
    if args.list_units:
        counts: dict = {}
        for e in entries:
            counts[e.get("unit")] = counts.get(e.get("unit"), 0) + 1
        out = [{"unit": u.get("id"), "title": u.get("title"), "theme": u.get("theme"),
                "raw_entries": counts.get(u.get("id"), 0)} for u in units]
        out.append({"unit": None, "raw_entries": counts.get(None, 0), "note": "not linked to a lesson (extras, answer keys)"})
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0
    lo = hi = None
    if args.pages:
        a, _, b = args.pages.partition("-")
        lo, hi = int(a), int(b or a)
    picked = []
    for e in entries:
        if args.unit and e.get("unit") != args.unit:
            continue
        if args.kind and e.get("kind") != args.kind:
            continue
        if lo is not None and not (lo <= (e.get("page") or -1) <= hi):
            continue
        if args.search and args.search.lower() not in (e.get("text") or "").lower():
            continue
        picked.append({k: e.get(k) for k in ("id", "unit", "page", "doc", "marker", "kind", "instruction", "text", "flags")})
    unit = next((u for u in units if u.get("id") == args.unit), None)
    print(json.dumps({"unit": unit, "count": len(picked), "shown": min(len(picked), args.limit),
                      "entries": picked[: args.limit]}, ensure_ascii=False, indent=1))
    return 0


def cmd_transcribe(args) -> int:
    from oknos import transcribe

    conn = db.open_db()
    try:
        ids = [int(x) for x in args.ids.split(",")] if args.ids else None
        done = transcribe.transcribe(conn, args.model, ids, allow_download=args.download)
    except transcribe.MissingDependency as e:
        print(str(e))
        return 1
    finally:
        conn.close()
    if not done:
        print("No recordings are waiting for a transcript.")
    for d in done:
        print(f"submission {d['submission_id']}: {d['text'] or '(nothing heard)'}")
    return 0


def cmd_voice(args) -> int:
    """Speech made ahead of time (phase 10, docs/VOICE.md): status, build, sample."""
    from oknos import packs, voice

    if args.action == "status":
        st = voice.status(packs.load_all())
        print(f"Order: {' → '.join(st['order']) or '(none: the browser voice only)'}")
        for p in st["providers"]:
            where = f"#{p['position']}" if p["position"] else "  -"
            quota = f", {p['used']:,} of {p['free']:,} free characters this month" if p["free"] else (f", {p['used']:,} characters this month" if p["used"] else "")
            print(f"  {where} {p['name']:7} {'ready' if not p['problem'] else p['problem']}{quota}")
        print(f"Clips: {st['files']:,} made ({', '.join(f'{k} {v:,}' for k, v in st['by_provider'].items()) or 'none'}), "
              f"{st['shipped']:,} shipped with the open content (Google); "
              f"{st['missing']:,} of {st['texts']:,} texts still use the browser voice.")
        return 0
    if args.action == "sample":
        if not args.provider:
            print("Which provider? e.g. oknos voice sample google")
            return 1
        for role in voice.ROLES:
            try:
                path = voice.make_sample(args.provider, role)
                print(f"{args.provider} {role}: {path}")
            except voice.Refused as e:
                print(f"{args.provider} {role}: {e}")
                return 1
        return 0
    # build
    started = time.monotonic()

    def progress(n, total, who):
        if n % 50 == 0 or n == total:
            rate = n / max(time.monotonic() - started, 1e-6)
            left = (total - n) / rate if rate else 0
            print(f"  {n:,}/{total:,} ({who or 'nobody could make it'}), about {left / 60:.0f} min left", flush=True)

    result = voice.build(packs.load_all(), limit=args.limit, wait=args.wait, redo=args.redo, progress=progress)
    made = ", ".join(f"{k} {v:,}" for k, v in result["made"].items()) or "nothing"
    print(f"Made: {made}. Not made (the browser voice stays): {result['failed']:,}. Texts in all: {result['total']:,}.")
    return 0


def cmd_podcast(args) -> int:
    """Podcast lessons (phase 11, docs/PODCASTS.md): list the scripts, check one, render one."""
    from oknos import podcast

    if args.action == "list":
        rows = podcast.scripts()
        if not rows:
            print(f"No scripts yet in {podcast.podcasts_dir()} (the podcast skill writes them).")
        for r in rows:
            if "error" in r:
                print(f"  {r['id']}: {r['error']}")
                continue
            state = (f"rendered, {r['seconds'] / 60:.1f} min" + (", script changed since" if r.get("stale") else "")
                     if r["rendered"] else f"not rendered (about {r['minutes']} min)")
            print(f"  {r['id']:32} {r['kind']:8} {r['lang']}  {state}")
        return 0
    if args.action == "prune":
        gone = podcast.prune()
        print(f"Removed {len(gone['episodes'])} old personal episodes and {gone['clips']} clips no script speaks."
              + (f" Kept the clips: {gone['kept_clips_because']}." if gone.get("kept_clips_because") else ""))
        return 0
    if args.action == "material":
        from oknos import packs, podcast_material, report

        if args.id not in ("daily", "weekly"):
            print("Which kind? oknos podcast material daily (or weekly) [--date YYYY-MM-DD]")
            return 1
        try:
            day = date.fromisoformat(args.date) if args.date else db.today() + timedelta(days=1)
        except ValueError:
            print(f"--date: not a date: {args.date!r} (YYYY-MM-DD)", file=sys.stderr)
            return 2
        paths.ensure_learner_dir()
        conn = db.open_db()
        try:
            catalog = packs.load_all()
            packs.sync_items(conn, catalog)
            data = podcast_material.material(conn, catalog, args.id, day, report._read_profile())
        finally:
            conn.close()
        print(json.dumps(data, ensure_ascii=False, indent=1))
        return 0
    if not args.id:
        print("Which episode? e.g. oknos podcast check book.lesson-01.tr")
        return 1
    try:
        if args.action == "check":
            c = podcast.check(args.id)
            for x in c["problems"]:
                print(f"PROBLEM {x}")
            for x in c["notes"][:20]:
                print(f"note    {x}")
            cost = c["cost"]
            print(f"{c['id']}: {c['segments']} segments, {len(c['parts'])} parts, about {c['minutes']} minutes.")
            print(f"Lines: {cost['lines']}; still to voice: {cost['to_make']} clips, {cost['chars']:,} characters")
            for lang, v in cost["by_lang"].items():
                print(f"  {lang}: {v['clips']} clips, {v['chars']:,} characters")
            for name, v in cost["by_provider"].items():
                free = f" of {v['free']:,} free" if v["free"] else ""
                tokens = f", about {v['tokens']:,} audio tokens" if v.get("tokens") else ""
                print(f"  {name} would make {v['chars']:,} characters{tokens} (this month so far: {v['used_this_month']:,}{free})")
            if cost.get("cast"):
                print("Cast: " + ", ".join(f"{c['name']} = {c['voice']}" for c in cost["cast"].values()))
            if cost["no_service"]:
                print(f"  {cost['no_service']} lines have no service that can make them (keys or the Voice screen's list).")
            return 1 if c["problems"] else 0
        # render
        def progress(stage, n, total):
            if n == total or n % 25 == 0:
                print(f"  {'voicing' if stage == 'clips' else 'joining'} {n}/{total}", flush=True)
            elif stage == "clips" and n % 5 == 0:
                print(f"  voicing {n}/{total}", flush=True)

        meta = podcast.render(args.id, wait=args.wait, progress=progress)
        spent = ", ".join(f"{k} {v:,} characters" for k, v in meta["chars"].items()) or "nothing (every clip was there)"
        if meta.get("tokens"):
            spent += f" ({meta['tokens']:,} audio tokens)"
        print(f"{meta['id']}: {meta['seconds'] / 60:.1f} minutes, {len(meta['parts'])} parts. Spent: {spent}.")
        print(f"File: {podcast.episode_dir(args.id) / 'episode.mp3'}")
        return 0
    except podcast.PodcastError as e:
        print(str(e))
        return 1


def cmd_reload(args) -> int:
    """Tell the running app to load new content and coach files (the coach runs this after writing)."""
    port = running_port()
    if not port:
        print("Oknos is not running. It loads the new content by itself the next time it starts.")
        return 0
    req = urllib.request.Request(f"{_url(port)}api/reload", data=b"{}", method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            info = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"The app did not answer the reload: {e}", file=sys.stderr)
        return 1
    print(f"Reloaded: {info['packs']} packs, {info['items']} items. The app is at {_url(port)}")
    for problem in info.get("problems", []):
        print(f"  content note: {problem}")
    return 0


def cmd_run(args) -> int:
    from oknos import scheduling

    ok, detail = scheduling.run(args.skill, args.agent)
    print(f"{args.skill}: {'ok' if ok else 'failed'} ({detail})")
    return 0 if ok else 1


def cmd_schedule(args) -> int:
    from oknos import scheduling

    try:
        if args.action == "add":
            if not args.skill:
                print("Say which skill to schedule: daily-prep or watch.")
                return 2
            every = args.every or ("week" if args.skill == "watch" else "day")
            print(scheduling.add(args.skill, every, args.at, args.day, args.agent))
        elif args.action == "remove":
            if not args.skill:
                print("Say which skill to unschedule: daily-prep or watch.")
                return 2
            print(scheduling.remove(args.skill))
        else:
            for line in scheduling.describe():
                print(line)
    except (ValueError, RuntimeError, OSError) as e:
        print(f"Could not change the schedule: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_schema(args) -> int:
    from oknos import coachfiles, curriculum, exams, packs

    out = paths.REPO_ROOT / "schemas"
    out.mkdir(exist_ok=True)
    schemas = {**packs.json_schemas(), "blueprint": exams.json_schema(),
               "plan": coachfiles.Plan.model_json_schema(), "mock": coachfiles.MockDef.model_json_schema(), "curriculum": curriculum.json_schema()}
    for name, schema in schemas.items():
        (out / f"{name}.schema.json").write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote schemas/{name}.schema.json")
    return 0


def cmd_shortcut(args) -> int:
    from oknos import shortcut

    try:
        created = shortcut.create()
    except Exception as e:
        print(f"Could not create the shortcut: {e}", file=sys.stderr)
        return 1
    for path in created:
        print(f"Created {path}")
    return 0 if created else 1


def cmd_guard(args: argparse.Namespace) -> int:
    from oknos import guard

    return guard.main(args.rev)


def main(argv: list[str] | None = None) -> int:
    _utf8_console()
    parser = argparse.ArgumentParser(prog="oknos", description="Oknos, a local Greek learning app.")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("start", help="start the app (in the background) and open the browser")
    p.add_argument("--foreground", action="store_true", help="run the server in this window (for development)")
    p.add_argument("--no-browser", action="store_true", help="do not open the browser")
    p.add_argument("--port", type=int, default=None, help=f"port to use (default {paths.DEFAULT_PORT} or the next free one)")
    p.set_defaults(func=cmd_start)

    p = sub.add_parser("stop", help="stop the running app")
    p.set_defaults(func=cmd_stop)

    p = sub.add_parser("guard", help="check that git tracks nothing private (learner data, private content, user paths)")
    p.add_argument("--rev", default=None, help="check this commit instead of the index (the pre-push hook passes it)")
    p.set_defaults(func=cmd_guard)

    p = sub.add_parser("health", help="check that the install works")
    p.add_argument("--server", action="store_true", help="also require the app to be running")
    p.add_argument("--json", action="store_true", help="print the result as JSON")
    p.set_defaults(func=cmd_health)

    p = sub.add_parser("validate", help="check a content pack (or a learner folder) and explain any problems")
    p.add_argument("path", help="a pack folder, a folder of packs, or a learner folder (checks the coach files too)")
    p.add_argument("--notes", type=int, default=15, help="how many notes to print per pack (default 15)")
    p.add_argument("--quick", action="store_true", help="skip the unfamiliar-words and tap-a-word checks")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("words", help="list the tappable words that find no meaning; --write maps inflected forms to their word")
    p.add_argument("path", help="a pack folder, a folder of packs, or a learner folder")
    p.add_argument("--write", action="store_true", help="add the forms Wiktionary maps to a known word to the pack's glossary.json")
    p.add_argument("--json", default=None, help="write the words still without a meaning, with hints, to this file")
    p.add_argument("--show", type=int, default=40, help="how many leftover words to print per pack (default 40)")
    p.set_defaults(func=cmd_words)

    p = sub.add_parser("report", help="print the learner's progress as JSON, for the coach")
    p.add_argument("--since", default="14d", help="the window, e.g. 14d or 3w (default 14d)")
    p.add_argument("--words", action="store_true", help="also list every word the learner has met")
    p.add_argument("--pretty", action="store_true", help="indent the JSON")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("raw", help="show raw imported exercises of a private pack, for rebuilding")
    p.add_argument("pack", help="the private pack id, e.g. greek-helper")
    p.add_argument("--unit", default=None, help="a unit id from units.json, e.g. lesson-05")
    p.add_argument("--kind", default=None, help="exercise, answer_key, test, revision or listening_test")
    p.add_argument("--pages", default=None, help="a page or page range, e.g. 66-70")
    p.add_argument("--search", default=None, help="only entries whose text contains this")
    p.add_argument("--limit", type=int, default=60)
    p.add_argument("--list-units", action="store_true", help="list the units and how many raw entries each has")
    p.set_defaults(func=cmd_raw)

    p = sub.add_parser("transcribe", help="transcribe speaking recordings locally (run as: uv run --group speech ...)")
    p.add_argument("--model", default="small", help="faster-whisper model size (default small)")
    p.add_argument("--ids", default=None, help="only these submission ids, comma-separated (re-transcribes them)")
    p.add_argument("--download", action="store_true", help="allow downloading the model (ask the learner first)")
    p.set_defaults(func=cmd_transcribe)

    p = sub.add_parser("voice", help="speech made ahead of time: status, build, sample (docs/VOICE.md)")
    p.add_argument("action", choices=["status", "build", "sample"])
    p.add_argument("provider", nargs="?", help="for sample: azure, edge, google or openai")
    p.add_argument("--limit", type=int, default=None, help="build: make at most this many clips")
    p.add_argument("--wait", action="store_true", help="build: wait for a busy provider instead of using the next one")
    p.add_argument("--redo", default=None, help="build: remake the clips this provider made, with the others")
    p.set_defaults(func=cmd_voice)

    p = sub.add_parser("podcast", help="podcast lessons: list, check, render, material, prune (docs/PODCASTS.md)")
    p.add_argument("action", choices=["list", "check", "render", "material", "prune"])
    p.add_argument("id", nargs="?", help="for check and render: the episode id (its folder in learner/podcasts/); "
                                        "for material: daily or weekly")
    p.add_argument("--date", default=None, help="material: the day the episode is for (default: tomorrow)")
    p.add_argument("--wait", action="store_true", help="render: wait for a busy voice service instead of using the next one")
    p.set_defaults(func=cmd_podcast)

    p = sub.add_parser("reload", help="make the running app load new content and coach files")
    p.set_defaults(func=cmd_reload)

    p = sub.add_parser("run", help="run a coach skill headless with the learner's agent, and log the outcome")
    p.add_argument("skill", choices=["daily-prep", "watch"])
    p.add_argument("--agent", choices=["claude", "codex"], default=None)
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("schedule", help="list, add or remove scheduled coach runs (ask the learner first)")
    p.add_argument("action", choices=["list", "add", "remove"])
    p.add_argument("skill", nargs="?", choices=["daily-prep", "watch"])
    p.add_argument("--every", choices=["day", "week"], default=None)
    p.add_argument("--at", default="05:00", help="time of day, HH:MM (default 05:00)")
    p.add_argument("--day", default="SUN", choices=["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"])
    p.add_argument("--agent", choices=["claude", "codex"], default="claude")
    p.set_defaults(func=cmd_schedule)

    p = sub.add_parser("import", help="import someone's own material as a private content pack")
    p.add_argument("mapping", help="a mapping file, or the name of a built-in one (greek-helper)")
    p.add_argument("--source", required=True, help="the folder that holds the material")
    p.add_argument("--out", default=None, help="output folder (default content/private/<pack id>)")
    p.set_defaults(func=cmd_import)

    p = sub.add_parser("schema", help="write the content pack JSON Schemas to schemas/")
    p.set_defaults(func=cmd_schema)

    p = sub.add_parser("shortcut", help="put an Oknos shortcut on the desktop")
    p.set_defaults(func=cmd_shortcut)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
