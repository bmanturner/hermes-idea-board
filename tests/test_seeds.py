import sqlite3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from idea_board import seeds  # noqa: E402
from idea_board.store import Store  # noqa: E402

SEEDS = [
    {"id": "s001", "title": "Turn meeting notes into tasks", "what": "", "kind": "once",
     "needs": ["meeting_notes", "tasks"], "keywords": ["meeting", "transcript", "action", "standup"]},
    {"id": "s002", "title": "Text you a morning task digest", "what": "", "kind": "recurring",
     "needs": ["tasks", "schedule", "messaging"], "keywords": ["todo", "deadline", "priority"]},
    {"id": "s003", "title": "Chase overdue invoices", "what": "", "kind": "recurring",
     "needs": ["payments", "email"], "keywords": ["invoice", "client", "overdue", "payment"]},
    {"id": "s004", "title": "Summarize the web on a topic", "what": "", "kind": "once",
     "needs": ["web"], "keywords": ["research", "article"]},
    {"id": "s005", "title": "Keep a reading list in your notes", "what": "", "kind": "once",
     "needs": ["notes", "web"], "keywords": ["book", "reading", "article"]},
]
CATALOG = [
    {"slug": "notion", "name": "Notion", "classes": ["notes"], "rank": 1, "description": "Pages"},
    {"slug": "todoist_mcp", "name": "Todoist", "classes": ["tasks"], "rank": 2, "description": "Tasks"},
    {"slug": "linear", "name": "Linear", "classes": ["tasks"], "rank": 11, "description": "Issues"},
    {"slug": "granola_mcp", "name": "Granola", "classes": ["meeting_notes"], "rank": 5, "description": "Meetings"},
    {"slug": "stripe_mcp", "name": "Stripe", "classes": ["payments"], "rank": 8, "description": "Payments"},
    {"slug": "pandadoc_mcp", "name": "PandaDoc", "classes": [], "rank": 50, "description": "Docs"},
]


def caps(*connected, available=("notion", "todoist_mcp", "linear", "granola_mcp", "stripe_mcp", "pandadoc_mcp")):
    out = [
        {"id": "toolset:web", "kind": "toolset", "name": "web", "status": "ready", "tools": ["web_search"]},
        {"id": "toolset:cronjob", "kind": "toolset", "name": "cronjob", "status": "ready", "tools": ["cronjob"]},
        {"id": "platform:telegram", "kind": "platform", "name": "telegram", "status": "ready"},
        {"id": "mcp:Fastmail", "kind": "mcp", "name": "Fastmail", "status": "ready",
         "tools": ["mcp__Fastmail__read_email", "mcp__Fastmail__create_event"]},
        {"id": "skill:competitor-news-monitor", "kind": "skill", "name": "competitor-news-monitor", "status": "ready"},
    ]
    for slug in available:
        out.append({"id": f"connector:{slug}", "kind": "connector", "name": slug,
                    "status": "ready" if slug in connected else "available"})
    return out


def session(title, *texts):
    return {"id": title, "title": title, "turns": [{"role": "user", "text": t} for t in texts]}


