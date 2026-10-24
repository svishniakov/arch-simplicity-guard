# Architecture Simplicity Guard

An agent skill for reviewing architecture decisions and implementation plans for unnecessary complexity. It asks whether each substantial mechanism serves a current requirement or a realistic risk, and whether a simpler approach would preserve the same requirements, data protection, contracts, and responsibilities.

Use it when designing architecture, reviewing a proposed solution, or revising an overcomplicated plan. Routine local edits do not require this review.

## What it checks

- **Architecture:** abstractions, dependencies, services, storage, queues, caches, compatibility layers, and configuration options.
- **Failure handling:** whether retries, fallbacks, and recovery have a defined failure scenario, acceptable behavior, and stopping condition.
- **Infrastructure and access:** whether new environments, roles, credentials, certificates, or network components justify their operational cost and preserve permission boundaries.
- **Acceptance criteria:** whether blocking checks detect actual requirement violations without rejecting valid work or depending unnecessarily on neighboring components.

The result is a conclusion with specific findings and any limits on the assessment. Blocking findings identify the requirement, disputed mechanism, evidence, consequences, and what would resolve the issue. The skill does not create separate complexity scores or tracking documents.

A review request does not authorize edits. The skill follows the host agent's permissions and workflow; it does not start Agent Flow or create an additional reviewer role on its own.

## Supported models

The shared instructions can be used by agents that support `SKILL.md`. The following models have additional guidance in this repository:

| Model | Recognized model IDs | Guidance |
| --- | --- | --- |
| GPT-6 Astra | `gpt-6-astra` | [GPT-6 Astra](references/gpt-6-astra.md) |
| GPT-6.1 Sol | `gpt-6.1-sol` | [GPT-6.1 Sol](references/gpt-6.1-sol.md) |
| Kimi K3 | `kimi-k3`, `k3`, `k3-256k` | [Kimi K3 and K3.1 Pro](references/kimi-k3.md) |
| Kimi K3.1 Pro | `kimi-k3.1-pro`, `k3.1-pro` | [Kimi K3 and K3.1 Pro](references/kimi-k3.md) |
| Kimi K3.1 Pro Highspeed | `kimi-k3.1-pro-highspeed`, `k3.1-pro-highspeed` | [Kimi K3 and K3.1 Pro](references/kimi-k3.md) |

Model selection is an instruction to the agent, not an executable router. When the environment provides an exact model ID, the agent reads the matching supplement. For other or unknown models, it uses only the shared instructions. The skill does not guess the model or change its reasoning effort.

These adaptations have not been independently evaluated on model tasks. The skill instructions and reference files are currently written in Russian; this README is in English.

## Installation

The commands below require Git and GitHub CLI (`gh`). Choose the location used by your agent. Clone the entire repository so the relative links to `references/` remain valid.

### Codex: all projects

```sh
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
gh repo clone svishniakov/arch-simplicity-guard \
  "${CODEX_HOME:-$HOME/.codex}/skills/arch-simplicity-guard"
```

### Kimi Code: all projects

Kimi Code supports the shared user skills directory:

```sh
mkdir -p "$HOME/.config/agents/skills"
gh repo clone svishniakov/arch-simplicity-guard \
  "$HOME/.config/agents/skills/arch-simplicity-guard"
```

See the official [Kimi Code skill documentation](https://moonshotai.github.io/kimi-cli/en/customization/skills.html) for discovery rules and custom locations.

For another compatible agent, place the repository in that agent's documented skills directory. Start a new session after installation if the skill is not visible.

The destination must not already contain an installation. If it does, inspect it before replacing anything; the clone command will not update an existing directory.

## Usage

In Codex, invoke the skill by name and provide the decision or plan to review:

```text
Use $arch-simplicity-guard to review this implementation plan.
Check whether the proposed mechanisms, infrastructure, and acceptance
criteria are necessary. Report concrete findings. Do not edit files.
```

In Kimi Code:

```text
/skill:arch-simplicity-guard Review the current architecture plan for unnecessary complexity. Do not edit files.
```

Provide the current requirements, relevant code or contracts, and known environment constraints. When important facts are unavailable, the skill should identify the affected part of the assessment rather than invent assumptions or expand the review to the entire project.

## Repository contents

- [SKILL.md](SKILL.md): shared review criteria and conditions for loading model guidance.
- [agents/openai.yaml](agents/openai.yaml): Codex display metadata and default invocation prompt.
- [references/](references/): model guidance and the [source instruction](references/architecture-simplicity-gate-source.md) used to prepare adaptations.

New model adaptations should start from the source instruction and the model developer's official recommendations. Keep shared behavior in `SKILL.md`, place model-specific guidance in `references/`, and add its exact IDs to the selection list. Distinguish documented recommendations from project-specific choices.
