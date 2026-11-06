"""Idea Board storage: cards, dismissals, rules and runs in one SQLite file.

In Hermes the connection comes from ``plugins.plugin_storage.plugin_db("idea-board")``
(``<HERMES_HOME>/plugin-data/idea-board/data.db``); tests pass ``sqlite3.connect(":memory:")``.
"""
from __future__ import annotations

import json
import sqlite3
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from .text import content_tokens, topic_match

@lru_cache(maxsize=1)
def _connector_names() -> dict[str, str]:
    try:
        path = Path(__file__).resolve().parent.parent / "data" / "connectors.json"
        return {c["slug"]: c["name"] for c in json.loads(path.read_text())["connectors"]}
    except Exception:
        return {}


def cap_label(cap_id: str) -> str:
    """A capability id as a person would say it in a rule: 'connector:granola_mcp' → 'Granola',
    'toolset:browser' → 'the browser tools', 'skill:pdf' → 'the pdf skill'."""
    kind, _, name = str(cap_id).partition(":")
    if not name:
        return str(cap_id)
    if kind == "connector":
        return _connector_names().get(name) or name.removesuffix("_mcp").replace("_", " ").title()
    if kind == "toolset":
        return f"the {name.replace('_', ' ')} tools"
    if kind == "skill":
        return f"the {name} skill"
    if kind == "platform":
        return name.capitalize()
    return name  # MCP servers keep the name the user gave them


BOARD_SIZE = 12        # open ideas on the board at once
OLDER_AFTER_DAYS = 7   # an idea nobody touched for this long moves to "Older"

STALE_RUN_SECONDS = 30 * 60
STALE_RUN_ERROR = "it stopped before finishing (Hermes may have restarted); the next run starts fresh"

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, started_at REAL, finished_at REAL, status TEXT, trigger TEXT,
  sessions_read INTEGER DEFAULT 0, evidence INTEGER DEFAULT 0, candidates INTEGER DEFAULT 0,
  kept INTEGER DEFAULT 0, rejected TEXT, input_tokens INTEGER DEFAULT 0, output_tokens INTEGER DEFAULT 0,
  cost_usd REAL, model TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS cards (
  id TEXT PRIMARY KEY, run_id INTEGER, created_at REAL, updated_at REAL, status TEXT,
  kind TEXT, lens TEXT, topic TEXT, title TEXT, why TEXT, prompt TEXT, uses TEXT, evidence TEXT,
  schedule TEXT, expires TEXT, risk TEXT, value_min REAL, score REAL, value_note TEXT,
  stretch INTEGER DEFAULT 0, seed_id TEXT, then_recurring TEXT,
  started_at REAL, session_id TEXT, outcome TEXT, snooze_until REAL);
CREATE TABLE IF NOT EXISTS dismissals (
  id INTEGER PRIMARY KEY AUTOINCREMENT, card_id TEXT, at REAL, reason_code TEXT, reason_text TEXT);
