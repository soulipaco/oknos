"""Phase 10: speech made ahead of time, by the first provider in the learner's list that works."""

import json

import pytest

from oknos import voice


class Fake(voice.Provider):
    """A provider that records what it was asked and can be told to refuse or be unready."""

    def __init__(self, name, *, refuse=False, problem=None, free=None, interval=0.0):
        super().__init__(name, {"f": f"{name}-f", "m": f"{name}-m"}, free, min_interval=interval, label=name)
        self.refuse, self.problem, self.calls = refuse, problem, []

    def ready(self, keys, profile):
        return self.problem

    def make(self, text, role, keys):
        self.calls.append((text, role))
        if self.refuse:
            raise voice.Refused("no")
        return f"{self.name}:{role}:{text}".encode() + b"\0" * 1200


def test_a_text_is_cached_once_whatever_its_case_or_spacing(learner):
    assert voice.key("Καλημέρα!", "f") == voice.key("  καλημέρα!\n", "f")
    assert voice.key("Καλημέρα!", "f") != voice.key("Καλημέρα!", "m")
    assert voice.file_for("Καλημέρα", "f").parent.parent.parent == learner / "voice"


def test_the_first_provider_that_works_makes_the_clip(learner):
    a, b, c = Fake("a", problem="needs a key"), Fake("b", refuse=True), Fake("c")
    who = voice.make("Γεια σου.", "m", chain=[a, b, c], keys={}, profile={})
    assert who == "c" and not a.calls and b.calls == [("Γεια σου.", "m")]
    assert voice.file_for("Γεια σου.", "m").read_bytes().startswith(b"c:m:")
    assert voice.usage()["c"] == len("Γεια σου.")


def test_nobody_can_make_it_and_the_browser_voice_stays(learner):
    assert voice.make("Γεια.", "f", chain=[Fake("a", refuse=True)], keys={}, profile={}) is None
    assert not voice.file_for("Γεια.", "f").exists()


def test_a_free_quota_is_left_at_ninety_percent(learner):
    capped, other = Fake("capped", free=100), Fake("other")
    voice._add_usage("capped", 85)
    assert voice.make("Καλημέρα σας!", "f", chain=[capped, other], keys={}, profile={}) == "other"
    assert not capped.calls


def test_a_long_wait_passes_the_clip_on_and_a_short_one_is_waited_out(learner):
    slow, quick = Fake("slow", interval=60), Fake("quick")
    assert voice.make("ένα", "f", chain=[slow, quick], keys={}, profile={}) == "slow"
    assert voice.make("δύο", "f", chain=[slow, quick], keys={}, profile={}) == "quick"
    paced = Fake("paced", interval=0.2)
    assert voice.make("τρία", "f", chain=[paced, quick], keys={}, profile={}) == "paced"
    assert voice.make("τέσσερα", "f", chain=[paced, quick], keys={}, profile={}) == "paced"


def test_who_speaks_decides_the_voice():
    assert voice.role_of("Ζεϊνέπ") == "f" and voice.role_of("Γιώργος") == "m"
    assert voice.role_of("Ο διαχειριστής") == "m" and voice.role_of("Πέτρος") == "m"
    assert voice.role_of("Μαρία") == "f" and voice.role_of(None) == "f"


def test_edge_gets_a_word_it_refuses_without_the_accent():
    assert voice.soften("Είστε η κυρία Ζεϊνέπ;") == "Είστε η κυρία Ζεϊνεπ;"
    assert voice.soften("Καλημέρα!") == "Καλημέρα!"


