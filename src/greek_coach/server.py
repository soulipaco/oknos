"""The local web server: JSON API plus the static front end in web/."""

from __future__ import annotations

import json
import logging
import mimetypes
import secrets
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from greek_coach import coachfiles, db, health, lookup, packs, paths, scheduler, session
from greek_coach.checking import CheckError, check
from greek_coach.packs import OPEN_TASKS, FormItem, SpeakItem, VocabItem, WriteItem

log = logging.getLogger("greek_coach.server")

# Some Windows registries map .js to text/plain, which makes browsers refuse ES modules.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/json", ".json")

UI_LANGS = ("en", "tr")
DEFAULT_MINUTES = 10
RECORDING_MAX_BYTES = 20_000_000
RECORDING_TYPES = {"audio/webm": ".webm", "audio/ogg": ".ogg", "audio/mp4": ".m4a", "audio/mpeg": ".mp3",
                   "audio/wav": ".wav", "audio/x-wav": ".wav"}


def read_profile() -> dict:
    try:
        data = json.loads(paths.profile_path().read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def write_profile(changes: dict) -> dict:
    profile = read_profile()
    profile.update(changes)
    paths.ensure_learner_dir()
    paths.profile_path().write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return profile


def _lang(profile: dict, fallback: str = "en") -> str:
    lang = profile.get("ui_lang")
    return lang if lang in UI_LANGS else fallback


def _minutes(profile: dict) -> int:
    m = profile.get("minutes")
    return m if isinstance(m, int) and 1 <= m <= 120 else DEFAULT_MINUTES


class ProfileIn(BaseModel):
    ui_lang: Literal["en", "tr"] | None = None
    minutes: int | None = None


class SessionIn(BaseModel):
    kind: Literal["daily", "extra", "practice"] = "daily"
    items: list[str] = []  # practice sessions: these item keys, in this order
    ui_lang: Literal["en", "tr"] | None = None
    has_voice: bool = False


class FlagIn(BaseModel):
    item_key: str
    reason: Literal["wrong", "confusing", "audio"] = "wrong"
    note: str | None = None


class LookupIn(BaseModel):
    word: str
    item_key: str | None = None
    ui_lang: Literal["en", "tr"] | None = None


class AttemptIn(BaseModel):
    session_id: int
    item_key: str
    card: dict[str, Any] = {}
    response: dict[str, Any]
    latency_ms: int | None = None
    audio_plays: int = 0
    lookups: int = 0


def _sync_coach_files() -> None:
    """Take in what the coach wrote (feedback, flag verdicts). Never fatal."""
    try:
        conn = db.open_db()
        try:
            coachfiles.sync(conn)
        finally:
            conn.close()
    except Exception:  # a broken coach file must never take the app down
        log.exception("could not read the coach's files")


def _word_count(text: str) -> int:
    return len([w for w in text.split() if any(c.isalnum() for c in w)])


def create_app() -> FastAPI:
    paths.ensure_learner_dir()
    conn = db.open_db()
    catalog = packs.load_all()
    packs.sync_items(conn, catalog)
    conn.close()
    _sync_coach_files()

    app = FastAPI(title="Greek Coach", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.catalog = catalog
    app.state.lookup = lookup.Index(catalog)

    def reload_content() -> packs.Catalog:
        fresh = packs.load_all()
        c = db.open_db()
        try:
            packs.sync_items(c, fresh)
        finally:
            c.close()
        app.state.catalog = fresh
        app.state.lookup = lookup.Index(fresh)
        _sync_coach_files()
        return fresh

    @app.middleware("http")
    async def no_cache(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-cache"
        return response

    @app.get("/health")
    def get_health():
        return health.report(app.state.catalog)

    @app.get("/api/home")
    def home():
        profile = read_profile()
        lang = _lang(profile)
        _sync_coach_files()
        conn = db.open_db()
        try:
            stats = session.home_stats(conn, app.state.catalog, lang)
            coach = coach_block(conn)
        finally:
            conn.close()
        return {
            "coach": coach,
            "ui_lang": profile.get("ui_lang") if profile.get("ui_lang") in UI_LANGS else None,
            "minutes": _minutes(profile),
            "packs": [{"id": p.id, "title": p.manifest.title.model_dump(), "items": len(p.items)}
                      for p in app.state.catalog.packs],
            "stats": stats,
            "today": db.today().isoformat(),
        }

    def coach_block(conn) -> dict:
        today = db.today()
        ready = conn.execute("SELECT id, kind FROM submissions WHERE status='marked' AND feedback_seen_at IS NULL "
                             "ORDER BY id DESC").fetchall()
        waiting = conn.execute("SELECT COUNT(*) FROM submissions WHERE status='new'").fetchone()[0]
        total = conn.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
        try:
            problems = coachfiles.run_problems()
            dates = coachfiles.next_dates(today)
            message = coachfiles.message_for_home(today)
        except Exception:
            log.exception("coach files")
            problems, dates, message = [], None, None
        return {
            "message": message,
            "dates": dates,
            "feedback_ready": [{"id": r["id"], "kind": r["kind"]} for r in ready],
            "submissions_waiting": waiting,
            "submissions_total": total,
            "run_problems": problems,
        }

    @app.post("/api/profile")
    def set_profile(body: ProfileIn):
        changes: dict[str, Any] = {}
        if body.ui_lang:
            changes["ui_lang"] = body.ui_lang
        if body.minutes is not None:
            if not 1 <= body.minutes <= 120:
                raise HTTPException(422, "minutes must be between 1 and 120")
            changes["minutes"] = body.minutes
        profile = write_profile(changes) if changes else read_profile()
        return {"ui_lang": profile.get("ui_lang"), "minutes": _minutes(profile)}

    @app.post("/api/session")
    def new_session(body: SessionIn):
        profile = read_profile()
        lang = body.ui_lang or _lang(profile)
        minutes = _minutes(profile) if body.kind == "daily" else 5
        if body.kind == "daily":
            minutes = coachfiles.restart_minutes(db.today()) or minutes  # the coach asked for a small restart
        conn = db.open_db()
        try:
            if body.kind == "practice":
                missing = [k for k in body.items if k not in app.state.catalog.items]
                if missing or not body.items:
                    raise HTTPException(404, f"unknown items: {missing}")
                return session.practice(conn, app.state.catalog, lang, body.items)
            return session.build(conn, app.state.catalog, lang, minutes, body.kind, has_voice=body.has_voice)
        finally:
            conn.close()

    @app.post("/api/attempt")
    def attempt(body: AttemptIn):
        entry = app.state.catalog.items.get(body.item_key)
        if entry is None:
            raise HTTPException(404, f"unknown item {body.item_key}")
        _, item = entry
        try:
            result = check(item, body.card, body.response)
        except CheckError as e:
            raise HTTPException(422, str(e))
        record = {"card": {k: v for k, v in body.card.items() if k != "item_key"}, "response": body.response}
        recording = None
        if isinstance(item, SpeakItem) and body.response.get("recording"):
            recording = _recording_file(body.response["recording"])
            if recording is None:
                raise HTTPException(422, "that recording was not uploaded")
        expected = session.DEFAULT_SECONDS[session.card_class(item)]
        quick = body.latency_ms is not None and body.latency_ms < expected * 1000 * 0.5
        conn = db.open_db()
        try:
            if conn.execute("SELECT 1 FROM sessions WHERE id=?", (body.session_id,)).fetchone() is None:
                raise HTTPException(404, f"unknown session {body.session_id}")
            with conn:
                cur = conn.execute(
                    """
                    INSERT INTO attempts(session_id, item_key, ts, response_json, score, correct, latency_ms,
                                         lookups, audio_plays, accent_note)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        body.session_id,
                        body.item_key,
                        db.now(),
                        json.dumps(record, ensure_ascii=False),
                        result.score,
                        None if result.correct is None else int(result.correct),
                        body.latency_ms,
                        max(0, body.lookups),
                        body.audio_plays,
                        result.accent_note,
                    ),
                )
                conn.execute(
                    "UPDATE sessions SET items_done=(SELECT COUNT(*) FROM attempts WHERE session_id=?) WHERE id=?",
                    (body.session_id, body.session_id),
                )
                state = None
                submission_id = None
                if isinstance(item, OPEN_TASKS):
                    submission_id = _save_submission(conn, item, body, cur.lastrowid, recording)
                else:
                    state = scheduler.record(conn, body.item_key, item.type, result.correct, result.score,
                                             lookups=max(0, body.lookups), accent_note=bool(result.accent_note),
                                             quick=quick)
        finally:
            conn.close()
        out: dict[str, Any] = {
            "attempt_id": cur.lastrowid,
            "submission_id": submission_id,
            "score": result.score,
            "correct": result.correct,
            "answer": result.answer,
            "parts": result.parts,
            "accent_note": result.accent_note,
            "explain": item.explain.model_dump() if item.explain else None,
            "next_due": state.due_at if state else None,
        }
        if isinstance(item, VocabItem) and item.example:
            out["example"] = item.example.model_dump()
        if isinstance(item, FormItem) and item.translation:
            out["translation"] = item.translation.model_dump()
        return out

    def _recording_file(name: str):
        base = coachfiles.recordings_dir().resolve()
        target = (paths.learner_dir() / name).resolve()
        if base in target.parents and target.is_file():
            return target
        return None

    def _save_submission(conn, item, body: AttemptIn, attempt_id: int, recording) -> int | None:
        if body.response.get("skipped"):
            return None
        if isinstance(item, WriteItem):
            text = body.response["text"].strip()
            cur = conn.execute(
                "INSERT INTO submissions(item_key, session_id, attempt_id, ts, kind, text, word_count) "
                "VALUES (?, ?, ?, ?, 'writing', ?, ?)",
                (body.item_key, body.session_id, attempt_id, db.now(), text, _word_count(text)))
            return cur.lastrowid
        if recording is None:
            return None  # spoke aloud without recording: counted as done, nothing to mark
        cur = conn.execute(
            "INSERT INTO submissions(item_key, session_id, attempt_id, ts, kind) VALUES (?, ?, ?, ?, 'speaking')",
            (body.item_key, body.session_id, attempt_id, db.now()))
        sid = cur.lastrowid
        final = recording.with_name(f"{sid}{recording.suffix}")
        recording.replace(final)
        conn.execute("UPDATE submissions SET recording_path=? WHERE id=?",
                     (final.relative_to(paths.learner_dir()).as_posix(), sid))
        return sid

    @app.post("/api/recording")
    async def upload_recording(request: Request):
        """A speaking recording, sent as the raw request body (no form encoding)."""
        kind = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
        ext = RECORDING_TYPES.get(kind)
        if ext is None:
            raise HTTPException(415, f"unsupported audio type {kind!r}")
        data = await request.body()
        if not data:
            raise HTTPException(422, "the recording is empty")
        if len(data) > RECORDING_MAX_BYTES:
            raise HTTPException(413, "the recording is too long")
        folder = coachfiles.recordings_dir()
        folder.mkdir(parents=True, exist_ok=True)
        name = f"upload-{db.today().isoformat()}-{secrets.token_hex(4)}{ext}"
        (folder / name).write_bytes(data)
        return {"recording": f"recordings/{name}"}

    @app.api_route("/recordings/{name}", methods=["GET", "HEAD"])
    def get_recording(name: str):
        target = _recording_file(f"recordings/{name}")
        if target is None:
            raise HTTPException(404, "no such recording")
        return FileResponse(target)

    def _submission_json(r, full: bool) -> dict:
        entry = app.state.catalog.items.get(r["item_key"])
        item = entry[1] if entry else None
        out = {"id": r["id"], "kind": r["kind"], "ts": r["ts"], "item_key": r["item_key"], "status": r["status"],
               "word_count": r["word_count"], "seen": bool(r["feedback_seen_at"]),
               "prompt": item.prompt.model_dump() if isinstance(item, (WriteItem, SpeakItem)) else None}
        if full:
            out["text"] = r["text"]
            out["recording"] = f"/{r['recording_path']}" if r["recording_path"] else None
            if isinstance(item, WriteItem):
                out["words"] = item.words
            if isinstance(item, SpeakItem) and item.model:
                out["model"] = item.model.model_dump()
            fb = coachfiles.feedback(r["id"])
            out["feedback"] = fb.model_dump() if fb else None
            tr = coachfiles.transcript(r["id"])
            out["transcript"] = tr.get("text") if tr else None
        return out

    @app.get("/api/submissions")
    def list_submissions():
        _sync_coach_files()
        conn = db.open_db()
        try:
            rows = conn.execute("SELECT * FROM submissions ORDER BY id DESC LIMIT 100").fetchall()
        finally:
            conn.close()
        return {"submissions": [_submission_json(r, False) for r in rows]}

    @app.get("/api/submissions/{submission_id}")
    def get_submission(submission_id: int):
        _sync_coach_files()
        conn = db.open_db()
        try:
            r = conn.execute("SELECT * FROM submissions WHERE id=?", (submission_id,)).fetchone()
            if r is None:
                raise HTTPException(404, "no such submission")
            out = _submission_json(r, True)
            if out["feedback"] and not r["feedback_seen_at"]:
                with conn:
                    conn.execute("UPDATE submissions SET feedback_seen_at=? WHERE id=?", (db.now(), submission_id))
        finally:
            conn.close()
        return out

    @app.post("/api/session/{session_id}/end")
    def end_session(session_id: int):
        lang = _lang(read_profile())
        conn = db.open_db()
        try:
            session.end(conn, session_id)
            result = session.summary(conn, app.state.catalog, session_id, lang)
        finally:
            conn.close()
        if result is None:
            raise HTTPException(404, f"unknown session {session_id}")
        return result

    @app.post("/api/lookup")
    def do_lookup(body: LookupIn):
        lang = body.ui_lang or _lang(read_profile())
        entries, how = app.state.lookup.find(body.word)
        conn = db.open_db()
        try:
            with conn:
                conn.execute(
                    "INSERT INTO lookups(ts, item_key, word, found) VALUES (?, ?, ?, ?)",
                    (db.now(), body.item_key, body.word[:80], entries[0].item_key if entries else None),
                )
                # Tapping a word signals it was not known (unless the match is ambiguous).
                sure = how in ("exact", "accents") or (how == "stem" and len(entries) == 1)
                if entries and sure and entries[0].item_key != body.item_key:
                    scheduler.lookup_signal(conn, entries[0].item_key)
        finally:
            conn.close()
        return lookup.as_json(entries, how, lang)

    @app.post("/api/flag")
    def flag(body: FlagIn):
        if body.item_key not in app.state.catalog.items:
            raise HTTPException(404, f"unknown item {body.item_key}")
        conn = db.open_db()
        try:
            with conn:
                cur = conn.execute("INSERT INTO flags(ts, item_key, reason, note) VALUES (?, ?, ?, ?)",
                                   (db.now(), body.item_key, body.reason, (body.note or "")[:500] or None))
        finally:
            conn.close()
        return {"flag_id": cur.lastrowid}

    @app.post("/api/reload")
    def reload():
        """Reload content packs (the coach calls this after writing a pack)."""
        fresh = reload_content()
        return {"packs": len(fresh.packs), "items": len(fresh.items), "problems": fresh.problems[:50]}

    @app.api_route("/packs/{pack_id}/audio/{name:path}", methods=["GET", "HEAD"])
    def pack_audio(pack_id: str, name: str):
        pack = next((p for p in app.state.catalog.packs if p.id == pack_id), None)
        if pack is None:
            raise HTTPException(404, "unknown pack")
        base = (pack.path / "audio").resolve()
        target = (base / name).resolve()
        if base not in target.parents or not target.is_file():
            raise HTTPException(404, "no such audio file")
        return FileResponse(target)

    @app.api_route("/audio-cache/{pack_id}/{item_id}", methods=["GET", "HEAD"])
    def cached_audio(pack_id: str, item_id: str):
        """Listening audio pre-generated by the coach (scripts/make_audio.py) into learner/audio/."""
        base = paths.audio_cache_dir().resolve()
        for ext in (".mp3", ".wav", ".ogg"):
            target = (base / pack_id / f"{item_id}{ext}").resolve()
            if base in target.parents and target.is_file():
                return FileResponse(target)
        raise HTTPException(404, "no pre-generated audio")

    app.mount("/", StaticFiles(directory=paths.WEB_DIR, html=True), name="web")
    return app
