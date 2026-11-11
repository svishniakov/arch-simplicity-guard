# Architecture Simplicity Guard

Reviews architecture and implementation plans for unnecessary abstractions, infrastructure, credentials, and acceptance checks. Suggests simpler solutions that preserve current requirements and component responsibilities.

Plain text rules with no scripts: the agent applies them in its own session, on the model and reasoning settings of that session, inside Agent Flow, foxmorrow or a regular chat. Instructions are written in Russian.

## What it checks

* Architecture: abstractions, dependencies, services, storage, queues, caches, compatibility and configuration options, and retry or fallback logic without a current requirement.
* Infrastructure and protection: new environments, credentials, roles and safeguards when existing ones suffice or the threat is not realistic.
* Verification and acceptance: failure conditions that reject correct work, and test scope beyond the affected behavior, its dependencies and specific risks.

For each blocking finding the agent names the place, the original requirement, the questioned mechanism and what would resolve it. Without blocking findings it accepts the decision and may still suggest a simpler alternative.

## Contents

* `SKILL.md`: when and how to apply the guard.
* `references/core.md`: the rules the agent applies.
* `references/architecture-simplicity-gate-source.md`: the original instruction that `core.md` is derived from; read it only when revising the rules.

## Install

Requires Node.js and Git.

```sh
npx skills add svishniakov/arch-simplicity-guard
```

Add `-g` for a global installation.

## Use

Ask your agent to use `arch-simplicity-guard` to review a plan or architecture decision. Provide the requirements and the relevant context.

```text
Use $arch-simplicity-guard to review the plan below against its requirements.
Identify unnecessary mechanisms and suggest simpler alternatives that preserve
the requirements. Explain any blocking findings. Do not edit files.

Requirements: [paste requirements]
Plan: [paste plan or provide its path]
```
