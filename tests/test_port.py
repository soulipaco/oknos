"""The app keeps its port across restarts, and says when Tailscale Serve points elsewhere.

None of this needs Tailscale: its status is given as data, or the command is stubbed away."""

import json
import socket
import subprocess

import pytest

from oknos import cli, paths, tailnet

SERVE_8643 = {
    "TCP": {"443": {"HTTPS": True}},
    "Web": {"laptop.example.ts.net:443": {"Handlers": {"/": {"Proxy": "http://127.0.0.1:8643"}}}},
}


def _hold(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((paths.HOST, port))
    s.listen(1)
    return s


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((paths.HOST, 0))
        return s.getsockname()[1]


def test_start_takes_the_port_it_used_last(learner):
    learner.mkdir(parents=True, exist_ok=True)
    port = _free_port()
    cli.remember_port(port)
    assert cli.last_port() == port
    assert cli.choose_port() == port


def test_a_busy_last_port_falls_back_to_the_usual_range(learner):
    learner.mkdir(parents=True, exist_ok=True)
    held = _hold(_free_port())
    try:
        cli.remember_port(held.getsockname()[1])
        port = cli.choose_port()
    finally:
        held.close()
    assert paths.DEFAULT_PORT <= port < paths.DEFAULT_PORT + 20


def test_without_a_record_it_starts_from_8642(learner):
    learner.mkdir(parents=True, exist_ok=True)
    assert cli.last_port() is None
    assert paths.DEFAULT_PORT <= cli.choose_port() < paths.DEFAULT_PORT + 20


def test_a_server_that_was_not_stopped_still_counts(learner):
    """The laptop restarted: only the old .port file is left, and it is the port to keep."""
    learner.mkdir(parents=True, exist_ok=True)
    paths.port_file().write_text("8643", encoding="utf-8")
    assert cli.last_port() == 8643


def test_a_broken_record_is_ignored(learner):
    learner.mkdir(parents=True, exist_ok=True)
    paths.last_port_file().write_text("not a port", encoding="utf-8")
    assert cli.last_port() is None


@pytest.mark.parametrize("target, port", [
    ("http://127.0.0.1:8643", 8643),
    ("http://localhost:8643/", 8643),
    ("127.0.0.1:8650", 8650),
    ("8642", 8642),
    ("http://192.168.1.5:8643", None),
    ("https://example.com", None),
    ("", None),
    (None, None),
])
def test_serve_targets_are_read_as_local_ports(target, port):
    assert tailnet._local_port(target) == port


def test_tcp_forwards_count_too():
    assert tailnet.served_ports({"TCP": {"5000": {"TCPForward": "127.0.0.1:8642"}}}) == [8642]


def test_no_tailscale_no_notes():
    assert tailnet.notes(8642, None) == {"installed": False, "serve_ports": [], "funnel": False, "problems": []}


def test_serve_on_the_apps_port_is_fine():
    n = tailnet.notes(8643, SERVE_8643)
    assert n["serve_ports"] == [8643] and n["problems"] == []


def test_serve_on_another_port_gives_the_one_command():
    [problem] = tailnet.notes(8642, SERVE_8643)["problems"]
    assert "port 8643" in problem and problem.endswith("tailscale serve --bg 8642")
    assert "funnel" not in problem.lower()


def test_no_port_no_mismatch():
    assert tailnet.notes(None, SERVE_8643)["problems"] == []


def test_serve_not_set_up_says_nothing():
    assert tailnet.notes(8642, {})["problems"] == []


def test_funnel_on_is_flagged():
    status = dict(SERVE_8643, AllowFunnel={"laptop.example.ts.net:443": True})
    [problem] = tailnet.notes(8643, status)["problems"]
    assert "Funnel is on" in problem and "tailscale serve reset" in problem


def test_missing_tailscale_reads_as_none():
    assert tailnet.serve_status() is None  # conftest hides any installed Tailscale


@pytest.mark.parametrize("code, out, expected", [
    (0, json.dumps(SERVE_8643), SERVE_8643),
    (0, "", {}),
    (0, "not json", None),
    (1, "", None),  # Tailscale installed but not running or signed out
])
def test_the_status_command_is_read_safely(monkeypatch, code, out, expected):
    monkeypatch.setattr(tailnet, "_exe", lambda: "tailscale")
    seen = []

    def fake_run(cmd, **kw):
        seen.append(cmd)
        return subprocess.CompletedProcess(cmd, code, stdout=out, stderr="")

    monkeypatch.setattr(tailnet.subprocess, "run", fake_run)
    assert tailnet.serve_status() == expected
    assert seen == [["tailscale", "serve", "status", "--json"]]  # read only, never a change


def test_health_shows_no_tailscale_line_without_it(learner, capsys):
    assert cli.main(["health"]) == 0
    assert "Tailscale" not in capsys.readouterr().out


def test_health_json_carries_tailscale(learner, capsys):
    assert cli.main(["health", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["tailscale"]["installed"] is False


def test_health_fails_when_funnel_is_on(learner, monkeypatch, capsys):
    monkeypatch.setattr(tailnet, "serve_status", lambda: dict(SERVE_8643, AllowFunnel={"x:443": True}))
    assert cli.main(["health"]) == 1
    assert "Funnel is on" in capsys.readouterr().out


def test_start_says_how_to_re_point_serve(learner, monkeypatch, capsys):
    monkeypatch.setattr(cli, "running_port", lambda: 8642)
    monkeypatch.setattr(tailnet, "serve_status", lambda: SERVE_8643)
    assert cli.main(["start", "--no-browser"]) == 0
    out = capsys.readouterr().out
    assert "already running" in out and "tailscale serve --bg 8642" in out


def test_start_is_quiet_when_serve_matches(learner, monkeypatch, capsys):
    monkeypatch.setattr(cli, "running_port", lambda: 8643)
    monkeypatch.setattr(tailnet, "serve_status", lambda: SERVE_8643)
    assert cli.main(["start", "--no-browser"]) == 0
    assert "Note:" not in capsys.readouterr().out
