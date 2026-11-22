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

from oknos import (coachfiles, curriculum, db, exams, health, lookup, mock, packs, paths, plan, readiness,
                         scheduler, session, voice)
from oknos.checking import CheckError, check
from oknos.packs import OPEN_TASKS, FormItem, SpeakItem, VocabItem, WriteItem

log = logging.getLogger("oknos.server")

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
    kind: Literal["daily", "extra", "practice", "choose"] = "daily"
    items: list[str] = []  # practice sessions: these item keys, in this order
    what: str | None = None    # choose: words, verbs, reading, listening, tasks, writing, speaking, review
    stage: str | None = None
    lemma: str | None = None
    topic: str | None = None
    minutes: int | None = None
    ui_lang: Literal["en", "tr"] | None = None
    has_voice: bool = False


class ChapterProgressIn(BaseModel):
    section: int | None = None
    finished: bool = False


class ChapterChecksIn(BaseModel):
    items: list[str] = []


class ChapterPracticeIn(BaseModel):
    minutes: int | None = None
    has_voice: bool = False


class ChapterFlagIn(BaseModel):
    section: int
    reason: Literal["wrong", "confusing", "audio"] = "wrong"
    note: str | None = None


class VoiceSampleIn(BaseModel):
    provider: str
    role: Literal["f", "m"] = "f"


class VoiceOrderIn(BaseModel):
    providers: list[str]


class FlagIn(BaseModel):
    item_key: str
    reason: Literal["wrong", "confusing", "audio"] = "wrong"
    note: str | None = None


class LookupIn(BaseModel):
    word: str
    item_key: str | None = None
    ui_lang: Literal["en", "tr"] | None = None


class MockAnswerIn(BaseModel):
    item_key: str
    response: dict[str, Any]


