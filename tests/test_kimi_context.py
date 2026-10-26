import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from kimi_context import current_context
from render_instructions import SKILL_ROOT, render_instructions


SESSION = "session-test"
AGENT = "child-a"


def turn(number, model="k3.1-pro", effort="high"):
    return [
        {"type": "agent.turn.started", "turnId": number},
        {"type": "llm.request", "agentId": AGENT, "kind": "loop", "turnStep": f"{number}.1",
         "model": model, "modelAlias": "irrelevant-alias", "thinkingEffort": effort},
    ]


class KimiContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.session = self.home / "sessions/workdir" / SESSION
        self.wire = self.session / "agents" / AGENT / "wire.jsonl"
        self.wire.parent.mkdir(parents=True)
        self.index = self.home / "session_index.jsonl"
        self.index.write_text(json.dumps({"sessionId": SESSION, "sessionDir": str(self.session)}) + "\n")
        parent = self.session / "agents/main/wire.jsonl"
        parent.parent.mkdir()
        parent.write_text("parent must not be read")
        self.write(*turn(1))

    def write(self, *events):
        self.wire.write_text("".join(json.dumps(event) + "\n" for event in events))

    def read(self):
        return current_context(self.home, SESSION, AGENT)

    def cli(self, *args):
        return subprocess.run([sys.executable, "-B", str(SKILL_ROOT / "scripts/render_instructions.py"),
                               "--harness", "kimi-code", *args], text=True, capture_output=True,
                              env={**os.environ, "KIMI_CODE_HOME": str(self.home), "CODEX_THREAD_ID": "unrelated"})

    def test_reads_exact_child_and_preserves_raw_request_model(self):
        before = self.index.read_bytes(), self.wire.read_bytes()
        with self.index.open("a") as stream:
            stream.write(json.dumps({"sessionId": "other", "sessionDir": "/unrelated"}) + "\n")
        self.assertEqual(self.read(), {"model": "k3.1-pro", "reasoning_effort": "high"})
        self.assertEqual(self.wire.read_bytes(), before[1])

    def test_ignores_compaction_foreign_agent_and_foreign_turn(self):
        foreign = {**turn(1)[1], "agentId": "main", "model": "gpt-6-astra"}
        compaction = {**turn(1)[1], "kind": "compaction", "model": "other-model"}
        self.write(*turn(1), foreign, compaction, turn(9)[1])
        self.assertEqual(self.read()["model"], "k3.1-pro")

    def test_resume_reads_new_turn_and_model(self):
        self.write(*turn(1), {"type": "agent.turn.ended", "turnId": 1}, *turn(2, "kimi-k3", "low"))
        self.assertEqual(self.read(), {"model": "kimi-k3", "reasoning_effort": "low"})

    def test_finished_or_new_turn_without_request_does_not_use_stale_context(self):
        for tail in ({"type": "agent.turn.ended", "turnId": 1},
                     {"type": "turn.ended", "agentId": AGENT, "turnId": 1},
                     {"type": "agent.turn.started", "turnId": 2}):
            with self.subTest(tail=tail):
                self.write(*turn(1), tail)
                self.assertRaises(ValueError, self.read)

    def test_partial_append_is_ignored(self):
        with self.wire.open("a") as stream:
            stream.write('{"type":"llm.request",')
        self.assertEqual(self.read()["model"], "k3.1-pro")
        self.write({"type": "agent.turn.started", "turnId": 2})
        with self.wire.open("a") as stream:
            stream.write(json.dumps(turn(2)[1])[:40])
        self.assertRaises(ValueError, self.read)

    def test_native_default_can_have_different_family_and_missing_effort(self):
        self.write(*turn(2, "gpt-7", None))
        result = render_instructions(**self.read())
        self.assertEqual(result["model"], "gpt-7")
        self.assertEqual(result["profile"], "references/openai.md")
        self.assertIsNone(result["reasoning_effort"])
        self.write(*turn(2, None))
        self.assertRaises(ValueError, self.read)

    def test_missing_or_deleted_session_and_invalid_identity(self):
        for session, agent in (("", AGENT), (SESSION, "../main"), ("unknown", AGENT)):
            with self.subTest(session=session, agent=agent), self.assertRaises(ValueError):
                current_context(self.home, session, agent)
        with self.index.open("a") as stream:
            stream.write(json.dumps({"sessionId": SESSION, "deleted": True}) + "\n")
        self.assertRaises(ValueError, self.read)

    def test_session_directory_must_belong_to_native_root(self):
        for path in ("relative", str(self.home / "elsewhere")):
            with self.subTest(path=path):
                self.index.write_text(json.dumps({"sessionId": SESSION, "sessionDir": path}) + "\n")
                self.assertRaises(ValueError, self.read)

    def test_cli_requires_native_ids_and_has_no_model_override(self):
        args = ("--session-id", SESSION, "--agent-id", AGENT)
        result = self.cli(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["profile"], "references/kimi-k3.md")
        for invalid in ((), ("--session-id", SESSION), (*args, "--model", "kimi-k3")):
            with self.subTest(args=invalid):
                self.assertNotEqual(self.cli(*invalid).returncode, 0)


if __name__ == "__main__":
    unittest.main()
