from __future__ import annotations

import json
import re
from pathlib import Path


def current_context(kimi_home: Path, session_id: str, agent_id: str) -> dict:
    for name, identity in (("session_id", session_id), ("agent_id", agent_id)):
        if not isinstance(identity, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", identity):
            raise ValueError(f"Kimi requires a native {name}")
    session_dir = None
    with (kimi_home / "session_index.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            if not line.endswith("\n"):
                break
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError("Invalid Kimi session index entry")
            if record.get("sessionId") == session_id:
                session_dir = None if record.get("deleted") else record.get("sessionDir")
    if not isinstance(session_dir, str) or not session_dir:
        raise ValueError("Kimi session has no directory in its native index")
    directory = Path(session_dir)
    if not directory.is_absolute() or not directory.resolve().is_relative_to((kimi_home / "sessions").resolve()):
        raise ValueError("Kimi session directory is outside native sessions")
    wire = directory / "agents" / agent_id / "wire.jsonl"
    if not wire.resolve().is_relative_to(directory.resolve()):
        raise ValueError("Kimi agent journal is outside its session")

    active_turn = None
    context = None
    with wire.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.endswith("\n"):
                break
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError("Invalid Kimi event")
            kind = record.get("type")
            if record.get("agentId", agent_id) != agent_id:
                continue
            if kind == "agent.turn.started":
                active_turn = record.get("turnId")
                context = None
            elif kind in {"agent.turn.ended", "turn.ended"} and record.get("turnId") == active_turn:
                active_turn = context = None
            elif kind == "llm.request" and active_turn is not None and record.get("kind") == "loop":
                step = record.get("turnStep")
                if step is not None and not str(step).startswith(f"{active_turn}."):
                    continue
                if record.get("agentId") != agent_id:
                    continue
                context = record
    if context is None:
        raise ValueError("Kimi agent has no model request for its active turn")
    model = context.get("model")
    if not isinstance(model, str) or not model or model.strip() != model:
        raise ValueError("Kimi current request has no valid model identifier")
    effort = context.get("thinkingEffort")
    return {"model": model, "reasoning_effort": effort if isinstance(effort, str) and effort else None}