CREATE TABLE IF NOT EXISTS rules (
  id INTEGER PRIMARY KEY AUTOINCREMENT, created_at REAL, reason_code TEXT, scope TEXT, match TEXT,
  text TEXT, source_cards TEXT, hits INTEGER DEFAULT 0, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS consumed_evidence (quote_key TEXT PRIMARY KEY, at REAL, card_id TEXT);
"""

OPEN = ("open", "snoozed")
# Reason chips on the dismiss menu. Codes map to behaviour; only some create rules.
REASONS = {
    "not_relevant": "Not relevant to me",
    "already_done": "Already handled",
    "wrong_timing": "Not now",
    "dont_automate": "Don't automate this",
    "too_risky": "Too risky",
    "wrong_tool": "Wrong tool for this",
    "not_topic": "Not this topic",
}
SNOOZE_DAYS = 7
_JSON_FIELDS = ("uses", "evidence")


class Store:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # ---- meta (setup choices) ----------------------------------------------------------------
    def get_meta(self, key: str, default: Any = None) -> Any:
        row = self.conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        if not row:
            return default
        try:
            return json.loads(row["value"])
        except (TypeError, ValueError):
            return row["value"]

    def set_meta(self, key: str, value: Any) -> None:
        self.conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, json.dumps(value)))
        self.conn.commit()

    # ---- runs -------------------------------------------------------------------------------
    def _close_stale_runs(self) -> None:
        """A run takes minutes. One still 'running' after STALE_RUN_SECONDS was cut off (Hermes
        restarted or the process died), so record it as failed instead of running forever."""
        self.conn.execute(
            "UPDATE runs SET status = 'error', finished_at = started_at, error = ? "
            "WHERE status = 'running' AND started_at < ?", (STALE_RUN_ERROR, time.time() - STALE_RUN_SECONDS))
        # Always commit: Python's sqlite3 opens a transaction for any UPDATE, even one that changes no
        # rows, and an uncommitted one holds the write lock against the nightly run and the board.
        self.conn.commit()

    def start_run(self, trigger: str) -> int:
        self._close_stale_runs()
        cur = self.conn.execute("INSERT INTO runs (started_at, status, trigger) VALUES (?, 'running', ?)",
                                (time.time(), trigger))
        self.conn.commit()
        return int(cur.lastrowid or 0)

    def finish_run(self, run_id: int, status: str, **stats: Any) -> None:
        cols = ["finished_at = ?", "status = ?"]
        vals: list[Any] = [time.time(), status]
        for k, v in stats.items():
            cols.append(f"{k} = ?")
            vals.append(json.dumps(v) if isinstance(v, (list, dict)) else v)
        self.conn.execute(f"UPDATE runs SET {', '.join(cols)} WHERE id = ?", (*vals, run_id))
        self.conn.commit()

    def last_run(self) -> dict[str, Any] | None:
        """The newest run that finished (ok or failed); a run in progress is ``active_run``."""
        self._close_stale_runs()
        row = self.conn.execute("SELECT * FROM runs WHERE status != 'running' ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None

    def active_run(self) -> dict[str, Any] | None:
        self._close_stale_runs()
        row = self.conn.execute("SELECT * FROM runs WHERE status = 'running' ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None

    # ---- cards ------------------------------------------------------------------------------
    def next_card_id(self) -> str:
        row = self.conn.execute("SELECT value FROM meta WHERE key = 'card_seq'").fetchone()
        n = int(row["value"]) + 1 if row else 1
        self.conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('card_seq', ?)", (str(n),))
        return f"IB-{n:04d}"

    def add_card(self, card: dict[str, Any]) -> str:
        now = time.time()
        row = {k: (json.dumps(v) if k in _JSON_FIELDS else v) for k, v in card.items()}
        row.setdefault("status", "open")
        row.setdefault("created_at", now)
        row["updated_at"] = now
        cols = ", ".join(row)
        self.conn.execute(f"INSERT INTO cards ({cols}) VALUES ({', '.join('?' for _ in row)})", tuple(row.values()))
        self.conn.commit()
        return card["id"]

    def card(self, card_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
        return self._card(row) if row else None

    def cards(self, statuses: Iterable[str] = OPEN) -> list[dict[str, Any]]:
        statuses = tuple(statuses)
        q = f"SELECT * FROM cards WHERE status IN ({', '.join('?' for _ in statuses)}) ORDER BY score DESC, created_at DESC"
        return [self._card(r) for r in self.conn.execute(q, statuses)]

    def board(self, now: float | None = None) -> list[dict[str, Any]]:
        """Open cards, best first, at most BOARD_SIZE: snoozes that ran out reopen, expired one-offs close,
        and ideas set aside move to 'older' (see ``_set_aside``)."""
        now = now or time.time()
        today = time.strftime("%Y-%m-%d", time.localtime(now))
        self.conn.execute("UPDATE cards SET status = 'open', snooze_until = NULL, updated_at = ? "
                          "WHERE status = 'snoozed' AND snooze_until <= ?", (now, now))
        self.conn.execute("UPDATE cards SET status = 'expired', updated_at = ? "
                          "WHERE status IN ('open', 'snoozed', 'older') AND expires IS NOT NULL AND expires < ?",
                          (now, today))
        self._set_aside(now)
        self.conn.commit()
        return self.cards(("open",))

    def _set_aside(self, now: float) -> None:
        """Keep the board short. Ideas from the newest run, and ideas the user brought back or that came
        back from a snooze since then, keep their place. The rest move to 'older' when nobody touched them
        for OLDER_AFTER_DAYS, or when they fall outside the best BOARD_SIZE."""
        rows = [dict(r) for r in self.conn.execute(
            "SELECT id, created_at, updated_at, score FROM cards WHERE status = 'open'")]
        if not rows:
            return
        touched = {r["id"]: float(r["updated_at"] or r["created_at"] or 0) for r in rows}
        fresh_since = max(float(r["created_at"] or 0) for r in rows) - 3600  # one run inserts within minutes
        fresh = {i for i, t in touched.items() if t >= fresh_since}
        stale_before = now - OLDER_AFTER_DAYS * 86400
        aside = {r["id"] for r in rows if r["id"] not in fresh and touched[r["id"]] < stale_before}
        keep = sorted((r for r in rows if r["id"] not in aside),
                      key=lambda r: (r["id"] not in fresh, -float(r["score"] or 0)))
        aside |= {r["id"] for r in keep[BOARD_SIZE:]}
        if aside:
            self.conn.executemany("UPDATE cards SET status = 'older', updated_at = ? WHERE id = ?",
                                  [(now, i) for i in aside])

    def restore(self, card_id: str) -> bool:
        """Put an idea from 'Older' back on the board; it counts as fresh until the next run."""
        card = self.card(card_id)
        if not card or card["status"] != "older":
            return False
        self._set(card_id, status="open")
        return True

    def _set(self, card_id: str, **fields: Any) -> None:
        fields["updated_at"] = time.time()
        sets = ", ".join(f"{k} = ?" for k in fields)
        self.conn.execute(f"UPDATE cards SET {sets} WHERE id = ?", (*fields.values(), card_id))
        self.conn.commit()

    def mark_started(self, card_id: str) -> None:
        self._set(card_id, status="started", started_at=time.time())

    def link_session(self, card_id: str, session_id: str) -> None:
        self._set(card_id, session_id=session_id)

    def report(self, card_id: str, outcome: str) -> None:
        self._set(card_id, outcome=outcome, status="done" if outcome == "done" else "started")

    def snooze(self, card_id: str, days: int = SNOOZE_DAYS) -> None:
        self._set(card_id, status="snoozed", snooze_until=time.time() + days * 86400)

    @staticmethod
    def _card(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        for k in _JSON_FIELDS:
            if d.get(k):
                d[k] = json.loads(d[k])
            else:
                d[k] = []
        return d

    # ---- dismissals and rules ---------------------------------------------------------------
    def dismiss(self, card_id: str, reason_code: str, reason_text: str = "") -> dict[str, Any]:
        """Record a dismissal and apply what the reason means. Returns {"action": ..., "rule": ...}."""
        if reason_code not in REASONS:
            raise ValueError(f"unknown reason {reason_code!r}")
        card = self.card(card_id)
        if not card:
            raise KeyError(card_id)
        self.conn.execute("INSERT INTO dismissals (card_id, at, reason_code, reason_text) VALUES (?, ?, ?, ?)",
                          (card_id, time.time(), reason_code, reason_text.strip()[:500]))
        if reason_code == "wrong_timing":
            self.snooze(card_id)
            return {"action": "snoozed", "rule": None}
        self._set(card_id, status="dismissed")
        if reason_code == "already_done":
            for ev in card.get("evidence") or []:
                key = (ev.get("quote") or "").lower()
                if key:
                    self.conn.execute("INSERT OR IGNORE INTO consumed_evidence VALUES (?, ?, ?)",
                                      (key, time.time(), card_id))
            self.conn.commit()
            return {"action": "evidence_consumed", "rule": None}
        rule = self._rule_for(card, reason_code, reason_text)
        rule_id = self._add_rule(rule)
        widened = self._maybe_widen(reason_code, rule)
        return {"action": "rule", "rule": rule_id, "widened": widened}

    def _rule_for(self, card: dict[str, Any], code: str, note: str) -> dict[str, Any]:
        topic = card.get("topic") or card.get("title") or ""
        main_cap = next((u for u in card.get("uses") or [] if not u.startswith("platform:")), None)
        match: dict[str, Any] = {"topic": topic}
        if code == "dont_automate":
            match["kind"] = "recurring"
        elif code == "too_risky":
            match["risk"] = "external-action"
        elif code == "wrong_tool" and main_cap:
            match["capability"] = main_cap
        text = {
            "not_relevant": f"I won't suggest ideas about “{topic}”.",
            "not_topic": f"I'll stay off the topic “{topic}”.",
            "dont_automate": f"I won't put “{topic}” on a schedule.",
            "too_risky": f"I won't suggest anything that acts on its own for “{topic}”.",
            "wrong_tool": f"I won't use {cap_label(main_cap) if main_cap else 'that tool'} for “{topic}”.",
        }[code]
        if note.strip():
            text += f" You said: “{note.strip()[:160]}”"
        return {"reason_code": code, "scope": "topic", "match": match, "text": text, "source_cards": [card["id"]]}

    def _add_rule(self, rule: dict[str, Any]) -> int:
        cur = self.conn.execute(
            "INSERT INTO rules (created_at, reason_code, scope, match, text, source_cards) VALUES (?, ?, ?, ?, ?, ?)",
            (time.time(), rule["reason_code"], rule["scope"], json.dumps(rule["match"]), rule["text"],
             json.dumps(rule["source_cards"])))
        self.conn.commit()
        return int(cur.lastrowid or 0)

    def _maybe_widen(self, code: str, rule: dict[str, Any]) -> int | None:
        """Two strikes to widen: the same reason about the same tool (or the same kind) on a
        different topic drops the topic from the rule."""
        key = "capability" if code == "wrong_tool" else "kind" if code == "dont_automate" else None
        if not key or key not in rule["match"]:
            return None
        for other in self.rules():
            m = other["match"]
            if (other["reason_code"] == code and other["scope"] == "topic" and m.get(key) == rule["match"][key]
                    and not topic_match(m.get("topic", ""), rule["match"]["topic"])):
                wide = {"reason_code": code, "scope": key, "match": {key: rule["match"][key]},
                        "text": (f"I won't use {cap_label(rule['match'][key])} for ideas like these." if key == "capability"
                                 else "I won't put things on a schedule unless you ask."),
                        "source_cards": sorted(set(other["source_cards"]) | set(rule["source_cards"]))}
                if not any(r["scope"] == key and r["match"] == wide["match"] for r in self.rules()):
                    return self._add_rule(wide)
        return None

    def rules(self, active: bool = True) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM rules WHERE active = ? ORDER BY id", (1 if active else 0,))
        out = []
        for r in rows:
            d = dict(r)
            d["match"] = json.loads(d["match"])
            d["source_cards"] = json.loads(d["source_cards"])
            out.append(d)
        return out

    def undo_dismiss(self, card_id: str) -> bool:
        """Put a dismissed or snoozed card back and retire the rules its dismissal created."""
        card = self.card(card_id)
        if not card or card["status"] not in ("dismissed", "snoozed"):
            return False
        last = self.conn.execute("SELECT at FROM dismissals WHERE card_id = ? ORDER BY id DESC LIMIT 1",
                                 (card_id,)).fetchone()
        if last:
            for r in self.rules():
                if card_id in r["source_cards"] and r["created_at"] >= last["at"]:
                    self.delete_rule(r["id"])
            self.conn.execute("DELETE FROM consumed_evidence WHERE card_id = ?", (card_id,))
        self._set(card_id, status="open", snooze_until=None)
        return True

    def edit_rule(self, rule_id: int, text: str) -> None:
        self.conn.execute("UPDATE rules SET text = ? WHERE id = ?", (text.strip()[:300], rule_id))
        self.conn.commit()

    def delete_rule(self, rule_id: int) -> None:
        self.conn.execute("UPDATE rules SET active = 0 WHERE id = ?", (rule_id,))
        self.conn.commit()

    def hit_rule(self, rule_id: int) -> None:
        self.conn.execute("UPDATE rules SET hits = hits + 1 WHERE id = ?", (rule_id,))
        self.conn.commit()

    def blocking_rule(self, cand: dict[str, Any]) -> dict[str, Any] | None:
        """The first active rule this candidate breaks, or None."""
        for r in self.rules():
            m = r["match"]
            if "topic" in m and not (topic_match(m["topic"], cand.get("topic") or "")
                                     or topic_match(m["topic"], cand.get("title") or "")):
                continue
            if "kind" in m and cand.get("kind") != m["kind"]:
                continue
            if "risk" in m and cand.get("risk") != m["risk"]:
                continue
            if "capability" in m and m["capability"] not in (cand.get("uses") or []):
                continue
            return r
        return None

    def consumed_quotes(self) -> set[str]:
        return {r["quote_key"] for r in self.conn.execute("SELECT quote_key FROM consumed_evidence")}

    # ---- learning summary for the prompts ---------------------------------------------------
    def history_for_prompt(self, limit: int = 40) -> dict[str, Any]:
        rows = self.conn.execute(
            "SELECT id, status, kind, topic, title, outcome FROM cards ORDER BY created_at DESC LIMIT ?", (limit,))
        recent = [dict(r) for r in rows]
        return {
            "open": [c for c in recent if c["status"] in OPEN],
            "started": [c for c in recent if c["status"] in ("started", "done")],
            "dismissed": [c for c in recent if c["status"] == "dismissed"],
            "set_aside": [c for c in recent if c["status"] == "older"],
            "rules": [r["text"] for r in self.rules()],
        }


def title_key(title: str) -> frozenset[str]:
    return frozenset(content_tokens(title))
