"""Scheduled coach runs (SPEC §6): `greek-coach run <skill>` and `greek-coach schedule ...`.

`run` starts the learner's agent headless on one skill and always records the outcome in
learner/coach/runs.log, so a failed or crashed run shows on the home screen instead of
disappearing. `schedule` writes the operating system's entry that calls `run`, plus
learner/coach/schedule.json, which the app uses to notice runs that stopped happening.

The schedule is standing configuration on the learner's machine: the skills create it only
after the learner says yes.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from greek_coach import coachfiles, db, paths

SKILLS = ("daily-prep", "watch")
TASK_PREFIX = "Greek Coach"
RUN_TIMEOUT_S = 45 * 60
CLAUDE_TOOLS = ("Read", "Write", "Edit", "Glob", "Grep", "WebFetch", "WebSearch",
                "Bash(uv run greek-coach:*)", "Bash(uv run python scripts/:*)",
                "Bash(uv run --group speech greek-coach:*)")


def prompt(skill: str) -> str:
    return (f"Run the {skill} skill: read .agents/skills/{skill}/SKILL.md and follow it. "
            "This is a scheduled run and nobody is watching: never ask a question, skip anything that "
            "needs the learner's answer, and finish with a short summary of what you wrote.")


def find_agent(agent: str) -> str | None:
    """The agent's executable. The official installers put it in ~/.local/bin (Claude Code) or the
    npm folder, which a scheduled task's PATH often lacks, so those are checked too."""
    exe = shutil.which(agent)
    if exe:
        return exe
    home = Path.home()
    names = [f"{agent}.exe", f"{agent}.cmd", agent] if os.name == "nt" else [agent]
    folders = [home / ".local" / "bin", home / ".claude" / "local", Path(os.environ.get("APPDATA", home)) / "npm",
               home / ".npm-global" / "bin", Path("/usr/local/bin"), Path("/opt/homebrew/bin")]
    for folder in folders:
        for name in names:
            if (folder / name).is_file():
                return str(folder / name)
    return None


def agent_command(agent: str, skill: str) -> list[str] | None:
    """The headless command line for an agent, or None if it is not installed."""
    override = os.environ.get("GREEK_COACH_AGENT_CMD")  # tests and unusual installs: a JSON list
    if override:
        return [*json.loads(override), prompt(skill)]
    exe = find_agent(agent)
    if not exe:
        return None
    if agent == "claude":
        return [exe, "-p", prompt(skill), "--permission-mode", "acceptEdits", "--allowedTools", *CLAUDE_TOOLS]
    if agent == "codex":
        return [exe, "exec", "--full-auto", prompt(skill)]
    return None


