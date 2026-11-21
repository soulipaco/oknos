from oknos import db


def test_health_endpoint(client):
    r = client.get("/health").json()
    assert r["app"] == "oknos"
    assert r["ok"] is True
    assert r["greek_roundtrip"] is True
    assert r["greek_sample"] == db.GREEK_SAMPLE
    assert r["schema_version"] == 6
    assert r["items"] >= 20
    assert isinstance(r["pid"], int)


def test_migrations_are_idempotent(learner):
    conn = db.connect()
    assert db.migrate(conn) == 6
    assert db.migrate(conn) == 6
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"meta", "items", "sessions", "attempts", "review_state", "lookups", "flags"} <= tables


def test_cli_health_offline(learner, capsys):
    from oknos.cli import main

    assert main(["health"]) == 0
    out = capsys.readouterr().out
    assert db.GREEK_SAMPLE in out
    assert main(["health", "--server"]) == 1  # nothing is running for this temp learner folder


def test_cli_validate(capsys):
    from oknos import paths
    from oknos.cli import main

    assert main(["validate", str(paths.CONTENT_DIR / "open" / "open-shared-words-tr")]) == 0
    assert "Everything is valid." in capsys.readouterr().out
