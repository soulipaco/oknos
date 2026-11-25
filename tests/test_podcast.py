"""Phase 11: podcast lessons, written as a script, checked, and joined into one file (docs/PODCASTS.md)."""

import base64
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


def test_a_connection_cut_halfway_is_tried_again_then_refused(monkeypatch):
    import http.client

    calls = []

    class Cut:
        def read(self):
            calls.append(1)
            if len(calls) == 1:
                raise http.client.IncompleteRead(b"abc")
            return b"ID3 audio"

    monkeypatch.setattr(voice.time, "sleep", lambda s: None)
    monkeypatch.setattr(voice.urllib.request, "urlopen", lambda req, timeout: Cut())
    assert voice._post("https://example.invalid/", b"x", {}) == b"ID3 audio" and len(calls) == 2

    class AlwaysCut:
        def read(self):
            raise http.client.IncompleteRead(b"")

    monkeypatch.setattr(voice.urllib.request, "urlopen", lambda req, timeout: AlwaysCut())
    with pytest.raises(voice.Refused, match="IncompleteRead"):
        voice._post("https://example.invalid/", b"x", {})


# ---------- the cast (format v2) ----------

CAST = [
    {"id": "ada", "name": "Ada", "role": "host", "lang": ["tr"], "gender": "f", "age": "35", "manner": "warm"},
    {"id": "mert", "name": "Mert", "role": "cohost", "lang": ["tr", "el"], "gender": "m"},
    {"id": "katerina", "name": "Κατερίνα", "role": "guest", "lang": ["el"], "gender": "f"},
]


def test_a_cast_gives_each_speaker_a_voice_by_gender_and_checks_their_languages(learner):
    raw = script(cast=CAST, segments=[
        {"part": "Giriş"},
        {"lang": "tr", "say": "Hoş geldin!", "who": "ada"},
        {"lang": "tr", "say": "Merhaba Ada.", "who": "mert"},
        {"lang": "el", "say": "Στον Πειραιά.", "who": "katerina"},
        {"lang": "el", "say": "Στον Πειραιά.", "who": "mert"},
    ])
    write(learner, raw)
    assert podcast.check("open.first-words.tr")["problems"] == []
    got = {(t, r, lang) for t, r, lang in podcast.lines(podcast.load("open.first-words.tr"))}
    assert ("Merhaba Ada.", "m", "tr") in got and ("Hoş geldin!", "f", "tr") in got
    assert ("Στον Πειραιά.", "f", "el") in got and ("Στον Πειραιά.", "m", "el") in got

    raw["segments"] += [{"lang": "tr", "say": "Merhaba.", "who": "katerina"}, {"lang": "el", "say": "Γεια!", "who": "nikos"}]
    write(learner, raw)
    problems = podcast.check("open.first-words.tr")["problems"]
    assert any("does not speak tr" in p for p in problems) and any("'nikos' is not in the cast" in p for p in problems)


def test_a_cast_member_needs_a_known_role_gender_and_id():
    for bad in ({"gender": "x"}, {"role": "singer"}, {"id": "Ada K"}, {"lang": []}):
        with pytest.raises(podcast.PodcastError):
            podcast.parse(script(cast=[{**CAST[0], **bad}]))


# ---------- the voices of a cast episode (docs/PODCASTS.md "The voices") ----------

from oknos import casting  # noqa: E402

SCENE = CAST + [
    {"id": "ayse", "name": "Αϊσέ", "role": "character", "lang": ["el"], "gender": "f", "age": "30", "manner": "shy"},
    {"id": "nikos", "name": "Νίκος", "role": "character", "lang": ["el"], "gender": "m"},
]