def test_a_hung_edge_connection_fails_the_clip_and_the_next_provider_makes_it(learner, monkeypatch):
    edge_tts = pytest.importorskip("edge_tts")
    import asyncio
    import time

    class Hangs:
        def __init__(self, *a, **k):
            pass

        async def stream(self):
            await asyncio.sleep(3600)
            yield {"type": "audio", "data": b""}

    monkeypatch.setattr(edge_tts, "Communicate", Hangs)
    monkeypatch.setattr(voice.time, "sleep", lambda s: None)
    edge = voice.providers()["edge"]
    edge.timeout = 0.2
    other = Fake("other")
    start = time.monotonic()
    assert voice.make("Καλημέρα.", "f", chain=[edge, other], keys={}, profile={"edge_tts_ok": True}) == "other"
    assert time.monotonic() - start < 5


def test_keys_come_from_the_learner_folder_and_never_show(learner, monkeypatch):
    learner.mkdir(parents=True, exist_ok=True)
    (learner / "secrets.env").write_text("# keys\nGOOGLE_TTS_API_KEY=AIza-secret\nOPENAI_API_KEY=\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")
    keys = voice.secrets()
    assert keys["GOOGLE_TTS_API_KEY"] == "AIza-secret" and keys["OPENAI_API_KEY"] == "sk-from-env"
    shown = json.dumps(voice.status())
    assert "AIza-secret" not in shown and "sk-from-env" not in shown
    google = next(p for p in voice.status()["providers"] if p["name"] == "google")
    assert google["problem"] is None


def test_build_makes_what_is_missing_and_remembers_who_made_it(catalog, monkeypatch):
    fake = Fake("google")
    monkeypatch.setattr(voice, "providers", lambda: {"google": fake})
    pairs = voice.texts(catalog)
    assert len(pairs) > 50 and all(r in voice.ROLES for _, r in pairs)
    result = voice.build(catalog, limit=5, pause=0)
    assert result["made"] == {"google": 5} and len(fake.calls) == 5
    again = voice.build(catalog, limit=5, pause=0)  # the first five exist now: the next five are made
    assert again["made"] == {"google": 5} and fake.calls[5] != fake.calls[0]
    assert sum(1 for v in voice.read_index().values() if v["p"] == "google") == 10


def test_the_app_serves_a_made_clip_and_404_otherwise(client, learner):
    target = voice.file_for("Καλημέρα!", "m")
    target.parent.mkdir(parents=True)
    target.write_bytes(b"ID3" + b"\0" * 2000)
    r = client.get("/voice", params={"r": "m", "t": "καλημέρα!"})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg"
    assert client.get("/voice", params={"r": "f", "t": "Καλημέρα!"}).status_code == 404
    assert client.get("/voice", params={"r": "x", "t": "Καλημέρα!"}).status_code == 404
    st = client.get("/api/voice").json()
    assert {"order", "providers", "files"} <= set(st)


@pytest.mark.parametrize("bad", ["", "   "])
def test_an_empty_text_finds_nothing(client, bad):
    assert client.get("/voice", params={"r": "f", "t": bad}).status_code == 404


def test_a_speaker_keeps_one_voice_family_while_it_can(catalog, monkeypatch):
    """Microsoft refuses a clip now and then (throttling): it is tried again before Google steps in."""
    class Flaky(Fake):
        def make(self, text, role, keys):
            self.calls.append((text, role))
            if len(self.calls) % 2:  # every other first try is refused
                raise voice.Refused("busy")
            return b"edge" + b"\0" * 1200

    edge, google = Flaky("edge"), Fake("google")
    edge.family, google.family = "microsoft", "google"
    monkeypatch.setattr(voice, "providers", lambda: {"edge": edge, "google": google})
    learner_profile = {"voice": {"providers": ["edge", "google"]}}
    monkeypatch.setattr(voice, "read_profile", lambda: learner_profile)
    result = voice.build(catalog, limit=6, pause=0)
    assert result["made"] == {"edge": 6} and result["failed"] == 0 and not google.calls


def test_the_coachs_own_texts_never_go_to_the_free_edge_route(learner):
    edge, google = Fake("edge"), Fake("google")
    assert voice.make("Η σπιτονοικοκυρά σου λέει…", "f", chain=[edge, google], keys={}, profile={}, own=True) == "google"
    assert not edge.calls
