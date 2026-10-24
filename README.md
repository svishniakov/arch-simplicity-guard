# Architecture Simplicity Guard

Reviews architecture and implementation plans for unnecessary abstractions, infrastructure, credentials, and acceptance checks. Suggests simpler solutions that preserve current requirements and component responsibilities.

Works independently or within Agent Flow. Selects model-specific instructions automatically. Instructions are written in Russian.

## Install

Requires Node.js, Git, and Python 3.10+.

```sh
npx skills add svishniakov/arch-simplicity-guard
```

Add `-g` for a global installation. Codex is supported; [Claude Code support is experimental and requires a hook](references/claude-code.md).

## Use

Ask your agent to use `arch-simplicity-guard` to review a plan or architecture decision. Provide the requirements and relevant context.