def cast_script(**over):
    return script(cast=SCENE, segments=[
        {"part": "Sahne"},
        {"lang": "el", "say": "Γεια σου, Αϊσέ! Πού μένεις;", "who": "nikos"},
        {"lang": "el", "say": "Μένω στην Κυψέλη. Εσύ;", "who": "ayse"},
        {"lang": "el", "say": "Εγώ μένω στο Παγκράτι.", "who": "nikos"},
        {"part": "Konuşma"},
        {"lang": "tr", "say": "Ada, bir şey soracağım.", "who": "mert"},
        {"lang": "tr", "say": "Sor bakalım.", "who": "ada"},
        {"lang": "tr", "say": "Neden bazen ston, bazen stin?", "who": "mert"},
        {"lang": "el", "say": "Στον Πειραιά.", "who": "katerina"},
        {"lang": "el", "say": "Στον Πειραιά.", "who": "katerina", "speed": 0.8},
        {"echo": 1.2},
        {"lang": "tr", "say": "Evet dediğimde, yani Ναι dediğimde, herkes güldü.", "who": "mert"},
        {"pause": 1},
    ], **over)


class Actor(voice.Provider):
    """A service like Gemini: named voices, two speakers in one request, Greek inside Turkish."""

    named = dialogue = mixed = True

    def __init__(self, name="gemini"):
        super().__init__(name, {"f": "Kore", "m": "Orus"}, None, label=name, family="google",
                         lang_voices={"tr": {"f": "Kore", "m": "Orus"}, "en": {"f": "Kore", "m": "Orus"}})
        self.calls = []

    def ready(self, keys, profile):
        return None

    def make(self, text, role, keys, lang="el", voice_name=None, style=None):
        self.calls.append(("one", (voice_name,), (text,), style))
        return tone(1.0)

    def make_exchange(self, turns, keys):
        self.calls.append(("two", tuple(t[1] for t in turns), tuple(t[2] for t in turns), turns[0][3]))
        return tone(0.8 * len(turns))


class Reader(Actor):
    """A service like Chirp 3 HD: named voices, but one line at a time and no Greek inside Turkish."""

    dialogue = mixed = False

    def __init__(self):
        super().__init__("google")


def test_the_show_keeps_its_voices_and_no_two_people_share_one():
    script_ = podcast.parse(cast_script())
    members, _ = casting.speakers(script_)
    voices = casting.assign(members, "google")
    show = casting.table()["families"]["google"]["show"]
    assert voices["ada"] == show["ada"] and voices["mert"] == show["mert"] and voices["katerina"] == show["katerina"]
    assert len(set(voices.values())) == len(voices)
    pool = casting.table()["families"]["google"]["voices"]
    assert pool[voices["ayse"]][0] == "f" and pool[voices["nikos"]][0] == "m"
    # The same character gets the same voice in another episode with other people.
    other = podcast.parse(script(cast=[SCENE[3], {**SCENE[4], "id": "x", "name": "Γιάννης"}],
                                 segments=[{"part": "A"}, {"lang": "el", "say": "Γεια!", "who": "ayse"},
                                           {"lang": "el", "say": "Γεια!", "who": "x"}]))
    assert casting.assign(casting.speakers(other)[0], "google")["ayse"] == voices["ayse"]
    # A script may choose a voice itself; a provider with no pool gets none.
    chosen = podcast.parse(script(cast=[{**SCENE[3], "voice": {"google": "Leda"}}],
                                  segments=[{"part": "A"}, {"lang": "el", "say": "Γεια!", "who": "ayse"},
                                            {"lang": "el", "say": "Καλημέρα!", "who": "ayse"}]))
    assert casting.assign(casting.speakers(chosen)[0], "google")["ayse"] == "Leda"
    assert casting.assign(members, casting.family_of("azure")) == {}


def test_more_people_than_voices_of_a_gender_share_only_then():
    many = [{"id": f"w{i}", "name": f"Γυναίκα {i}", "role": "character", "lang": ["el"], "gender": "f"} for i in range(16)]
    segs = [{"part": "A"}] + [{"lang": "el", "say": "Γεια!", "who": m["id"]} for m in many]
    voices = casting.assign(casting.speakers(podcast.parse(script(cast=many, segments=segs)))[0], "google")
    free = sum(1 for g, _ in casting.table()["families"]["google"]["voices"].values() if g == "f") - 2  # Ada, Katerina
    assert len(set(voices.values())) == free and len(voices) == 16


