import importlib.util
import sqlite3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import fixtures  # noqa: E402
from idea_board import packet, pipeline  # noqa: E402
from idea_board.store import Store  # noqa: E402
from test_core import cand, fake_llm  # noqa: E402

spec = importlib.util.spec_from_file_location("idea_board_api_under_test", ROOT / "dashboard" / "plugin_api.py")
api = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
spec.loader.exec_module(api)  # type: ignore[union-attr]


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.store = Store(sqlite3.connect(":memory:"))
        api._STORE_OVERRIDE = self.store  # type: ignore[attr-defined]
        pkt = packet.build(fixtures.inventory(), fixtures.sessions(), self.store, now=fixtures.NOW.astimezone())
        pipeline.run(pkt, fake_llm([cand(), cand(title="Pack for the Denver flight", kind="once", lens="coming_up",
                                                  topic="denver trip", evidence_ids=["E1"], uses=["toolset:web"],
                                                  schedule=None, minutes_once=30)]), self.store, now=fixtures.NOW)

    def tearDown(self):
        api._STORE_OVERRIDE = None  # type: ignore[attr-defined]

    def test_board_shape(self):
        b = api.board()
        self.assertEqual(len(b["cards"]), 2)
        c = b["cards"][0]
        for key in ("id", "title", "why", "prompt", "uses", "evidence", "value_note", "risk", "kind"):
            self.assertIn(key, c)
        self.assertEqual(c["uses"][0].keys(), {"id", "kind", "name"})
        self.assertEqual(b["last_run"]["kept"], 2)
        self.assertIn("dont_automate", [r["code"] for r in b["reasons"]])

    def test_start_dismiss_undo(self):
        ids = [c["id"] for c in api.board()["cards"]]
        api.started(ids[0])
        self.assertEqual(len(api.board()["cards"]), 1)
        self.assertEqual(api.board()["started"][0]["id"], ids[0])
        res = api.dismiss(ids[1], api.DismissInput(reason="not_topic", note="I'm not travelling"))
        self.assertEqual(res["action"], "rule")
        self.assertIn("I'm not travelling", res["rule"])
        self.assertEqual(len(api.board()["rules"]), 1)
        self.assertTrue(api.undo(ids[1])["ok"])
        self.assertEqual(len(api.board()["rules"]), 0)
        self.assertEqual([c["id"] for c in api.board()["cards"]], [ids[1]])

    def test_older_ideas_listed_restored_and_startable(self):
        ids = [c["id"] for c in api.board()["cards"]]
        self.store.conn.execute("UPDATE cards SET status = 'older' WHERE id = ?", (ids[0],))
        self.store.conn.commit()
        b = api.board()
        self.assertEqual(([c["id"] for c in b["older"]], b["older_count"]), ([ids[0]], 1))
        self.assertNotIn(ids[0], [c["id"] for c in b["cards"]])
        self.assertIn("updated_at", b["older"][0])
        self.assertEqual(api.restore(ids[0]), {"ok": True})
        self.assertIn(ids[0], [c["id"] for c in api.board()["cards"]])
        self.store.conn.execute("UPDATE cards SET status = 'older' WHERE id = ?", (ids[0],))
        self.store.conn.commit()
        api.started(ids[0])
        self.assertEqual(api.board()["started"][0]["id"], ids[0])

    def test_errors(self):
        with self.assertRaises(api.HTTPException):
            api.dismiss("IB-9999", api.DismissInput(reason="not_topic", note=""))
        cid = api.board()["cards"][0]["id"]
        with self.assertRaises(api.HTTPException):
            api.dismiss(cid, api.DismissInput(reason="bogus", note=""))
        with self.assertRaises(api.HTTPException):
            api.edit_rule(1, api.RuleInput(text="  "))

    def test_setup_defaults_and_choices(self):
        s = api.board()["setup"]
        self.assertFalse(s["done"])
        self.assertEqual((s["history_days"], s["max_cards"], s["schedule"]), (14, 6, None))
        self.assertIn("follows_main", s["model"])
        out = api.setup(api.SetupInput(history_days=30, max_cards=3, schedule="manual"))["setup"]
        self.assertEqual((out["history_days"], out["max_cards"], out["schedule"]), (30, 3, "manual"))
        self.assertEqual(self.store.get_meta("history_days"), 30)
        with self.assertRaises(api.HTTPException):
            api.setup(api.SetupInput(max_cards=50))
        self.assertTrue(api.setup(api.SetupInput(done=True))["setup"]["done"])
        self.assertTrue(api.board()["setup"]["done"])

    def test_snooze_and_rule_edit(self):
        cid = api.board()["cards"][0]["id"]
        api.snooze(cid, api.SnoozeInput(days=3))
        self.assertEqual([c["id"] for c in api.board()["snoozed"]], [cid])
        other = api.board()["cards"][0]["id"]
        api.dismiss(other, api.DismissInput(reason="dont_automate", note=""))
        rid = api.board()["rules"][0]["id"]
        api.edit_rule(rid, api.RuleInput(text="No invoice automation"))
        self.assertEqual(api.board()["rules"][0]["text"], "No invoice automation")
        api.delete_rule(rid)
        self.assertEqual(api.board()["rules"], [])


if __name__ == "__main__":
    unittest.main()
