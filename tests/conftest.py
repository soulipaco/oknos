import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _real_clock():
    from greek_coach import db

    db.set_clock(None)
    yield
    db.set_clock(None)


@pytest.fixture
def learner(tmp_path, monkeypatch):
    """A throwaway learner folder, so tests never touch the real learner/.

    Content comes from the tracked open packs only: a private pack on the developer's machine
    (content/private/) must never change what the tests see.
    """
    from greek_coach import paths

    path = tmp_path / "learner"
    monkeypatch.setenv("GREEK_COACH_LEARNER_DIR", str(path))
    monkeypatch.setattr(paths, "content_roots", lambda: [
        ("open", paths.CONTENT_DIR / "open"),
        ("private", tmp_path / "private"),
        ("generated", path / "generated"),
    ])
    return path


@pytest.fixture
def client(learner):
    from greek_coach.server import create_app

    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def catalog(learner):
    from greek_coach import packs

    return packs.load_all()