def test_older_scripts_get_the_host_the_guest_and_their_characters():
    members, who_of = casting.speakers(podcast.parse(script()))
    assert who_of[1] == "ada"                      # a Turkish line with no speaker: the host
    assert members[who_of[3]].name == "Κατερίνα" and members[who_of[3]].role == "character"
    assert members[who_of[6]].gender == "m"        # Γιώργος


def test_lines_between_two_people_are_one_request_and_a_third_voice_or_a_gap_starts_another():
    s = podcast.parse(cast_script())
    _, who_of = casting.speakers(s)
    units = [u for u in podcast.plan(s, who_of) if isinstance(u, podcast.Unit)]
    # A service that acts dialogue: Katerina (a third voice) starts a new request; her slowed line
    # stays in it (asked to be slow), and the echo gap after it ends it.
    assert [sorted(u.ids()) for u in units] == [["ayse", "nikos"], ["ada", "mert"], ["katerina"], ["mert"]]
    assert [len(u.lines) for u in units] == [3, 3, 2, 1] and not any(u.solo for u in units)
    # A service that reads line by line: the slowed, echoed line is made on its own.
    fine = [u for u in podcast.plan(s, who_of, acts=False) if isinstance(u, podcast.Unit)]
    assert [len(u.lines) for u in fine] == [3, 3, 1, 1, 1] and fine[3].solo


def test_greek_inside_turkish_is_a_note_for_a_speaker_who_speaks_greek_else_a_problem(learner):
    write(learner, cast_script())
    c = podcast.check("open.first-words.tr")
    assert c["problems"] == [] and any("Greek inside a tr line" in n for n in c["notes"])
    raw = cast_script()
    raw["segments"][11]["who"] = "ada"  # Ada speaks Turkish only in this cast
    write(learner, raw)
    assert any("Greek letters inside a tr line" in p for p in podcast.check("open.first-words.tr")["problems"])


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg joins the clips")
def test_a_cast_episode_is_acted_in_exchanges_with_its_voices_and_the_jingle(learner, monkeypatch):
    actor = Actor()
    monkeypatch.setattr(podcast, "_chain", lambda profile, keys: [actor])
    write(learner, cast_script())
    assert podcast.check("open.first-words.tr")["cost"]["by_provider"]["gemini"]["tokens"] > 0
    meta = podcast.render("open.first-words.tr")
    show = casting.table()["families"]["google"]["show"]
    kinds = [c[0] for c in actor.calls]
    assert kinds == ["two", "two", "one", "one", "one"]  # Katerina's slow repeat: its own pace, its own request
    assert "slowly" in actor.calls[3][3] and "slowly" not in actor.calls[2][3]
    assert actor.calls[1][1] == (show["mert"], show["ada"], show["mert"])
    assert "Mert" in actor.calls[1][3]  # each line carries its speaker's style
    assert actor.calls[4][2] == ("Evet dediğimde, yani Ναι dediğimde, herkes güldü.",)
    assert meta["cast"]["ada"]["voice"] == show["ada"] and meta["sounds"] is True
    assert [p["title"] for p in meta["parts"]] == ["Sahne", "Konuşma"] and meta["parts"][0]["t"] > 2  # after the jingle
    assert len(meta["lines"]) == 9 and [x["t"] for x in meta["lines"]] == sorted(x["t"] for x in meta["lines"])
    speech = 0.8 * (3 + 3 + 2) + 1.25 + 1.0
    assert meta["seconds"] > speech + 5  # the jingle, the sting, the close, the gaps
    # A second render spends nothing; prune keeps the clips an episode lists.
    again = podcast.render("open.first-words.tr")
    assert again["chars"] == {} and len(actor.calls) == 5
    assert podcast.prune()["clips"] == 0 and all(podcast.cast_clip(k).is_file() for k in again["clips"])


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg joins the clips")
def test_a_service_without_dialogue_reads_line_by_line_and_cannot_say_mixed_lines(learner, monkeypatch):
    reader = Reader()
    monkeypatch.setattr(podcast, "_chain", lambda profile, keys: [reader])
    raw = cast_script()
    raw["segments"] = raw["segments"][:11]
    write(learner, raw)
    meta = podcast.render("open.first-words.tr")
    assert {c[0] for c in reader.calls} == {"one"} and len(reader.calls) == 7  # the slow repeat reuses its clip
    assert meta["cast"]["nikos"]["voice"] != meta["cast"]["mert"]["voice"]
    write(learner, cast_script())
    with pytest.raises(podcast.PodcastError, match="mixed lines"):
        podcast.render("open.first-words.tr")


