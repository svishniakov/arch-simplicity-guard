import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from claude_hook import MARKER_COMMAND, claude_context
from render_instructions import ContextError, SKILL_ROOT, render_instructions


class ClaudeHookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "session-a/subagents/agent-child-a.jsonl"
        self.path.parent.mkdir(parents=True)
        self.parent = self.root / "session-a.jsonl"
        self.parent.write_text("parent must not be read")
        self.payload = {
            "hook_event_name": "PostToolUse", "tool_name": "Bash",
            "tool_input": {"command": MARKER_COMMAND}, "tool_use_id": "toolu_current",
            "session_id": "session-a", "agent_id": "child-a",
            "transcript_path": str(self.parent), "effort": {"level": "high"},
        }
        self.write(self.record())

    def record(self, model="claude-sonnet-5-5", tool="toolu_current", agent="child-a", session="session-a"):
        return {"type": "assistant", "sessionId": session, "agentId": agent, "message": {
            "model": model, "content": [{"type": "tool_use", "id": tool, "name": "Bash",
                                         "input": {"command": MARKER_COMMAND}}],
        }}

    def write(self, *records):
        self.path.write_text("".join(json.dumps(record) + "\n" for record in records))

    def cli(self, payload=None, *args):
        return subprocess.run([sys.executable, "-B", str(SKILL_ROOT / "scripts/claude_hook.py"), *args],
                              input=json.dumps(self.payload if payload is None else payload),
                              text=True, capture_output=True)

    def test_current_call_ignores_parent_other_agent_and_later_unrelated_response(self):
        self.write(self.record("claude-opus-5-5", agent="parent"),
                   self.record("claude-haiku-5-5", session="other-session"),
                   self.record(), self.record("claude-fable-5-1", tool="toolu_other"))
        before = self.path.read_bytes(), self.parent.read_bytes()
        self.assertEqual(claude_context(self.payload), {
            "model": "claude-sonnet-5-5", "reasoning_effort": "high"})
        self.assertEqual(before, (self.path.read_bytes(), self.parent.read_bytes()))

    def test_new_call_uses_changed_model_and_effort(self):
        self.write(self.record(), self.record("claude-opus-5-5", tool="toolu_next"))
        self.assertEqual(claude_context(self.payload)["model"], "claude-sonnet-5-5")
        self.payload.update(tool_use_id="toolu_next", effort={"level": "medium"})
        self.assertEqual(claude_context(self.payload), {
            "model": "claude-opus-5-5", "reasoning_effort": "medium"})

    def test_direct_child_path_and_optional_effort(self):
        self.payload["transcript_path"] = str(self.path)
        del self.payload["effort"]
        self.assertIsNone(claude_context(self.payload)["reasoning_effort"])

    def test_native_hook_can_adjust_non_command_arguments(self):
        self.payload["tool_input"].update(timeout=3000, description="Load guard instructions")
        self.payload["model"] = "claude-opus-5-5"
        self.assertEqual(claude_context(self.payload)["model"], "claude-sonnet-5-5")

    def test_missing_identity_paths_model_and_call_do_not_fall_back(self):
        for field in ("session_id", "agent_id", "tool_use_id", "transcript_path"):
            with self.subTest(field=field):
                payload = {**self.payload, field: ""}
                self.assertRaises(ContextError, claude_context, payload)
        for records in [[], [self.record(tool="old")], [self.record(model=None)],
                        [self.record(agent="parent")], [self.record(session="parent")]]:
            self.write(*records)
            with self.subTest(records=records), self.assertRaises(ContextError):
                claude_context(self.payload)
        self.path.unlink()
        self.assertRaises(FileNotFoundError, claude_context, self.payload)

    def test_foreign_and_relative_paths_are_rejected(self):
        for path in ("relative.jsonl", str(self.parent.with_name("other.jsonl")),
                     str(self.path.with_name("agent-other.jsonl"))):
            with self.subTest(path=path), self.assertRaises(ContextError):
                claude_context({**self.payload, "transcript_path": path})
        self.assertRaises(ContextError, claude_context, {**self.payload, "agent_id": "../other"})

    def test_missing_and_partial_current_entry_never_uses_old_model(self):
        self.write(self.record(tool="old"))
        with self.path.open("a") as stream:
            stream.write(json.dumps(self.record())[:90])
        self.assertRaises(ContextError, claude_context, self.payload)
        self.write(self.record())
        with self.path.open("a") as stream:
            stream.write('{"type":')
        self.assertEqual(claude_context(self.payload)["model"], "claude-sonnet-5-5")

    def test_conflicting_models_and_mismatched_call_fail(self):
        self.write(self.record(), self.record(model="claude-opus-5-5"))
        self.assertRaises(ContextError, claude_context, self.payload)
        record = self.record()
        record["message"]["content"][0]["input"]["command"] = "some other command"
        self.write(record)
        self.assertRaises(ContextError, claude_context, self.payload)

    def test_unknown_identifiers_and_aliases_receive_core_without_guessing(self):
        for model in ("future-claude", "opus", "anthropic.claude-opus-5-5"):
            with self.subTest(model=model):
                self.write(self.record(model=model))
                result = render_instructions(**claude_context(self.payload))
                self.assertEqual(result["model"], model)
                self.assertIsNone(result["profile"])

    def test_hook_delivers_full_instructions_and_never_overrides_model_manually(self):
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "PostToolUse")
        self.assertEqual(json.loads(output["additionalContext"]), render_instructions("claude-sonnet-5-5", "high"))
        self.assertNotEqual(self.cli(None, "--model", "claude-opus-5-5").returncode, 0)

    def test_failure_feedback_and_unrelated_commands(self):
        self.path.unlink()
        result = self.cli()
        output = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(output["decision"], "block")
        self.assertIn("review unperformed", output["reason"])
        self.assertNotIn("hookSpecificOutput", output)
        for changes in ({"tool_input": {"command": "echo unrelated"}},
                        {"tool_name": "Read"}, {"hook_event_name": "PreToolUse"}):
            result = self.cli({**self.payload, **changes})
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))

    def test_missing_profile_is_reported_as_unperformed(self):
        from claude_hook import main
        from io import StringIO
        output = StringIO()
        with patch("sys.stdin", StringIO(json.dumps(self.payload))), patch("sys.stdout", output), \
                patch("sys.stderr", StringIO()), patch("sys.argv", ["claude_hook.py"]), \
                patch("claude_hook.render_instructions", side_effect=FileNotFoundError("missing profile")):
            self.assertEqual(main(), 0)
        self.assertIn("missing profile", json.loads(output.getvalue())["reason"])


if __name__ == "__main__":
    unittest.main()