def run(skill: str, agent: str | None = None, timeout: int = RUN_TIMEOUT_S) -> tuple[bool, str]:
    """Run one skill headless. Always appends a line to runs.log. Returns (ok, detail)."""
    sched = coachfiles.schedule()
    agent = agent or (sched.agent if sched else "claude")
    log_dir = paths.log_dir() / "runs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{db.today().isoformat()}-{skill}.log"
    cmd = agent_command(agent, skill)
    if cmd is None:
        detail = f"the agent '{agent}' was not found on this computer"
        coachfiles.append_run(skill, False, detail)
        return False, detail
    started = time.monotonic()
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", GREEK_COACH_SCHEDULED_RUN=skill)
    with log_file.open("a", encoding="utf-8") as log:
        log.write(f"\n--- {db.now()} {skill} with {agent} ---\n")
        log.flush()
        try:
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            proc = subprocess.run(cmd, cwd=paths.REPO_ROOT, env=env, stdin=subprocess.DEVNULL, stdout=log,
                                  stderr=subprocess.STDOUT, timeout=timeout, creationflags=flags)
            code = proc.returncode
        except subprocess.TimeoutExpired:
            code = "timeout"
        except OSError as e:
            code = f"could not start: {e}"
    minutes = round((time.monotonic() - started) / 60, 1)
    rel = log_file.relative_to(paths.learner_dir()).as_posix()
    ok = code == 0
    detail = f"exit={code} {minutes}min log={rel}"
    if not ok:
        # The agent's last words usually say why ("Not logged in · Please run /login").
        try:
            tail = [l.strip() for l in log_file.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
            if tail and not tail[-1].startswith("---"):
                detail += f" last={tail[-1][:120]}"
        except OSError:
            pass
    coachfiles.append_run(skill, ok, detail)
    return ok, detail


# ---------- the operating system's scheduler ----------

def _python_for_tasks() -> str:
    exe = Path(sys.executable)
    if os.name == "nt":
        w = exe.with_name("pythonw.exe")
        if w.exists():
            return str(w)  # no console window at 05:00
    return str(exe)


def _run_args(skill: str) -> list[str]:
    return [_python_for_tasks(), "-m", "greek_coach", "run", skill]


def task_name(skill: str) -> str:
    return f"{TASK_PREFIX} {skill}"


def _write_schedule(update) -> coachfiles.Schedule:
    current = coachfiles.schedule() or coachfiles.Schedule()
    update(current)
    coachfiles.coach_dir().mkdir(parents=True, exist_ok=True)
    (coachfiles.coach_dir() / "schedule.json").write_text(
        json.dumps(current.model_dump(exclude_none=True), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return current


def add(skill: str, every: str, at: str, day: str | None, agent: str) -> str:
    """Create the OS entry and record it. Returns a plain description of what was created."""
    if skill not in SKILLS:
        raise ValueError(f"only these skills can be scheduled: {', '.join(SKILLS)}")
    task = coachfiles.Task(every=every, at=at, day=day if every == "week" else None, created=db.now())
    args = _run_args(skill)
    if os.name == "nt":
        tr = " ".join(f'"{a}"' if " " in a else a for a in args)
        sc = ["/SC", "DAILY"] if every == "day" else ["/SC", "WEEKLY", "/D", day or "SUN"]
        cmd = ["schtasks", "/Create", "/F", "/TN", task_name(skill), "/TR", tr, *sc, "/ST", at]
        _check(subprocess.run(cmd, capture_output=True, text=True))
        where = f"Windows Task Scheduler task '{task_name(skill)}'"
    elif sys.platform == "darwin":
        where = _launchd_add(skill, args, task)
    else:
        where = _cron_add(skill, args, task)
    _write_schedule(lambda s: (s.tasks.__setitem__(skill, task), setattr(s, "agent", agent)))
    when = f"every day at {at}" if every == "day" else f"every {day or 'SUN'} at {at}"
    return f"{where}: runs `greek-coach run {skill}` {when}"


def remove(skill: str) -> str:
    if os.name == "nt":
        subprocess.run(["schtasks", "/Delete", "/F", "/TN", task_name(skill)], capture_output=True, text=True)
    elif sys.platform == "darwin":
        plist = _plist_path(skill)
        subprocess.run(["launchctl", "unload", str(plist)], capture_output=True)
        plist.unlink(missing_ok=True)
    else:
        _cron_write([l for l in _cron_read() if not l.endswith(f"# greek-coach {skill}")])
    _write_schedule(lambda s: s.tasks.pop(skill, None))
    return f"removed the scheduled {skill} run"


def describe() -> list[str]:
    sched = coachfiles.schedule()
    lines = []
    for skill, task in (sched.tasks.items() if sched else []):
        lines.append(f"{skill}: every {task.every if task.every == 'day' else task.day or 'SUN'} at {task.at} "
                     f"with {sched.agent} (since {task.created})")
        if os.name == "nt":
            q = subprocess.run(["schtasks", "/Query", "/TN", task_name(skill), "/FO", "LIST"],
                               capture_output=True, text=True)
            lines.append("  Windows task: " + ("present" if q.returncode == 0 else "MISSING"))
    return lines or ["nothing is scheduled"]


def _check(proc: subprocess.CompletedProcess) -> None:
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "the scheduler refused").strip())


def _plist_path(skill: str) -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"org.greek-coach.{skill}.plist"


def _launchd_add(skill: str, args: list[str], task: coachfiles.Task) -> str:  # untested (no Mac yet)
    hour, minute = (int(x) for x in task.at.split(":"))
    interval = f"<key>Hour</key><integer>{hour}</integer><key>Minute</key><integer>{minute}</integer>"
    if task.every == "week":
        weekday = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"].index(task.day or "SUN")
        interval += f"<key>Weekday</key><integer>{weekday}</integer>"
    arg_xml = "".join(f"<string>{a}</string>" for a in args)
    plist = _plist_path(skill)
    plist.parent.mkdir(parents=True, exist_ok=True)
    plist.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0"><dict>'
        f"<key>Label</key><string>org.greek-coach.{skill}</string>"
        f"<key>ProgramArguments</key><array>{arg_xml}</array>"
        f"<key>WorkingDirectory</key><string>{paths.REPO_ROOT}</string>"
        f"<key>StartCalendarInterval</key><dict>{interval}</dict></dict></plist>\n", encoding="utf-8")
    subprocess.run(["launchctl", "unload", str(plist)], capture_output=True)
    _check(subprocess.run(["launchctl", "load", str(plist)], capture_output=True, text=True))
    return f"launchd job {plist}"


def _cron_read() -> list[str]:
    proc = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    return proc.stdout.splitlines() if proc.returncode == 0 else []


def _cron_write(lines: list[str]) -> None:
    _check(subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", capture_output=True, text=True))


def _cron_add(skill: str, args: list[str], task: coachfiles.Task) -> str:  # untested (no Linux yet)
    hour, minute = (int(x) for x in task.at.split(":"))
    dow = "*" if task.every == "day" else str(["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"].index(task.day or "SUN"))
    line = f"{minute} {hour} * * {dow} cd '{paths.REPO_ROOT}' && {' '.join(args)} # greek-coach {skill}"
    _cron_write([l for l in _cron_read() if not l.endswith(f"# greek-coach {skill}")] + [line])
    return "crontab entry"