def test_the_podcast_has_its_own_list_and_gemini_never_makes_the_apps_clips(learner):
    assert "gemini" in voice.podcast_providers() and "gemini" not in voice.providers()
    chain = podcast._chain({"voice": {"providers": ["azure"]}, "podcast": {"providers": ["gemini", "google"]}}, {})
    assert [p.name for p in chain] == ["gemini", "google"]
    assert [p.name for p in podcast._chain({"voice": {"providers": ["azure"]}}, {})] == ["azure"]


def test_gemini_asks_for_each_speaker_by_name_and_keeps_the_style_out_of_the_spoken_text(learner, monkeypatch):
    sent = []

    def fake_post(url, body, headers, timeout=60, tries=2):
        sent.append(json.loads(body))
        pcm = base64.b64encode(b"\x00\x01" * 2400).decode()
        return json.dumps({"candidates": [{"content": {"parts": [{"inlineData": {
            "mimeType": "audio/L16;codec=pcm;rate=24000", "data": pcm}}]}}],
            "usageMetadata": {"candidatesTokenCount": 7}}).encode()

    monkeypatch.setattr(voice, "_post", fake_post)
    g = voice.podcast_providers()["gemini"]
    keys = {"GEMINI_API_KEY": "k"}
    wav = g.make_exchange([("ada", "Sulafat", "Merhaba!", "warm"), ("mert", "Umbriel", "Selam.", "easy")], keys)
    assert wav[:4] == b"RIFF" and g.tokens == 7
    parts = sent[0]["contents"][0]["parts"]
    assert [p["speechMetadata"]["speaker"] for p in parts] == ["ada", "mert"] and parts[0]["text"] == "Merhaba!"
    voices = sent[0]["generationConfig"]["speechConfig"]["multiSpeakerVoiceConfig"]["speakerVoiceConfigs"]
    assert {v["speaker"]: v["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"] for v in voices} == {
        "ada": "Sulafat", "mert": "Umbriel"}
    g.make("Στον Πειραιά.", "f", keys, lang="el", voice_name="Gacrux", style="patient")
    assert sent[1]["contents"][0]["parts"][0] == {"text": "Στον Πειραιά.", "speechMetadata": {"style": "patient"}}
    with pytest.raises(ValueError):
        g.make_exchange([("a", "A", "1", None), ("b", "B", "2", None), ("c", "C", "3", None)], keys)


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg joins the clips")
def test_one_service_voices_the_whole_episode_and_a_refusal_stops_it_without_mixing(learner, monkeypatch):
    class Tired(Actor):
        def make_exchange(self, turns, keys):
            if len(self.calls) >= 1:
                raise voice.Refused("429 Too Many Requests")
            return super().make_exchange(turns, keys)

    tired, reader = Tired(), Reader()
    monkeypatch.setattr(podcast, "_chain", lambda profile, keys: [tired, reader])
    write(learner, cast_script())
    with pytest.raises(podcast.PodcastError, match="gemini refused"):
        podcast.render("open.first-words.tr")
    assert reader.calls == [] and len(tired.calls) == 1  # the first exchange is kept for the next try


