"""The app was called Greek Coach until 2026-11-21: old names still work, and old files are renamed."""

import sqlite3

from oknos import db, paths


def test_the_old_database_is_renamed_with_its_progress(tmp_path, monkeypatch):
    monkeypatch.setenv("OKNOS_LEARNER_DIR", str(tmp_path))
    old = tmp_path / paths.OLD_DB_NAME
    con = sqlite3.connect(old)
    con.execute("CREATE TABLE kept (x)")
    con.execute("INSERT INTO kept VALUES (42)")
    con.commit()
    con.close()
    assert paths.db_path() == tmp_path / "oknos.db"
    assert not old.exists()
    assert sqlite3.connect(tmp_path / "oknos.db").execute("SELECT x FROM kept").fetchone() == (42,)


def test_a_new_learner_gets_the_new_name(learner):
    db.open_db()
    assert paths.db_path().name == "oknos.db" and paths.db_path().exists()


def test_old_environment_variables_still_work(tmp_path, monkeypatch):
    monkeypatch.delenv("OKNOS_LEARNER_DIR", raising=False)
    monkeypatch.setenv("GREEK_COACH_LEARNER_DIR", str(tmp_path))
    assert paths.learner_dir() == tmp_path.resolve()
    monkeypatch.setenv("OKNOS_LEARNER_DIR", str(tmp_path / "new"))
    assert paths.learner_dir() == (tmp_path / "new").resolve()  # the new name wins
    monkeypatch.setenv("GREEK_COACH_MOCK_SPEED", "30")
    assert paths.env("MOCK_SPEED") == "30"
