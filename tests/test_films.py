"""The films of the Oknos myth in the app: served from docs/brand/animations/, the films page's
data, and the welcome film that plays once on first launch."""

import json
import shutil
import sqlite3

import pytest

from oknos import films, paths


def test_the_films_are_served_from_their_one_folder(client):
    for f in films.FILMS:
        r = client.get(f"/films/{f}.html")
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
        assert 'src="film.js"' in r.text and "fonts.googleapis" not in r.text  # the web font only outside the app
    js = client.get("/films/film.js")
    assert js.status_code == 200 and "javascript" in js.headers["content-type"] and "embed" in js.text
    assert client.get("/films/anim.css").headers["content-type"].startswith("text/css")
    pic = client.get("/films/frames/f1-01.webp")
    assert pic.status_code == 200 and pic.headers["content-type"] == "image/webp"
    assert client.head("/films/voice/f1-01.mp3").headers["content-type"] == "audio/mpeg"
    assert client.get("/films/ambience/f1.mp3").status_code == 200
    # one source of truth: no copies in web/
    assert not list(paths.WEB_DIR.rglob("*.webp")) and not (paths.WEB_DIR / "films").exists()


@pytest.mark.parametrize("name", [
    "README.md", "../../../pyproject.toml", "frames/../README.md", "voice/f1-01.wav", "frames/f1-01.mp3",
    "other/f1-01.webp", "4-no-such-film.html", "voice/no-such-clip.mp3", "frames/sub/f1-01.webp",
    # film 2 is archived: its files stay in docs/brand/animations/, the app does not serve them
    "2-oknos-and-his-wife.html", "frames/f2-01.webp", "voice/f2-01.mp3", "ambience/f2.mp3",
])
def test_only_the_films_files_are_served(client, name):
    assert client.get(f"/films/{name}").status_code == 404


def test_the_films_list(client):
    data = client.get("/api/films").json()
    assert [f["n"] for f in data["films"]] == [1, 3]  # film 2 is archived
    assert data["films"][1]["poster"] == "/films/frames/f3-01.webp"
    assert all(f["available"] for f in data["films"])
    assert data["films"][0] == {"n": 1, "id": "1-oknos-and-the-donkey", "available": True,
                                "poster": "/films/frames/f1-01.webp"}
    assert data["voice"] in ("voice", "voice-local")  # the tracked clips at least


@pytest.fixture
def film_copy(tmp_path, monkeypatch):
    """A copy of the films folder without voice-local/ (as on a fresh clone), to change freely."""
    d = tmp_path / "animations"
    shutil.copytree(paths.FILMS_DIR, d, ignore=shutil.ignore_patterns("voice-local"))
    monkeypatch.setattr(films, "films_dir", lambda: d)
    return d


def test_voice_local_is_played_when_it_is_there_else_voice(client, film_copy):
    assert client.get("/api/films").json()["voice"] == "voice"
    assert client.get("/films/voice-local/f1-01.mp3").status_code == 404
    (film_copy / "voice-local").mkdir()
    shutil.copy(film_copy / "voice" / "f1-01.mp3", film_copy / "voice-local" / "f1-01.mp3")
    assert client.get("/api/films").json()["voice"] == "voice-local"
    assert client.get("/films/voice-local/f1-01.mp3").status_code == 200
    shutil.rmtree(film_copy / "voice-local")
    shutil.rmtree(film_copy / "voice")
    assert client.get("/api/films").json()["voice"] is None  # silent, as before


def test_the_welcome_film_once_for_a_new_learner(client, learner):
    assert client.get("/api/home").json()["welcome_film"] is True
    r = client.post("/api/films/welcome", json={"how": "skipped"})
    assert r.status_code == 200 and r.json()["how"] == "skipped"
    seen = json.loads((learner / "profile.json").read_text(encoding="utf-8"))[films.PROFILE_KEY]
    assert seen == r.json()[films.PROFILE_KEY]
    assert client.get("/api/home").json()["welcome_film"] is False
    # a second call keeps the first date, and other profile keys are kept
    client.post("/api/profile", json={"ui_lang": "tr"})
    client.post("/api/films/welcome", json={"how": "ended"})
    profile = json.loads((learner / "profile.json").read_text(encoding="utf-8"))
    assert profile[films.PROFILE_KEY] == seen and profile["ui_lang"] == "tr"
    assert client.post("/api/films/welcome", json={"how": "maybe"}).status_code == 422


def test_ending_the_welcome_film_also_counts(client):
    assert client.post("/api/films/welcome", json={}).json()["how"] == "ended"
    assert client.get("/api/home").json()["welcome_film"] is False


def test_no_welcome_for_a_learner_who_has_used_the_app(client, learner):
    conn = sqlite3.connect(learner / "oknos.db")
    conn.execute("INSERT INTO chapter_reads (curriculum, stage, opened_at) VALUES ('c', 's', '2026-11-23')")
    conn.commit()
    conn.close()
    assert client.get("/api/home").json()["welcome_film"] is False


def test_no_welcome_and_no_films_when_the_files_are_missing(client, film_copy):
    (film_copy / "1-oknos-and-the-donkey.html").unlink()
    assert client.get("/api/home").json()["welcome_film"] is False
    data = client.get("/api/films").json()
    assert [f["available"] for f in data["films"]] == [False, True]
    shutil.rmtree(film_copy)
    assert client.get("/api/home").status_code == 200  # the app stays usable
    assert not any(f["available"] for f in client.get("/api/films").json()["films"])
    assert client.get("/films/film.js").status_code == 404


def test_the_profile_check_accepts_the_welcome_flag():
    from oknos import coachfiles

    p = coachfiles.Profile.model_validate({"ui_lang": "en", films.PROFILE_KEY: "2026-11-23"})
    assert p.welcome_film_seen == "2026-11-23"


def test_the_app_has_the_films_screen_and_its_words():
    js = (paths.WEB_DIR / "app.js").read_text(encoding="utf-8")
    assert "films: (n) => renderFilms(n)" in js and "showWelcome" in js
    keys = ["films_title", "films_lede", "film_1", "film_2", "film_3", "film_1_line", "film_2_line", "film_3_line",
            "films_link_coach", "films_link_book", "welcome_title", "welcome_skip", "welcome_start", "welcome_watch"]
    for lang in ("en", "tr"):
        strings = json.loads((paths.WEB_DIR / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))
        assert all(strings.get(k) for k in keys), lang