class SeedTests(unittest.TestCase):
    def test_classes_ready(self):
        have = seeds.classes_ready(caps("notion"), CATALOG)
        self.assertTrue({"web", "schedule", "messaging", "email", "calendar", "notes"} <= have)
        self.assertNotIn("monitoring", have)  # a skill named "...monitor" is not production monitoring
        self.assertNotIn("tasks", have)
        delegation = {"id": "toolset:delegation", "kind": "toolset", "name": "delegation", "status": "ready",
                      "tools": ["delegate_task"]}
        self.assertNotIn("tasks", seeds.classes_ready([delegation], CATALOG))  # handing work to a subagent isn't a task tracker
        reminders = {"id": "mcp:phone", "kind": "mcp", "name": "phone", "status": "ready", "tools": ["mobile_reminder_create"]}
        self.assertIn("tasks", seeds.classes_ready([reminders], CATALOG))
        lazy = {"id": "mcp:Fastmail", "kind": "mcp", "name": "Fastmail", "status": "ready", "tools": []}
        self.assertEqual(seeds.classes_ready([lazy], CATALOG), {"email", "calendar"})

    def test_topic_match_needs_two_chats_or_two_words(self):
        topics = seeds.chat_topics([session("a", "Any overdue invoices?"), session("b", "Send the invoice to the client")])
        self.assertEqual(seeds.topic_match(SEEDS[2], topics)[0], "invoice")
        once = seeds.chat_topics([session("a", "I read a book")])
        self.assertEqual(seeds.topic_match(SEEDS[4], once), [])
        # one chat with both words isn't enough, and generic words never count
        single = seeds.chat_topics([session("a", "overdue invoice from a client")])
        self.assertEqual(seeds.topic_match(SEEDS[2], single), [])
        pair = {"id": "p", "keywords": ["pull-request", "merge"]}
        prs = seeds.chat_topics([session("a", "Review my pull requests before merge"), session("b", "Two pull requests to merge")])
        self.assertEqual(sorted(seeds.topic_match(pair, prs)), ["merge", "pull-request"])
        generic = {"id": "g", "keywords": ["draft", "reply", "review", "lead"]}
        chats = seeds.chat_topics([session("a", "draft a reply, review it"), session("b", "review the draft for the lead role")])
        self.assertEqual(seeds.topic_match(generic, chats), [])

    def test_recommend_ranks_and_folds_alternatives(self):
        sessions = [session("standup", "Can you clean up the standup meeting transcript?"),
                    session("todo", "What's on my todo for today? The deadline is Friday"),
                    session("todo again", "Add the visa form to my todo, deadline Monday")]
        recs = seeds.recommend(caps(), sessions, seeds=SEEDS, catalog=CATALOG)
        names = [r["name"] for r in recs]
        self.assertEqual(names, ["Todoist"])  # the only connector whose ideas match these chats
        todoist = recs[0]
        self.assertEqual([a["name"] for a in todoist["alternatives"]], ["Linear"])
        self.assertEqual((todoist["unlocked"], todoist["matched"]), (1, 1))
        self.assertEqual(todoist["examples"][0]["words"], ["deadline", "todo"])
        # Notion and Stripe unlock ideas too, but nothing these chats talk about: not recommended
        self.assertNotIn("Granola", names)   # meeting notes alone isn't enough for s001
        reading = [session("a", "Save this article to my reading list"), session("b", "A good article for the reading pile")]
        self.assertEqual([r["name"] for r in seeds.recommend(caps(), reading, seeds=SEEDS, catalog=CATALOG)], ["Notion"])
        self.assertEqual(seeds.recommend(caps(), reading, seeds=SEEDS, catalog=CATALOG, hidden={"notion"}), [])

    def test_connected_connector_is_not_recommended(self):
        reading = [session("a", "Save this article to my reading list"), session("b", "A good article for the reading pile")]
        self.assertEqual(seeds.recommend(caps("notion"), reading, seeds=SEEDS, catalog=CATALOG), [])

    def test_available_now_and_prompt(self):
        have = seeds.classes_ready(caps(), CATALOG)
        now = seeds.available_now(SEEDS, have, seeds.chat_topics([]))
        self.assertEqual([s["id"] for s in now], ["s004"])
        prompt = seeds.connect_prompt({"name": "Todoist", "examples": [{"title": "Text you a morning task digest"}]})
        self.assertTrue(prompt.startswith("I'd like to connect Todoist."))
        self.assertIn("- Text you a morning task digest", prompt)

    def test_shipped_data_is_consistent(self):
        catalog = seeds.load_catalog()
        for c in catalog:
            self.assertTrue(set(c.get("classes") or []) <= set(seeds.CLASSES), c["slug"])
        library = seeds.load_seeds()
        if library:
            self.assertEqual(len({s["id"] for s in library}), len(library))
            for s in library:
                self.assertTrue(set(s["needs"]) <= set(seeds.CLASSES), s["id"])
                self.assertLessEqual(len(s["title"]), 60, s["id"])


class ConnectorApiTests(unittest.TestCase):
    def setUp(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("idea_board_api_seed_test", ROOT / "dashboard" / "plugin_api.py")
        self.api = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(self.api)  # type: ignore[union-attr]
        self.store = Store(sqlite3.connect(":memory:"))
        self.api._STORE_OVERRIDE = self.store  # type: ignore[attr-defined]
        chats = [session("a", "Overdue invoice for the client"), session("b", "Is the client invoice still overdue?"),
                 session("c", "Save this article to my reading list"), session("d", "Another article for the reading pile")]
        recs = seeds.recommend(caps(), chats, seeds=SEEDS, catalog=CATALOG)
        self.assertEqual({r["name"] for r in recs}, {"Stripe", "Notion"})
        self.store.set_meta("connector_recs", {"as_of": 1.0, "items": recs})

    def test_board_hide_unhide(self):
        board = self.api.board()["connectors"]
        self.assertTrue(board and len(board) <= 3)
        first = board[0]["slug"]
        self.assertIn("I'd like to connect", board[0]["prompt"])
        self.api.hide_connector(first)
        self.assertNotIn(first, [c["slug"] for c in self.api.board()["connectors"]])
        self.api.unhide_connector(first)
        self.assertIn(first, [c["slug"] for c in self.api.board()["connectors"]])
        with self.assertRaises(self.api.HTTPException):
            self.api.hide_connector("nope")


if __name__ == "__main__":
    unittest.main()
