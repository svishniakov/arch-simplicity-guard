#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from render_instructions import ContextError, render_instructions, valid_model


MARKER_COMMAND = "printf '%s\\n' 'arch-simplicity-guard:load'"


def is_guard_call(payload: dict) -> bool:
    tool_input = payload.get("tool_input")
    return (payload.get("hook_event_name") == "PostToolUse"
            and payload.get("tool_name") == "Bash"
            and isinstance(tool_input, dict)
            and tool_input.get("command") == MARKER_COMMAND)


def claude_context(payload: dict) -> dict:
    if not is_guard_call(payload):
        raise ContextError("Expected the guard's PostToolUse Bash event")
    for field in ("session_id", "agent_id", "tool_use_id"):
        value = payload.get(field)
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ContextError(f"Claude hook has no valid {field}")
    session, agent = payload["session_id"], payload["agent_id"]
    raw_path = payload.get("transcript_path")
    if not isinstance(raw_path, str) or not raw_path:
        raise ContextError("Claude hook has no transcript_path")
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        raise ContextError("Claude transcript_path must be absolute")
    child_name = f"agent-{agent}.jsonl"
    if path.name == f"{session}.jsonl":
        path = path.parent / session / "subagents" / child_name
    elif not (path.name == child_name and path.parent.name == "subagents"
              and path.parent.parent.name == session):
        raise ContextError("Claude transcript path does not identify this subagent")

    models = set()
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.endswith("\n"):
                break
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ContextError("Invalid Claude transcript entry")
            if (record.get("type") != "assistant" or record.get("sessionId") != session
                    or record.get("agentId") != agent):
                continue
            message = record.get("message")
            if not isinstance(message, dict) or not isinstance(message.get("content"), list):
                continue
            for block in message["content"]:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                if block.get("id") != payload["tool_use_id"]:
                    continue
                original_input = block.get("input")
                if (block.get("name") != "Bash" or not isinstance(original_input, dict)
                        or original_input.get("command") != MARKER_COMMAND):
                    raise ContextError("Claude tool call does not match the hook input")
                models.add(valid_model(message.get("model")))
    if len(models) != 1:
        raise ContextError("No unique model for this tool call in the subagent transcript; "
                           "the transcript may be delayed, disabled, or incompatible")
    effort = payload.get("effort")
    level = effort.get("level") if isinstance(effort, dict) else None
    return {"model": models.pop(), "reasoning_effort": level if isinstance(level, str) and level else None}


def main() -> int:
    argparse.ArgumentParser(description="Experimental Claude Code PostToolUse hook for the guard.").parse_args()
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ContextError("Expected a Claude Code hook JSON object")
        if not is_guard_call(payload):
            return 0
        result = render_instructions(**claude_context(payload))
    except (ContextError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        reason = f"arch-simplicity-guard: review unperformed: {exc}"
        print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
        print(reason, file=sys.stderr)
        return 0
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": json.dumps(result, ensure_ascii=False),
    }}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
