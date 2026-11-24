"""Phase 11: podcast lessons, written as a script, checked, and joined into one file (docs/PODCASTS.md)."""

import io
import json
import math
import shutil
import struct
import wave

import pytest

from oknos import podcast, voice

HAS_FFMPEG = shutil.which("ffmpeg") is not None


def tone(seconds: float, rate: int = 24_000) -> bytes:
    """A short WAV clip (ffmpeg reads it by its content, whatever the file is called)."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(i / 8))) for i in range(int(seconds * rate))))
    return buf.getvalue()


class Speaker(voice.Provider):
    """A keyed provider with Greek, Turkish and English voices; each clip is one second of tone."""

    def __init__(self, name="azure", *, langs=("tr", "en")):
        super().__init__(name, {"f": "el-f", "m": "el-m"}, None, label=name,
                         lang_voices={lang: {"f": f"{lang}-f", "m": f"{lang}-m"} for lang in langs})
        self.calls = []

    def ready(self, keys, profile):
        return None

    def make(self, text, role, keys, lang="el"):
        self.calls.append((text, role, lang))
        return tone(1.0)


def script(**over):
    base = {
        "id": "open.first-words.tr", "kind": "chapter", "curriculum": "open-a1-b1", "stage": "first-words",
        "lang": "tr", "title": {"tr": "İlk kelimeler", "en": "First words"}, "written": "2026-11-23",
        "sources": [{"what": "open-chapter", "ref": "open-book/lessons/first-words"}],
        "segments": [
            {"part": "Giriş"},
            {"lang": "tr", "say": "Merhaba! Bugün selamlaşmayı öğreniyoruz."},
            {"part": "Diyalog"},
            {"lang": "el", "say": "Καλημέρα!", "who": "Κατερίνα"},
            {"lang": "el", "say": "Καλημέρα!", "who": "Κατερίνα", "speed": 0.8},
            {"echo": 1.5},
            {"lang": "el", "say": "Γεια σου, Γιώργο.", "who": "Γιώργος"},
            {"pause": 1},
        ],
    }
    base.update(over)
    return base


def write(learner, raw):
    d = learner / "podcasts" / raw["id"]
    d.mkdir(parents=True, exist_ok=True)
    (d / "script.json").write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    return d


# ---------- the voices ----------

def test_greek_clip_keys_are_unchanged_and_other_languages_have_their_own(learner):
    assert voice.key("Καλημέρα", "f") == voice.key("Καλημέρα", "f", "el")
    assert voice.key("Merhaba", "f", "tr") != voice.key("Merhaba", "f", "en")
    assert voice.file_for("Merhaba", "f", lang="tr").is_relative_to(learner / "voice" / "tr" / "f")
    assert voice.file_for("Καλημέρα", "f").parent.parent.parent == learner / "voice"


def test_every_keyed_service_has_turkish_and_english_voices_and_edge_has_none():
    known = voice.providers()
    for name in ("azure", "google", "openai"):
        assert known[name].speaks("tr") and known[name].speaks("en")
    assert known["azure"].voice("f", "tr") == "tr-TR-EmelNeural"
    assert known["google"].voice("m", "en") == "en-US-Chirp3-HD-Orus"
    assert not known["edge"].speaks("tr")


def test_explanations_never_go_to_edge_and_skip_services_without_that_language(learner):
    class EdgeLike(Speaker):
        pass

    edge = EdgeLike("edge")
    greek_only = Speaker("greekonly", langs=())
    keyed = Speaker("google")
    who = voice.make("Merhaba!", "f", chain=[edge, greek_only, keyed], keys={}, profile={"edge_tts_ok": True}, lang="tr")
    assert who == "google" and edge.calls == [] and greek_only.calls == []
    assert voice.find("Merhaba!", "f", "tr") is not None
    assert voice.find("Merhaba!", "f", "en") is None


# ---------- the script ----------

def test_a_good_script_passes_the_check(learner):
    write(learner, script())
    out = podcast.check("open.first-words.tr")
    assert out["problems"] == []
    assert out["parts"] == ["Giriş", "Diyalog"]
    assert out["cost"]["lines"] == 3  # the slow repeat is the same clip


@pytest.mark.parametrize("change, expected", [
    ({"segments": [{"part": "A"}, {"lang": "tr", "say": "Kalimera demek: Καλημέρα."}, {"pause": 1}]}, "Greek letters inside a tr line"),
    ({"segments": [{"lang": "tr", "say": "Merhaba."}, {"part": "A"}, {"pause": 1}]}, "first segment must be a part"),
    ({"segments": [{"part": "A"}, {"pause": 1}, {"echo": 1.5}]}, "echo gap must follow"),
    ({"segments": [{"part": "A"}, {"lang": "el", "say": "Καλημερασ"}, {"pause": 1}]}, "σ instead of ς"),
])
def test_the_check_refuses_what_would_sound_wrong(learner, change, expected):
    write(learner, script(**change))
    assert any(expected in p for p in podcast.check("open.first-words.tr")["problems"])


@pytest.mark.parametrize("change", [
    {"segments": [{"part": "A"}, {"lang": "de", "say": "Hallo"}, {"pause": 1}]},
    {"segments": [{"part": "A"}, {"lang": "el", "say": "Γεια", "speed": 0.3}, {"pause": 1}]},
    {"lang": "el"},
    {"id": "Bad Id"},
])
def test_a_script_outside_the_format_is_refused(learner, change):
    with pytest.raises(podcast.PodcastError):
        podcast.parse(script(**change))


def test_the_script_must_sit_in_its_own_folder(learner):
    write(learner, script())
    (learner / "podcasts" / "other").mkdir()
    shutil.copy(learner / "podcasts" / "open.first-words.tr" / "script.json", learner / "podcasts" / "other" / "script.json")
    with pytest.raises(podcast.PodcastError, match="its folder"):
        podcast.load("other")


def test_unknown_or_unsafe_ids_find_no_audio(learner):
    assert podcast.audio_file("../oknos.db") is None
    assert podcast.audio_file("nothing.here") is None


# ---------- making the audio ----------

@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg joins the clips")
def test_render_makes_one_file_with_parts_and_lines_in_time(learner, monkeypatch):
    speaker = Speaker("azure")
    monkeypatch.setattr(podcast, "_chain", lambda profile, keys: [speaker])
    write(learner, script())
    meta = podcast.render("open.first-words.tr")
    assert len(speaker.calls) == 3 and {c[2] for c in speaker.calls} == {"tr", "el"}
    assert ("Γεια σου, Γιώργο.", "m", "el") in speaker.calls  # Giorgos speaks with the male voice
    assert podcast.audio_file("open.first-words.tr").stat().st_size > 1000
    assert [p["title"] for p in meta["parts"]] == ["Giriş", "Diyalog"]
    times = [line["t"] for line in meta["lines"]]
    assert times == sorted(times) and len(times) == 4
    # 3 one-second lines + 1 slowed (1.25 s) + gaps (0.35 each) + echo (1.25 × 1.5 + 1) + a 1 s pause
    expected = 3 + 1.25 + 4 * podcast.GAP + (1.25 * 1.5 + 1) + 1
    assert meta["seconds"] == pytest.approx(expected, abs=0.3)
    assert meta["chars"] == {"azure": sum(len(c[0]) for c in speaker.calls)}
    # A second render reuses every clip and spends nothing.
    again = podcast.render("open.first-words.tr")
    assert again["chars"] == {} and len(speaker.calls) == 3
    listed = podcast.listing()
    assert listed[0]["id"] == "open.first-words.tr" and listed[0]["stale"] is False


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg joins the clips")
def test_the_app_serves_the_episode_and_lets_the_phone_seek(client, learner, monkeypatch):
    monkeypatch.setattr(podcast, "_chain", lambda profile, keys: [Speaker("azure")])
    d = write(learner, script())
    podcast.render("open.first-words.tr")
    listing = client.get("/api/podcasts").json()
    assert [e["id"] for e in listing["episodes"]] == ["open.first-words.tr"]
    assert listing["by_stage"] == {"first-words": "open.first-words.tr"}
    one = client.get("/api/podcasts/open.first-words.tr").json()
    assert one["parts"][1]["title"] == "Diyalog" and one["stale"] is False
    full = client.get("/podcasts/open.first-words.tr.mp3")
    assert full.status_code == 200 and full.headers["content-type"] == "audio/mpeg"
    part = client.get("/podcasts/open.first-words.tr.mp3", headers={"Range": "bytes=100-199"})
    assert part.status_code == 206 and len(part.content) == 100
    assert client.get("/api/home").json()["podcasts"] == 1
    # The script changes: the episode is marked stale until it is made again.
    raw = script()
    raw["segments"].append({"lang": "tr", "say": "Hoşça kal!"})
    (d / "script.json").write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    assert client.get("/api/podcasts/open.first-words.tr").json()["stale"] is True


def test_no_episodes_and_unknown_ids(client):
    assert client.get("/api/podcasts").json()["episodes"] == []
    assert client.get("/api/podcasts/nothing").status_code == 404
    assert client.get("/podcasts/nothing.mp3").status_code == 404
    assert client.get("/podcasts/..%2Foknos.db.mp3").status_code == 404


def test_the_command_line_lists_and_checks_a_script(learner, capsys):
    from oknos import cli

    assert cli.main(["podcast", "list"]) == 0
    assert "No scripts yet" in capsys.readouterr().out
    write(learner, script())
    assert cli.main(["podcast", "list"]) == 0
    assert "open.first-words.tr" in capsys.readouterr().out
    assert cli.main(["podcast", "check", "open.first-words.tr"]) == 0
    out = capsys.readouterr().out
    assert "still to voice: 3 clips" in out and "tr: 1 clips" in out
    assert cli.main(["podcast", "check", "nothing"]) == 1


# ---------- personal episodes (daily, weekly) ----------

def personal(kind="daily", day="2026-11-25", **over):
    from datetime import date as _date

    from oknos.podcast_material import episode_id

    base = script(id=episode_id(kind, _date.fromisoformat(day), "tr"), kind=kind, curriculum=None, stage=None,
                  date=day, title={"tr": "Günün dersi", "en": "Today's lesson"},
                  sources=[{"what": "report", "note": "due and weak words"}], focus=["το τσάι"])
    base.update(over)
    return base


def test_personal_episode_ids_and_the_date_they_need(learner):
    from datetime import date

    from oknos.podcast_material import episode_id

    assert episode_id("daily", date(2026, 11, 25), "tr") == "daily.2026-11-25.tr"
    assert episode_id("weekly", date(2026, 11, 29), "en") == "weekly.2026-w48.en"
    write(learner, personal())
    assert podcast.check("daily.2026-11-25.tr")["problems"] == []
    no_date = personal()
    no_date.pop("date")
    write(learner, no_date)
    assert any("needs its date" in p for p in podcast.check("daily.2026-11-25.tr")["problems"])
    with pytest.raises(podcast.PodcastError):
        podcast.parse(personal(date="25 Nov"))


def _fake_render(learner, raw, rendered="2026-11-24T19:00:00"):
    """An episode on disk as render leaves it (episode.mp3 + episode.json), without ffmpeg."""
    d = write(learner, raw)
    (d / "episode.mp3").write_bytes(b"ID3")
    meta = {"id": raw["id"], "kind": raw["kind"], "lang": raw["lang"], "title": raw["title"], "date": raw.get("date"),
            "rendered": rendered, "seconds": 600, "script": podcast.script_hash(raw["id"]), "parts": []}
    (d / "episode.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return d


def test_today_is_the_daily_episode_else_the_weeks(learner):
    assert podcast.today_episode("2026-11-25") is None
    _fake_render(learner, personal("weekly", "2026-11-23"))
    assert podcast.today_episode("2026-11-25")["kind"] == "weekly"
    assert podcast.today_episode("2026-11-25", "en") is None
    _fake_render(learner, personal("daily", "2026-11-25"))
    assert podcast.today_episode("2026-11-25")["id"] == "daily.2026-11-25.tr"
    assert podcast.today_episode("2026-11-30") is None  # last week's weekly is not this week's


def test_the_home_screen_offers_todays_episode(client, learner):
    from oknos import db

    today = db.today().isoformat()
    (learner / "profile.json").write_text(json.dumps({"ui_lang": "en", "podcast": {"lang": "tr"}}), encoding="utf-8")
    assert client.get("/api/home").json()["podcast_today"] is None
    _fake_render(learner, personal("daily", today))
    got = client.get("/api/home").json()["podcast_today"]
    assert got["id"] == f"daily.{today}.tr" and got["seconds"] == 600


def test_prune_keeps_the_newest_personal_episodes_and_only_the_clips_still_spoken(learner):
    chapter = write(learner, script())
    for day in ("2026-11-20", "2026-11-21", "2026-11-22"):
        raw = personal("daily", day)
        raw["segments"] = [{"part": "Giriş"}, {"lang": "tr", "say": f"Bugün {day[-2:]}."}, {"lang": "el", "say": "Καλημέρα!"}]
        write(learner, raw)
    for text, lang in (("Merhaba! Bugün selamlaşmayı öğreniyoruz.", "tr"), ("Bugün 20.", "tr"), ("Bugün 22.", "tr"),
                       ("Καλημέρα!", "el")):
        f = voice.file_for(text, "f", lang=lang)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"ID3")
    gone = podcast.prune({"daily": 2, "weekly": 8})
    assert gone["episodes"] == ["daily.2026-11-20.tr"] and gone["clips"] == 1
    assert voice.find("Bugün 20.", "f", "tr") is None
    assert voice.find("Bugün 22.", "f", "tr") is not None
    assert voice.find("Merhaba! Bugün selamlaşmayı öğreniyoruz.", "f", "tr") is not None  # the chapter's
    assert voice.find("Καλημέρα!", "f") is not None  # Greek clips stay: the app uses them
    assert chapter.is_dir()


def test_material_lists_due_weak_and_wrong_words_with_meanings(learner, capsys):
    from datetime import timedelta

    from oknos import cli, db, packs, scheduler
    from oknos.podcast_material import material

    catalog = packs.load_all()
    conn = db.open_db()
    packs.sync_items(conn, catalog)
    words = [k for k, (_, it) in catalog.items.items() if it.type == "vocab" and not k.startswith("open-alphabet/")][:3]
    with conn:
        for k in words:
            scheduler.record(conn, k, "vocab", False, 0.0)
            conn.execute("INSERT INTO attempts(session_id, item_key, ts, response_json, score, correct) "
                         "VALUES (NULL, ?, ?, '{}', 0, 0)", (k, db.now()))
    tomorrow = db.today() + timedelta(days=1)
    m = material(conn, catalog, "daily", tomorrow, {"ui_lang": "tr"})
    conn.close()
    assert m["id"] == f"daily.{tomorrow.isoformat()}.tr" and m["lang"] == "tr" and m["exists"] is False
    assert {w["key"] for w in m["due"]} == set(words)
    assert all(w["meaning"] and w["lapses"] == 1 for w in m["due"])
    assert {x["key"] for x in m["mistakes"]} <= set(words) and m["mistakes"]
    assert {w["key"] for w in m["new"]} == set(words)
    assert m["previous"] == []
    assert cli.main(["podcast", "material", "weekly"]) == 0
    assert json.loads(capsys.readouterr().out)["id"].startswith("weekly.")
    assert cli.main(["podcast", "material", "monthly"]) == 1
