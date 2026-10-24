import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from render_instructions import ContextError, SKILL_ROOT, current_context, render_instructions


THREAD = "11111111-1111-4111-8111-111111111111"
PARENT = "22222222-2222-4222-8222-222222222222"


def event(kind, **payload):
    return {"type": kind, "payload": payload}


def turn(turn_id, model="gpt-6-astra", effort="xhigh"):
    return [
        event("event_msg", type="task_started", turn_id=turn_id),
        event("turn_context", turn_id=turn_id, model=model, effort=effort),
    ]


class RenderingTests(unittest.TestCase):
    def test_supported_models_and_aliases(self):
        cases = {
            "gpt-6-astra": "gpt-6-astra.md",
            "gpt-6.1-sol": "gpt-6.1-sol.md",
            "kimi-k3": "kimi-k3.md",
            "k3": "kimi-k3.md",
            "k3-256k": "kimi-k3.md",
            "kimi-k3.1-pro": "kimi-k3.md",
            "k3.1-pro": "kimi-k3.md",
            "kimi-k3.1-pro-highspeed": "kimi-k3.md",
            "k3.1-pro-highspeed": "kimi-k3.md",
            "claude-fable-5-1": "claude-fable-5-1.md",
            "claude-opus-5-5": "claude-opus-5-5.md",
            "claude-sonnet-5-5": "claude-sonnet-5-5.md",
            "claude-haiku-5-5": "claude-haiku-5-5.md",
        }
        core = (SKILL_ROOT / "references/core.md").read_text()
        for model, filename in cases.items():
            with self.subTest(model=model):
                result = render_instructions(model, "high")
                profile = "references/" + filename
                self.assertEqual(result["model"], model)
                self.assertEqual(result["reasoning_effort"], "high")
                self.assertEqual(result["profile"], profile)
                self.assertEqual(result["instructions"], core.rstrip() + "\n\n" + (SKILL_ROOT / profile).read_text())

    def test_unmapped_model_gets_only_core(self):
        result = render_instructions("future-model")
        self.assertIsNone(result["profile"])
        self.assertEqual(result["instructions"], (SKILL_ROOT / "references/core.md").read_text())

    def test_invalid_model_does_not_fall_back(self):
        for model in (None, "", " ", " gpt-6-astra", 42):
            with self.subTest(model=model), self.assertRaises(ContextError):
                render_instructions(model)

    def test_missing_known_profile_does_not_fall_back(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "references").mkdir()
            (root / "references/core.md").write_text("Core")
            with self.assertRaises(FileNotFoundError):
                render_instructions("gpt-6-astra", skill_root=root)
            self.assertEqual(render_instructions("future-model", skill_root=root)["instructions"], "Core")

    def test_missing_core_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(FileNotFoundError):
            render_instructions("future-model", skill_root=Path(directory))


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        (self.home / "sessions").mkdir()
        self.rollout = self.home / "sessions/child.jsonl"
        self.index = self.home / "state_5.sqlite"
        with closing(sqlite3.connect(self.index)) as db:
            db.execute("CREATE TABLE threads (id TEXT PRIMARY KEY, rollout_path TEXT)")
            db.execute("INSERT INTO threads VALUES (?, ?)", (THREAD, str(self.rollout)))
            db.execute("INSERT INTO threads VALUES (?, ?)", (PARENT, str(self.home / "sessions/parent.jsonl")))
            db.commit()
        (self.home / "sessions/parent.jsonl").write_text("unrelated unreadable session")
        self.write([event("session_meta", id=THREAD), *turn("child-turn")])

    def write(self, events):
        self.rollout.write_text("".join(json.dumps(record) + "\n" for record in events))

    def read(self):
        return current_context(self.home, THREAD)

    def cli(self, *args, thread=THREAD):
        env = {**os.environ, "CODEX_HOME": str(self.home), "CODEX_THREAD_ID": thread, "CODEX_SESSION_ID": PARENT}
        return subprocess.run([sys.executable, "-B", str(SKILL_ROOT / "scripts/render_instructions.py"), *args],
                              env=env, text=True, capture_output=True)

    def test_own_active_turn_after_inherited_history(self):
        self.write([
            event("session_meta", id=PARENT), *turn("parent-turn", "gpt-6.1-sol", "low"),
            event("session_meta", id=THREAD), *turn("child-turn"),
            event("turn_context", turn_id="parent-turn", model="gpt-6.1-sol", effort="low"),
        ])
        self.assertEqual(self.read(), {"model": "gpt-6-astra", "reasoning_effort": "xhigh"})

    def test_continuation_uses_new_model_and_latest_context(self):
        events = [event("session_meta", id=THREAD), *turn("first")]
        self.write(events)
        self.assertEqual(self.read()["model"], "gpt-6-astra")
        events += [event("event_msg", type="task_complete", turn_id="first"), *turn("second")]
        events += [event("turn_context", turn_id="second", model="gpt-6.1-sol", effort="high")]
        self.write(events)
        self.assertEqual(self.read(), {"model": "gpt-6.1-sol", "reasoning_effort": "high"})

    def test_full_history_fork_keeps_own_metadata_before_parent_history(self):
        inherited = [event("session_meta", id=THREAD), event("session_meta", id=PARENT),
                     *turn("parent-turn", "gpt-6.1-sol", "low")]
        self.write([*inherited, *turn("child-turn")])
        self.assertEqual(self.read(), {"model": "gpt-6-astra", "reasoning_effort": "xhigh"})
        self.write([*inherited, event("event_msg", type="task_started", turn_id="child-turn")])
        with self.assertRaises(ContextError):
            self.read()

    def test_no_stale_fallback_without_current_context(self):
        self.write([event("session_meta", id=THREAD), *turn("first"),
                    event("event_msg", type="task_started", turn_id="second")])
        with self.assertRaises(ContextError):
            self.read()

    def test_foreign_session_and_finished_turn_are_not_current(self):
        cases = [
            [event("session_meta", id=PARENT), *turn("parent")],
            [event("session_meta", id=THREAD), *turn("child"),
             event("event_msg", type="task_complete", turn_id="child")],
            [event("session_meta", id=THREAD), *turn("child"),
             event("event_msg", type="turn_aborted", turn_id="child")],
        ]
        for records in cases:
            with self.subTest(records=records):
                self.write(records)
                with self.assertRaises(ContextError):
                    self.read()

    def test_missing_model_errors_but_effort_is_optional(self):
        self.write([event("session_meta", id=THREAD), *turn("child", effort=None)])
        self.assertIsNone(self.read()["reasoning_effort"])
        self.write([event("session_meta", id=THREAD), *turn("child", model=None)])
        self.assertRaises(ContextError, self.read)

    def test_partial_append_does_not_invalidate_existing_context(self):
        with self.rollout.open("a") as stream:
            stream.write('{"type":"response_item",')
        self.assertEqual(self.read()["model"], "gpt-6-astra")

    def test_missing_thread_and_bad_identity(self):
        for identity in ("", "not-a-thread", "33333333-3333-4333-8333-333333333333"):
            with self.subTest(identity=identity), self.assertRaises(ContextError):
                current_context(self.home, identity)

    def test_index_is_read_only_and_other_sessions_are_not_read(self):
        before = self.index.read_bytes(), self.rollout.read_bytes()
        self.read()
        self.assertEqual(before, (self.index.read_bytes(), self.rollout.read_bytes()))
        self.index.unlink()
        with self.assertRaises(sqlite3.Error):
            self.read()
        self.assertFalse(self.index.exists())

    def test_rollout_must_belong_to_native_sessions(self):
        with closing(sqlite3.connect(self.index)) as db:
            db.execute("UPDATE threads SET rollout_path=? WHERE id=?", (str(self.home / "other.jsonl"), THREAD))
            db.commit()
        with self.assertRaises(ContextError):
            self.read()

    def test_cli_uses_own_identity_and_rejects_model_override(self):
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["profile"], "references/gpt-6-astra.md")
        self.assertNotEqual(self.cli("--model", "gpt-6.1-sol").returncode, 0)
        missing = self.cli(thread="")
        self.assertNotEqual(missing.returncode, 0)
        self.assertEqual(missing.stdout, "")
        self.assertIn("CODEX_THREAD_ID", missing.stderr)


if __name__ == "__main__":
    unittest.main()
