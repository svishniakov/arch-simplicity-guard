# Architecture Simplicity Guard

Reviews architecture and implementation plans for unnecessary abstractions, infrastructure, credentials, and acceptance checks. Suggests simpler solutions that preserve current requirements and component responsibilities.

Runs a reviewer subagent independently or works within Agent Flow. Prefers the parent model and reasoning settings, with a fallback to the harness defaults. Selects instructions for the executing model, using its OpenAI, Claude, or Kimi family profile when no exact profile exists. Instructions are written in Russian.

## Install

Requires Node.js, Git, and Python 3.10+.

```sh
npx skills add svishniakov/arch-simplicity-guard
```

Add `-g` for a global installation. Setup: [Codex](references/codex.md), [Kimi Code](references/kimi-code.md). [Claude Code requires a hook and remains experimental](references/claude-code.md); it has not been tested in a live Claude Code session.

## Use

Ask your agent to use `arch-simplicity-guard` to review a plan or architecture decision. Provide the requirements and relevant context.

```text
Use $arch-simplicity-guard to review the plan below against its requirements.
Identify unnecessary mechanisms and suggest simpler alternatives that preserve
the requirements. Explain any blocking findings. Do not edit files.

Requirements: [paste requirements]
Plan: [paste plan or provide its path]
```
