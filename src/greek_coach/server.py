"""The local web server: JSON API plus the static front end in web/."""

from __future__ import annotations

import json
import logging
import mimetypes
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from greek_coach import db, health, lookup, packs, paths, scheduler, session
from greek_coach.checking import CheckError, check
from greek_coach.packs import FormItem, VocabItem

log = logging.getLogger("greek_coach.server")

# Some Windows registries map .js to text/plain, which makes browsers refuse ES modules.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/json", ".json")

UI_LANGS = ("en", "tr")
DEFAULT_MINUTES = 10


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


def create_app() -> FastAPI:
    paths.ensure_learner_dir()
    conn = db.open_db()
    catalog = packs.load_all()
    packs.sync_items(conn, catalog)
    conn.close()

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
        conn = db.open_db()
        try:
            stats = session.home_stats(conn, app.state.catalog, lang)
        finally:
            conn.close()
        return {
            "ui_lang": profile.get("ui_lang") if profile.get("ui_lang") in UI_LANGS else None,
            "minutes": _minutes(profile),
            "packs": [{"id": p.id, "title": p.manifest.title.model_dump(), "items": len(p.items)}
                      for p in app.state.catalog.packs],
            "stats": stats,
            "today": db.today().isoformat(),
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
                        int(result.correct),
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
                state = scheduler.record(conn, body.item_key, item.type, result.correct, result.score,
                                         lookups=max(0, body.lookups), accent_note=bool(result.accent_note),
                                         quick=quick)
        finally:
            conn.close()
        out: dict[str, Any] = {
            "attempt_id": cur.lastrowid,
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
