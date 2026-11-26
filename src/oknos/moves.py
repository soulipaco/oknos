"""Content that moved keeps the learner's history (2026-11-26, when the maintainer's private book
became the open Oknos book).

An item moves when a pack's manifest `replaces` another pack (packs.apply_replaces): the old key
`<old pack>/<id>` becomes `<new pack>/<id>`, or the new pack's item with the same word. A
curriculum moves when another names it in `formerly` (curriculum.renames). On every sync the
rows that still carry an old key or curriculum are rewritten; once moved, there is nothing left
to do, so it is cheap and safe to run each time.
"""

from __future__ import annotations

import json
import logging
import sqlite3

log = logging.getLogger("oknos.moves")


def _present(conn: sqlite3.Connection, sql: str, keys: dict[str, str]) -> list[str]:
    return [r[0] for r in conn.execute(sql) if r[0] in keys]


def adopt(conn: sqlite3.Connection, items: dict[str, str], curricula: dict[str, str]) -> dict[str, int]:
    """Rewrite old item keys and curriculum ids to the new ones. Runs inside the caller's
    transaction. Returns how many rows of each kind moved (for tests and the log)."""
    done = {"items": 0, "review_state": 0, "plans": 0, "curricula": 0}
    if items:
        # the old keys that still hold something: once moved, none is left, so a later sync is a no-op
        held: set[str] = set()
        for sql in ("SELECT DISTINCT item_key FROM attempts", "SELECT item_key FROM review_state",
                    "SELECT DISTINCT item_key FROM flags", "SELECT DISTINCT item_key FROM submissions",
                    "SELECT DISTINCT item_key FROM lookups", "SELECT DISTINCT found FROM lookups"):
            held.update(_present(conn, sql, items))
        old_states = set(_present(conn, "SELECT item_key FROM review_state", items))
        for k in sorted(held):
            new = items[k]
            if conn.execute("SELECT 1 FROM items WHERE item_key=?", (new,)).fetchone() is None:
                continue  # the new item is not loaded: nothing to move it to yet
            conn.execute("UPDATE attempts SET item_key=? WHERE item_key=?", (new, k))
            conn.execute("UPDATE flags SET item_key=? WHERE item_key=?", (new, k))
            conn.execute("UPDATE submissions SET item_key=? WHERE item_key=?", (new, k))
            conn.execute("UPDATE lookups SET item_key=? WHERE item_key=?", (new, k))
            conn.execute("UPDATE lookups SET found=? WHERE found=?", (new, k))
            if k in old_states:
                _move_state(conn, k, new)
                done["review_state"] += 1
            done["items"] += 1
        prefixes = {k.split("/", 1)[0] + "/" for k in items}
        for sid, plan in conn.execute("SELECT id, plan_json FROM sessions WHERE plan_json IS NOT NULL").fetchall():
            if not any(p in plan for p in prefixes):
                continue
            cards = json.loads(plan)
            changed = False
            for c in cards if isinstance(cards, list) else []:
                new = items.get(c.get("item_key")) if isinstance(c, dict) else None
                if new and conn.execute("SELECT 1 FROM items WHERE item_key=?", (new,)).fetchone():
                    c["item_key"] = new
                    changed = True
            if changed:
                conn.execute("UPDATE sessions SET plan_json=? WHERE id=?", (json.dumps(cards, ensure_ascii=False), sid))
                done["plans"] += 1
    for old_id, new_id in curricula.items():
        n = 0
        for row in conn.execute("SELECT stage FROM chapter_reads WHERE curriculum=?", (old_id,)).fetchall():
            if conn.execute("SELECT 1 FROM chapter_reads WHERE curriculum=? AND stage=?", (new_id, row[0])).fetchone():
                conn.execute("DELETE FROM chapter_reads WHERE curriculum=? AND stage=?", (old_id, row[0]))
            else:
                conn.execute("UPDATE chapter_reads SET curriculum=? WHERE curriculum=? AND stage=?", (new_id, old_id, row[0]))
            n += 1
        n += conn.execute("UPDATE stage_checks SET curriculum=? WHERE curriculum=?", (new_id, old_id)).rowcount
        prefix = f"chapter:{old_id}/"
        n += conn.execute("UPDATE flags SET item_key=? || substr(item_key, ?) WHERE item_key LIKE ?",
                          (f"chapter:{new_id}/", len(prefix) + 1, prefix + "%")).rowcount
        done["curricula"] += n
    if any(done.values()):
        log.info("moved history: %s", done)
    return done


def _move_state(conn: sqlite3.Connection, old: str, new: str) -> None:
    """The review state goes to the new key; if both have one, the one seen last wins."""
    have = conn.execute("SELECT last_seen_at FROM review_state WHERE item_key=?", (new,)).fetchone()
    if have is None:
        conn.execute("UPDATE review_state SET item_key=? WHERE item_key=?", (new, old))
        return
    mine = conn.execute("SELECT last_seen_at FROM review_state WHERE item_key=?", (old,)).fetchone()
    if (mine[0] or "") > (have[0] or ""):
        conn.execute("DELETE FROM review_state WHERE item_key=?", (new,))
        conn.execute("UPDATE review_state SET item_key=? WHERE item_key=?", (new, old))
    else:
        conn.execute("DELETE FROM review_state WHERE item_key=?", (old,))
