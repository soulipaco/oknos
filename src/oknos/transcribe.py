"""Local transcription of speaking recordings with faster-whisper (SPEC §9).

faster-whisper is an optional dependency group (`speech`), used only by the coach:

    uv run --group speech oknos transcribe [--model small]

The model (small, about 0.5 GB) is downloaded once into .cache/oknos/whisper/, after the
learner's OK. Transcripts go to learner/recordings/<submission-id>.json. They are "what the
machine heard", never a pronunciation score: beginner speech is hard for any recogniser.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from oknos import coachfiles, db, paths

MODEL_DIR = paths.CACHE_DIR / "whisper"
DEFAULT_MODEL = "small"


class MissingDependency(RuntimeError):
    pass


def model_cached(name: str = DEFAULT_MODEL) -> bool:
    return (MODEL_DIR / f"models--Systran--faster-whisper-{name}" / "snapshots").is_dir()


def pending(conn: sqlite3.Connection, ids: list[int] | None = None) -> list[sqlite3.Row]:
    rows = conn.execute("SELECT * FROM submissions WHERE kind='speaking' AND recording_path IS NOT NULL ORDER BY id").fetchall()
    out = []
    for r in rows:
        if ids is not None and r["id"] not in ids:
            continue
        if ids is None and coachfiles.transcript(r["id"]) is not None:
            continue
        out.append(r)
    return out


def transcribe(conn: sqlite3.Connection, model_name: str = DEFAULT_MODEL, ids: list[int] | None = None,
               allow_download: bool = False) -> list[dict]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise MissingDependency(
            "faster-whisper is not installed. Run this command as: uv run --group speech oknos transcribe"
        ) from e
    todo = pending(conn, ids)
    if not todo:
        return []
    if not model_cached(model_name) and not allow_download:
        raise MissingDependency(
            f"The '{model_name}' speech model is not downloaded yet (about 0.5 GB for 'small'). "
            "Ask the learner, then run again with --download."
        )
    model = WhisperModel(model_name, device="cpu", compute_type="int8", download_root=str(MODEL_DIR))
    done = []
    for r in todo:
        audio = paths.learner_dir() / r["recording_path"]
        if not audio.is_file():
            continue
        segments, info = model.transcribe(str(audio), language="el", beam_size=5, vad_filter=True)
        segs = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip(),
                 "avg_logprob": round(s.avg_logprob, 3)} for s in segments]
        result = {
            "submission_id": r["id"],
            "item_key": r["item_key"],
            "model": f"faster-whisper-{model_name}",
            "language": info.language,
            "duration_s": round(info.duration, 1),
            "text": " ".join(s["text"] for s in segs).strip(),
            "segments": segs,
            "transcribed_at": db.now(),
        }
        out = coachfiles.recordings_dir() / f"{r['id']}.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        done.append(result)
    return done
