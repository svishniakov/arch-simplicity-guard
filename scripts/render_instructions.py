#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from uuid import UUID


PROFILES = {
    "gpt-6-astra": "references/gpt-6-astra.md",
    "gpt-6.1-sol": "references/gpt-6.1-sol.md",
    "kimi-k3": "references/kimi-k3.md",
    "k3": "references/kimi-k3.md",
    "k3-256k": "references/kimi-k3.md",
    "kimi-k3.1-pro": "references/kimi-k3.md",
    "k3.1-pro": "references/kimi-k3.md",
    "kimi-k3.1-pro-highspeed": "references/kimi-k3.md",
    "k3.1-pro-highspeed": "references/kimi-k3.md",
    "claude-fable-5-1": "references/claude-fable-5-1.md",
    "claude-opus-5-5": "references/claude-opus-5-5.md",
    "claude-sonnet-5-5": "references/claude-sonnet-5-5.md",
    "claude-haiku-5-5": "references/claude-haiku-5-5.md",
}
SKILL_ROOT = Path(__file__).resolve().parents[1]


class ContextError(ValueError):
    pass


def valid_model(model: object) -> str:
    if not isinstance(model, str) or not model or model.strip() != model:
        raise ContextError("Current turn has no valid model identifier")
    return model


def current_context(codex_home: Path, thread_id: str) -> dict:
    try:
        UUID(thread_id)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ContextError("CODEX_THREAD_ID must identify the executing agent") from exc

    index = (codex_home / "state_5.sqlite").resolve()
    with closing(sqlite3.connect(index.as_uri() + "?mode=ro", uri=True)) as db:
        row = db.execute("SELECT rollout_path FROM threads WHERE id = ?", (thread_id,)).fetchone()
    if row is None or not isinstance(row[0], str) or not row[0]:
        raise ContextError("Executing thread has no rollout_path in the Codex index")
    rollout = Path(row[0])
    if not rollout.is_absolute() or not rollout.resolve().is_relative_to((codex_home / "sessions").resolve()):
        raise ContextError("Executing thread rollout is outside Codex sessions")

    own_session = False
    active_turn = None
    context = None
    with rollout.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.endswith("\n"):
                break
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ContextError("Invalid Codex event")
            kind = event.get("type")
            if kind not in {"session_meta", "event_msg", "turn_context"}:
                continue
            payload = event.get("payload")
            if not isinstance(payload, dict):
                raise ContextError("Invalid Codex context payload")
            if kind == "session_meta":
                if payload.get("id") == thread_id:
                    own_session = True
                    active_turn = context = None
            elif own_session and kind == "event_msg":
                if payload.get("type") == "task_started":
                    active_turn = payload.get("turn_id")
                    context = None
                elif payload.get("type") in {"task_complete", "turn_aborted"} and payload.get("turn_id") == active_turn:
                    active_turn = context = None
            elif own_session and kind == "turn_context" and active_turn and payload.get("turn_id") == active_turn:
                context = payload
    if context is None:
        raise ContextError("Executing agent has no context for its active turn")
    model = valid_model(context.get("model"))
    effort = context.get("effort")
    return {"model": model, "reasoning_effort": effort if isinstance(effort, str) and effort else None}


def render_instructions(model: str, reasoning_effort: str | None = None, skill_root: Path = SKILL_ROOT) -> dict:
    model = valid_model(model)
    profile = PROFILES.get(model)
    instructions = (skill_root / "references/core.md").read_text(encoding="utf-8")
    if profile is not None:
        instructions = instructions.rstrip() + "\n\n" + (skill_root / profile).read_text(encoding="utf-8")
    return {"model": model, "reasoning_effort": reasoning_effort, "profile": profile, "instructions": instructions}


def main() -> int:
    parser = argparse.ArgumentParser(description="Render simplicity instructions for this Codex agent's active model.")
    parser.parse_args()
    codex_home = Path(os.environ.get("CODEX_HOME") or str(Path.home() / ".codex")).expanduser()
    try:
        context = current_context(codex_home, os.environ.get("CODEX_THREAD_ID", ""))
        result = render_instructions(**context)
    except (ContextError, OSError, UnicodeError, sqlite3.Error, json.JSONDecodeError) as exc:
        print(f"arch-simplicity-guard: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
