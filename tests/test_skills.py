"""Each skill has a canonical copy in .agents/skills/ and a Claude Code pointer in .claude/skills/.

The pointer must carry the same name and description and send the agent to the
canonical file (docs/SPEC.md §6).
"""

import re

import pytest

from oknos import paths

CANONICAL = paths.REPO_ROOT / ".agents" / "skills"
POINTERS = paths.REPO_ROOT / ".claude" / "skills"


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", text, re.S)
    assert m, f"{path} has no frontmatter"
    meta = {}
    for line in m.group(1).splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, m.group(2)


def names(root):
    return sorted(p.name for p in root.iterdir() if (p / "SKILL.md").exists())


def test_every_skill_has_both_copies():
    assert names(CANONICAL), "no canonical skills found"
    assert names(CANONICAL) == names(POINTERS)


@pytest.mark.parametrize("name", names(CANONICAL))
def test_pointer_matches_canonical(name):
    canon_meta, canon_body = frontmatter(CANONICAL / name / "SKILL.md")
    pointer_meta, pointer_body = frontmatter(POINTERS / name / "SKILL.md")
    assert canon_meta["name"] == name
    assert pointer_meta["name"] == canon_meta["name"]
    assert pointer_meta["description"] == canon_meta["description"]
    assert f".agents/skills/{name}/SKILL.md" in pointer_body
    assert len(pointer_body) < 600, "the pointer should only point, not duplicate the instructions"
    assert len(canon_body) > 500


def test_agents_md_lists_every_skill():
    agents = (paths.REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for name in names(CANONICAL):
        assert f".agents/skills/{name}/SKILL.md" in agents


def test_the_star_is_asked_only_by_the_coach_and_once():
    """COACHING §7.9: one ask, at a check-in, gated by the report's star.ask_now and recorded in star_asked."""
    coaching = (paths.REPO_ROOT / "docs" / "COACHING.md").read_text(encoding="utf-8")
    assert "### 7.9 The one star ask" in coaching and "`star_asked`" in coaching
    coach = (CANONICAL / "coach" / "SKILL.md").read_text(encoding="utf-8")
    assert "star.ask_now" in coach and "star_asked" in coach
    for name in names(CANONICAL):
        if name != "coach":
            body = (CANONICAL / name / "SKILL.md").read_text(encoding="utf-8")
            assert "star.ask_now" not in body, f"only the coach asks for a star, not {name}"
