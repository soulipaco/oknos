import shutil

import pytest
from fastapi.testclient import TestClient

OPEN_BOOK = "open-book"


@pytest.fixture(autouse=True)
def _real_clock():
    from oknos import db

    db.set_clock(None)
    yield
    db.set_clock(None)


@pytest.fixture(scope="session")
def _open_without_book(tmp_path_factory):
    """The tracked open packs without the open course's book (one read-only copy per test run)."""
    from oknos import paths

    root = tmp_path_factory.mktemp("content") / "open"
    root.mkdir()
    for pack in (paths.CONTENT_DIR / "open").iterdir():
        if pack.is_dir() and pack.name != OPEN_BOOK:
            shutil.copytree(pack, root / pack.name)
    return root


def _roots(monkeypatch, open_root, tmp_path, learner_dir):
    from oknos import paths

    monkeypatch.setattr(paths, "content_roots", lambda: [
        ("open", open_root),
        ("private", tmp_path / "private"),
        ("generated", learner_dir / "generated"),
    ])


@pytest.fixture
def learner(tmp_path, monkeypatch, _open_without_book):
    """A throwaway learner folder, so tests never touch the real learner/.

    Content comes from the tracked open packs only: a private pack on the developer's machine
    (content/private/) must never change what the tests see. The open course's book
    (content/open/open-book) is left out too: its chapters gate every stage (read first, then
    practise), and the session and scheduler tests are about the engine, not about that text.
    Tests of the book itself use the `open_book` fixture.
    """
    path = tmp_path / "learner"
    monkeypatch.setenv("OKNOS_LEARNER_DIR", str(path))
    _roots(monkeypatch, _open_without_book, tmp_path, path)
    return path


@pytest.fixture
def open_book(learner, tmp_path, monkeypatch):
    """The learner folder with all the tracked open packs, the open book included."""
    from oknos import paths

    _roots(monkeypatch, paths.CONTENT_DIR / "open", tmp_path, learner)
    return learner


@pytest.fixture
def client(learner):
    from oknos.server import create_app

    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def catalog(learner):
    from oknos import packs

    return packs.load_all()


@pytest.fixture
def full_catalog(open_book):
    """Every tracked open pack, the open book included: what a fresh clone loads."""
    from oknos import packs

    return packs.load_all()