def test_gemini_waits_and_asks_again_after_a_429(learner, monkeypatch):
    answers = [voice.Refused("429 Too Many Requests"), voice.Refused("503 Unavailable")]
    pcm = base64.b64encode(b"\x00\x01" * 2400).decode()

    def fake_post(url, body, headers, timeout=60, tries=2):
        if answers:
            raise answers.pop(0)
        return json.dumps({"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "audio/L16;rate=24000",
                                                                                  "data": pcm}}]}}]}).encode()

    slept = []
    monkeypatch.setattr(voice, "_post", fake_post)
    monkeypatch.setattr(voice.time, "sleep", slept.append)
    assert voice.podcast_providers()["gemini"].make("Γεια!", "f", {"GEMINI_API_KEY": "k"})[:4] == b"RIFF"
    assert slept == [15, 30]
    monkeypatch.setattr(voice, "_post", lambda *a, **k: (_ for _ in ()).throw(voice.Refused("400 Bad Request")))
    with pytest.raises(voice.Refused, match="400"):
        voice.podcast_providers()["gemini"].make("Γεια!", "f", {"GEMINI_API_KEY": "k"})


def test_gemini_stops_at_once_when_the_days_requests_are_used_up(learner, monkeypatch):
    def fake_post(url, body, headers, timeout=60, tries=2):
        raise voice.Refused("429 Too Many Requests {quotaId: GenerateRequestsPerDayPerProjectPerModel}")

    slept = []
    monkeypatch.setattr(voice, "_post", fake_post)
    monkeypatch.setattr(voice.time, "sleep", slept.append)
    with pytest.raises(voice.Refused, match="daily limit"):
        voice.podcast_providers()["gemini"].make("Γεια!", "f", {"GEMINI_API_KEY": "k"})
    assert slept == []


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg joins the clips")
def test_an_episode_that_does_not_fit_the_days_gemini_requests_goes_whole_to_the_fallback(learner, monkeypatch):
    actor, reader = Actor(), Reader()
    monkeypatch.setattr(podcast, "_chain", lambda profile, keys: [actor, reader])
    raw = cast_script()
    raw["segments"] = raw["segments"][:11]  # no Greek inside Turkish: the fallback can say all of it
    write(learner, raw)
    voice._add_usage(f"gemini_requests_{voice.quota_day()}", podcast.GEMINI_DAILY_REQUESTS - 2)
    cost = podcast.check("open.first-words.tr")["cost"]
    assert list(cost["by_provider"]) == ["google"]
    meta = podcast.render("open.first-words.tr")
    assert actor.calls == [] and set(meta["made"]) == {"google"}


# ---------- ElevenLabs v4 (chosen by the maintainer on 2026-11-25) ----------

class Eleven(Actor):
    """A service like ElevenLabs v4: up to ten people in one request, the pace as an audio tag."""

    max_speakers = 10
    max_chars = 2000
    style_kind = "tags"

    def __init__(self, left=None):
        voice.Provider.__init__(self, "elevenlabs", {"f": "Crhysa", "m": "Christos"}, None, label="elevenlabs",
                                family="elevenlabs", lang_voices={"tr": {"f": "Gozde", "m": "Arman"}})
        self.calls = []
        self.left = left

    def credits_left(self, keys):
        return self.left


