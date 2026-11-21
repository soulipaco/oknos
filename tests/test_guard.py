"""Phase 7: git must never publish learner data, private content or a local user path."""

import subprocess

from oknos import guard, paths

B = "\\"


def _repo(tmp_path):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)
    git("init", "-q")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "test")
    (tmp_path / ".gitignore").write_text("learner/\ncontent/private/\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("Install in C:" + B + "Users" + B + "you" + B + "oknos.\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-q", "-m", "start")
    return git


def test_this_repository_tracks_nothing_private():
    assert guard.check(paths.REPO_ROOT) == []
    assert guard.check(paths.REPO_ROOT, "HEAD") == []


def test_a_commit_that_adds_private_content_fails(tmp_path):
    git = _repo(tmp_path)
    assert guard.check(tmp_path) == [] and guard.check(tmp_path, "HEAD") == []
    (tmp_path / "content" / "private" / "book").mkdir(parents=True)
    (tmp_path / "content" / "private" / "book" / "lesson.json").write_text("[]", encoding="utf-8")
    git("add", "-f", "content/private/book/lesson.json")  # forced past .gitignore
    assert any("content/private/" in p for p in guard.check(tmp_path))
    git("commit", "-q", "-m", "oops")
    problems = guard.check(tmp_path, "HEAD")
    assert len(problems) == 1 and problems[0].startswith("content/private/book/lesson.json")


def test_a_local_user_path_fails_and_a_placeholder_does_not(tmp_path):
    git = _repo(tmp_path)
    (tmp_path / "notes.md").write_text(
        "My old project is in C:" + B + "Users" + B + "alice" + B + "Desktop.\n"
        "Fixtures use C:/Users/someone/scan.jpg and /home/you/oknos.\n", encoding="utf-8")
    git("add", "notes.md")
    problems = guard.check(tmp_path)
    assert len(problems) == 1 and problems[0].startswith("notes.md:1:")
    for text, bad in (("/ho" + "me/bob/x", True), ("x/AppData/Local/" + "Temp/claude/1/scratchpad", True),
                      ("the APPDATA folder", False), ("C:" + B + "Users" + B + "…", False)):
        assert bool(guard.USER_PATH.search(text)) == bad, text
