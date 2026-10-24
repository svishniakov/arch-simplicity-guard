# Architecture Simplicity Guard

An agent skill that reviews architecture and implementation plans for unnecessary complexity: extra abstractions, services, infrastructure, credentials, and acceptance checks. It favors the simplest solution that preserves current requirements, data protection, and component responsibilities.

Includes model-specific guidance for GPT-6 Astra, GPT-6.1 Sol, Kimi K3, and Kimi K3.1 Pro, including Highspeed. Other models use the shared instructions. Skill instructions are written in Russian.

## Install

Requires Node.js and Git. Run in your project and select your coding agent:

```sh
npx skills add svishniakov/arch-simplicity-guard
```

To install globally for all projects:

```sh
npx skills add svishniakov/arch-simplicity-guard -g
```

## Use

Ask your agent to apply `arch-simplicity-guard` to a plan or architecture decision. Include the requirements and relevant code or context.

Example in Codex:

```text
Use $arch-simplicity-guard to review this implementation plan.
Identify unnecessary mechanisms and acceptance checks, explain each
finding, and suggest simpler alternatives. Do not edit files.
```