def test_elevenlabs_gives_a_greek_character_a_greek_voice_of_their_age():
    members, _ = casting.speakers(podcast.parse(cast_script()))
    members["clerk"] = casting.Member("clerk", "Υπάλληλος", "character", "m", {"el"}, "50", "polite, brisk")
    voices = casting.assign(members, "elevenlabs")
    fam = casting.table()["families"]["elevenlabs"]
    assert {k: voices[k] for k in ("ada", "mert", "katerina")} == fam["show"]
    assert len(set(voices.values())) == len(voices)
    for mid in ("ayse", "nikos", "clerk"):
        assert casting.entry("elevenlabs", voices[mid])["lang"] == "el"
    assert casting.entry("elevenlabs", voices["clerk"])["age"] == "middle"
    assert casting.entry("elevenlabs", voices["ayse"])["age"] == "young"  # 30
    assert casting.voice_id("elevenlabs", "Crhysa") == "4hx4668A4ljDTKS4m5oV"
    assert casting.voice_id("google", "Kore") == "Kore"


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg joins the clips")
def test_elevenlabs_acts_more_than_two_people_together_and_slows_a_line_with_a_tag(learner, monkeypatch):
    eleven = Eleven()
    monkeypatch.setattr(podcast, "_chain", lambda profile, keys: [eleven])
    write(learner, cast_script())
    cost = podcast.check("open.first-words.tr")["cost"]
    assert cost["by_provider"]["elevenlabs"]["requests"] == 3
    podcast.render("open.first-words.tr")
    # The scene; the hosts with Katerina (a third voice) in one request, her slow repeat in it with
    # its tag; Mert's line after the echo gap.
    assert [c[0] for c in eleven.calls] == ["two", "two", "one"]
    show = casting.table()["families"]["elevenlabs"]["show"]
    assert eleven.calls[1][1] == (show["mert"], show["ada"], show["mert"], show["katerina"], show["katerina"])
    assert eleven.calls[1][3] is None  # no style on a line at normal pace


def test_elevenlabs_sends_library_ids_and_the_tag_and_waits_when_busy(learner, monkeypatch):
    sent, answers, slept = [], [voice.Refused("429 Too Many Requests")], []

    def fake_post(url, body, headers, timeout=60, tries=2):
        if answers:
            raise answers.pop(0)
        sent.append((url, json.loads(body), headers))
        return b"\x00\x01" * 4800

    monkeypatch.setattr(voice, "_post", fake_post)
    monkeypatch.setattr(voice.time, "sleep", slept.append)
    e = voice.podcast_providers()["elevenlabs"]
    keys = {"ELEVENLABS_API_KEY": "k"}
    wav = e.make_exchange([("ada", "Gozde", "Merhaba!", None), ("katerina", "Crhysa", "Στον Πειραιά.", "[slowly]")], keys)
    assert wav[:4] == b"RIFF" and slept == [5]
    url, body, headers = sent[0]
    assert "text-to-dialogue" in url and "pcm_24000" in url and headers["xi-api-key"] == "k"
    assert body["model_id"] == "eleven_v4"
    assert body["inputs"] == [{"text": "Merhaba!", "voice_id": "aEJD8mYP0nuof1XHShVY"},
                              {"text": "[slowly] Στον Πειραιά.", "voice_id": "4hx4668A4ljDTKS4m5oV"}]
    monkeypatch.setattr(voice, "_post", lambda *a, **k: (_ for _ in ()).throw(
        voice.Refused('401 Unauthorized {"detail":{"status":"quota_exceeded"}}')))
    with pytest.raises(voice.Refused, match="used up"):
        e.make("Γεια!", "f", keys)


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg joins the clips")
def test_an_episode_that_may_not_fit_the_elevenlabs_credits_goes_whole_to_the_fallback(learner, monkeypatch):
    eleven, reader = Eleven(left=50), Reader()
    monkeypatch.setattr(podcast, "_chain", lambda profile, keys: [eleven, reader])
    raw = cast_script()
    raw["segments"] = raw["segments"][:11]  # no Greek inside Turkish: the fallback can say all of it
    write(learner, raw)
    assert list(podcast.check("open.first-words.tr")["cost"]["by_provider"]) == ["google"]
    meta = podcast.render("open.first-words.tr")
    assert eleven.calls == [] and set(meta["made"]) == {"google"}
    eleven.left = None  # the key may not read the credits: try
    write(learner, {**raw, "written": "2026-11-26"})
    assert list(podcast.check("open.first-words.tr")["cost"]["by_provider"]) == ["elevenlabs"]