class MockCloseIn(BaseModel):
    by: Literal["learner", "time"] = "learner"


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

    app = FastAPI(title="Oknos", docs_url=None, redoc_url=None, openapi_url=None)
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
            try:
                cur = curriculum.summary(conn, app.state.catalog)
                cur_brief = None
                next_action = curriculum.next_action(curriculum.progress(conn, app.state.catalog),
                                                     stats["today"]["state"], stats["due"]["vocab"])
                if cur is not None:
                    cur_brief = {k: cur[k] for k in ("curriculum", "title", "current", "stages_done", "stages_total")}
                    nxt = cur["current"]["order"] + 1
                    cur_brief["next"] = cur["stages"][nxt] if nxt < len(cur["stages"]) else None
            except Exception:  # the home screen must open even if the curriculum breaks
                log.exception("curriculum")
                cur_brief = None
                next_action = {"kind": "daily", "stage": None, "then": None}
            try:
                words = session.home_words(conn, app.state.catalog, lang)
            except Exception:  # the home screen must open even if this breaks
                log.exception("home words")
                words = None
            try:
                mock.expire(conn, app.state.catalog)
                ready_brief = {k: _brief(v) for k, v in readiness.all_readiness(conn, app.state.catalog).items()}
            except Exception:  # the home screen must open even if readiness breaks
                log.exception("readiness")
                ready_brief = None
        finally:
            conn.close()
        return {
            "coach": coach,
            "readiness": ready_brief,
            "curriculum": cur_brief,
            "words": words,
            "next_action": next_action,
            "target_exam": profile.get("target_exam"),
            "ui_lang": profile.get("ui_lang") if profile.get("ui_lang") in UI_LANGS else None,
            "minutes": _minutes(profile),
            "packs": [{"id": p.id, "title": p.manifest.title.model_dump(), "items": len(p.items)}
                      for p in app.state.catalog.packs],
            "stats": stats,
            "today": db.today().isoformat(),
        }

    def _brief(r: dict) -> dict:
        return {"exam": r["exam"], "short": r["short"], "verdict": r["verdict"]["state"],
                "units": [{k: u[k] for k in ("unit", "points", "pass_line", "state", "estimate", "low", "high",
                                             "evidence", "evidence_needed")} for u in r["units"]]}

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
            if body.kind == "choose":
                try:
                    return session.chosen(conn, app.state.catalog, lang, body.what or "words",
                                          max(2, min(60, body.minutes or 10)), body.stage, body.lemma, body.topic,
                                          has_voice=body.has_voice)
                except ValueError as e:
                    raise HTTPException(422, str(e))
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
            if result is not None:
                result["check"] = curriculum.finish_check(conn, session_id)
        finally:
            conn.close()
        if result is None:
            raise HTTPException(404, f"unknown session {session_id}")
        return result

    # ---------- the curriculum and the learner's own lists (phase 5b) ----------

    @app.get("/api/curriculum")
    def get_curriculum():
        conn = db.open_db()
        try:
            out = curriculum.summary(conn, app.state.catalog)
            if out:
                out["pictures"] = session.stage_pictures(conn, app.state.catalog, _lang(read_profile()))
        finally:
            conn.close()
        return out or {"curriculum": None}

    @app.get("/api/practise")
    def get_practise(stage: str | None = None):
        """How many cards each practice choice has waiting (the Practise screen's tiles)."""
        conn = db.open_db()
        try:
            return session.choice_counts(conn, app.state.catalog, _lang(read_profile()), stage)
        finally:
            conn.close()

    @app.get("/api/curriculum/stages/{stage_id}")
    def get_stage(stage_id: str):
        lang = _lang(read_profile())
        conn = db.open_db()
        try:
            out = session.stage_detail(conn, app.state.catalog, lang, stage_id)
        finally:
            conn.close()
        if out is None:
            raise HTTPException(404, "no such stage")
        return out

    @app.post("/api/curriculum/stages/{stage_id}/check")
    def stage_check(stage_id: str):
        lang = _lang(read_profile())
        conn = db.open_db()
        try:
            return curriculum.start_check(conn, app.state.catalog, stage_id, lang)
        except ValueError as e:
            raise HTTPException(409, str(e))
        finally:
            conn.close()

    # ---------- chapters: read first, then practise (phase 5c) ----------

    def _chapter_or_404(conn, stage_id: str):
        cur = curriculum.active(app.state.catalog)
        ch = app.state.catalog.chapter(cur.id, stage_id) if cur else None
        if ch is None:
            raise HTTPException(404, "this stage has no chapter")
        return cur, ch

    @app.get("/api/chapters/{stage_id}")
    def get_chapter(stage_id: str):
        lang = _lang(read_profile())
        conn = db.open_db()
        try:
            cur = curriculum.active(app.state.catalog)
            ch = app.state.catalog.chapter(cur.id, stage_id) if cur else None
            if ch is not None and stage_id in [s.id for s in cur.stages]:
                curriculum.mark_read(conn, cur.id, stage_id, ch.version)  # opened
            out = session.chapter_view(conn, app.state.catalog, lang, stage_id)
        finally:
            conn.close()
        if out is None:
            raise HTTPException(404, "this stage has no chapter")
        return out

    @app.post("/api/chapters/{stage_id}/progress")
    def chapter_progress(stage_id: str, body: ChapterProgressIn):
        conn = db.open_db()
        try:
            cur, ch = _chapter_or_404(conn, stage_id)
            if body.section is not None and not 0 <= body.section < len(ch.sections):
                raise HTTPException(422, "no such section")
            return curriculum.mark_read(conn, cur.id, stage_id, ch.version, body.section, body.finished)
        finally:
            conn.close()

    @app.post("/api/chapters/{stage_id}/checks")
    def chapter_checks(stage_id: str, body: ChapterChecksIn):
        lang = _lang(read_profile())
        conn = db.open_db()
        try:
            return session.chapter_checks(conn, app.state.catalog, lang, stage_id, body.items)
        except ValueError as e:
            raise HTTPException(404, str(e))
        finally:
            conn.close()

    @app.post("/api/chapters/{stage_id}/practice")
    def chapter_practice(stage_id: str, body: ChapterPracticeIn):
        lang = _lang(read_profile())
        conn = db.open_db()
        try:
            return session.chapter_practice(conn, app.state.catalog, lang, stage_id,
                                            max(2, min(60, body.minutes or _minutes(read_profile()))), body.has_voice)
        except ValueError as e:
            raise HTTPException(404, str(e))
        finally:
            conn.close()

    @app.post("/api/chapters/{stage_id}/flag")
    def chapter_flag(stage_id: str, body: ChapterFlagIn):
        conn = db.open_db()
        try:
            cur, ch = _chapter_or_404(conn, stage_id)
            if not 0 <= body.section < len(ch.sections):
                raise HTTPException(422, "no such section")
            with conn:
                row = conn.execute("INSERT INTO flags(ts, item_key, reason, note) VALUES (?, ?, ?, ?)",
                                   (db.now(), f"chapter:{cur.id}/{stage_id}#{body.section}", body.reason,
                                    (body.note or "")[:500] or None))
        finally:
            conn.close()
        return {"flag_id": row.lastrowid}

    @app.get("/api/words")
    def get_words():
        lang = _lang(read_profile())
        conn = db.open_db()
        try:
            return session.word_list(conn, app.state.catalog, lang)
        finally:
            conn.close()

    @app.get("/api/verbs")
    def get_verbs():
        lang = _lang(read_profile())
        conn = db.open_db()
        try:
            return session.verb_table(conn, app.state.catalog, lang)
        finally:
            conn.close()

    # ---------- exam mode ----------

    @app.get("/api/exam")
    def exam_view():
        """Everything the exam screen shows: readiness against both pass rules, coverage, the
        plan with planned against done, the next dates, mocks and exam technique."""
        profile = read_profile()
        lang = _lang(profile)
        _sync_coach_files()
        conn = db.open_db()
        try:
            mock.expire(conn, app.state.catalog)
            ready = readiness.all_readiness(conn, app.state.catalog)
            cover = readiness.all_coverage(conn, app.state.catalog, lang)
            progress = plan.progress(conn, app.state.catalog)
            pinputs = plan.inputs(conn, profile, ready)
            mocks = {"defined": mock.definitions(app.state.catalog), "runs": mock.runs(conn, app.state.catalog)}
        finally:
            conn.close()
        bps = exams.load_blueprints()
        return {
            "today": db.today().isoformat(),
            "target_exam": profile.get("target_exam"),
            "exams": [{"id": bp.id, "short": bp.short, "title": bp.title.model_dump(), "level": bp.level,
                       "checked_at": bp.checked_at, "pass_rule": bp.pass_rule.model_dump(),
                       "sessions_note": bp.sessions_note.model_dump() if bp.sessions_note else None,
                       "units": [{"id": u.id, "title": u.title.model_dump(), "points": u.points, "minutes": u.minutes,
                                  "marked_by": u.marked_by, "technique": u.technique.model_dump(),
                                  "note": u.note.model_dump() if u.note else None,
                                  "tasks": [{"id": t.id, "title": t.title.model_dump(), "points": t.points,
                                             "questions": t.questions, "points_verified": t.points_verified}
                                            for t in u.tasks]} for u in bp.units],
                       "readiness": ready.get(bp.id), "coverage": cover.get(bp.id)} for bp in bps.values()],
            "plan": progress,
            "plan_inputs": {k: pinputs[k] for k in ("budget_minutes_week", "pace", "candidates",
                                                     "exams_without_announced_date", "watch_checked_at")},
            "dates": coachfiles.next_dates(db.today(), limit=4),
            "mocks": mocks,
        }

    def _mock_call(fn):
        conn = db.open_db()
        try:
            return fn(conn)
        except mock.MockError as e:
            raise HTTPException(409, str(e))
        finally:
            conn.close()

    @app.post("/api/mocks/{mock_id}/start")
    def mock_start(mock_id: str):
        return _mock_call(lambda conn: mock.run_view(conn, app.state.catalog,
                                                     mock.start_run(conn, app.state.catalog, mock_id)))

    @app.get("/api/mock-runs/{run_id}")
    def mock_run(run_id: int):
        _sync_coach_files()
        return _mock_call(lambda conn: mock.run_view(conn, app.state.catalog, run_id))

    @app.post("/api/mock-runs/{run_id}/sections/{unit}")
    def mock_section_start(run_id: int, unit: str):
        def go(conn):
            mock.expire(conn, app.state.catalog)
            sid = mock.start_section(conn, app.state.catalog, run_id, unit, _lang(read_profile()))
            return mock.section_view(conn, sid)
        return _mock_call(go)

    @app.get("/api/mock-sections/{section_id}")
    def mock_section(section_id: int):
        def go(conn):
            mock.expire(conn, app.state.catalog)
            return mock.section_view(conn, section_id)
        return _mock_call(go)

    @app.post("/api/mock-sections/{section_id}/answer")
    def mock_answer(section_id: int, body: MockAnswerIn):
        return _mock_call(lambda conn: mock.save_answer(conn, app.state.catalog, section_id, body.item_key, body.response))

    @app.post("/api/mock-sections/{section_id}/close")
    def mock_close(section_id: int, body: MockCloseIn):
        def go(conn):
            # This section first, as the page says (handed in, or its clock reached 0); then any
            # other section that ran out with nobody there.
            mock.close_section(conn, app.state.catalog, section_id, body.by)
            mock.expire(conn, app.state.catalog)
            return mock.section_view(conn, section_id)
        return _mock_call(go)

    @app.post("/api/mock-runs/{run_id}/abandon")
    def mock_abandon(run_id: int):
        def go(conn):
            mock.abandon(conn, app.state.catalog, run_id)
            return mock.run_view(conn, app.state.catalog, run_id)
        return _mock_call(go)

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
                sure = how in ("exact", "accents") or (how in ("stem", "form") and len(entries) == 1)
                # only real items have a review schedule (function words such as την are not items)
                if (entries and sure and entries[0].item_key != body.item_key
                        and entries[0].item_key in app.state.catalog.items):
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

    @app.api_route("/pictures/{pack_id}/{name}", methods=["GET", "HEAD"])
    def pack_picture(pack_id: str, name: str):
        """A word's picture (phase 9), from the pack's pictures/ folder."""
        pack = next((p for p in app.state.catalog.packs if p.id == pack_id), None)
        if pack is None:
            raise HTTPException(404, "unknown pack")
        base = (pack.path / "pictures").resolve()
        target = (base / name).resolve()
        if base not in target.parents or not target.is_file() or target.suffix not in (".webp", ".png", ".svg"):
            raise HTTPException(404, "no such picture")
        kind = {".webp": "image/webp", ".png": "image/png", ".svg": "image/svg+xml"}[target.suffix]
        return FileResponse(target, media_type=kind, headers={"Cache-Control": "max-age=86400"})

    # ---------- speech made ahead of time (phase 10, src/oknos/voice.py) ----------

    @app.api_route("/voice", methods=["GET", "HEAD"])
    def voice_clip(r: str = "f", t: str = ""):
        """The made clip for a text in a voice (f or m); 404 means: use the browser's voice."""
        if r not in voice.ROLES or not t.strip():
            raise HTTPException(404, "no clip")
        target = voice.file_for(t, r)
        if not target.is_file():
            raise HTTPException(404, "no clip")
        return FileResponse(target, media_type="audio/mpeg", headers={"Cache-Control": "max-age=86400"})

    @app.get("/api/voice")
    def voice_status(brief: bool = False):
        if brief:  # what every screen needs at start: are there clips at all
            return {"files": len(voice.read_index())}
        return voice.status(app.state.catalog)

    @app.api_route("/voice-sample/{name}", methods=["GET", "HEAD"])
    def voice_sample_file(name: str):
        base = (voice.voice_dir() / "samples").resolve()
        target = (base / name).resolve()
        if base not in target.parents or target.suffix != ".mp3" or not target.is_file():
            raise HTTPException(404, "no sample")
        return FileResponse(target, media_type="audio/mpeg")

    @app.post("/api/voice/sample")
    def voice_sample(body: VoiceSampleIn):
        """Make the test sentences now with one provider (sends only those two sentences to it)."""
        if body.provider not in voice.providers():
            raise HTTPException(404, "unknown provider")
        try:
            path = voice.make_sample(body.provider, body.role)
        except voice.Refused as e:
            raise HTTPException(409, str(e))
        return {"url": f"/voice-sample/{path.name}"}

    @app.post("/api/voice/order")
    def voice_order(body: VoiceOrderIn):
        known = voice.providers()
        chosen = [p for p in dict.fromkeys(body.providers) if p in known]
        profile = read_profile()
        write_profile({"voice": {**(profile.get("voice") or {}), "providers": chosen}})
        return voice.status(app.state.catalog)

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
