# Architecture Simplicity Guard

An agent skill that reviews architecture and implementation plans for unnecessary complexity: extra abstractions, services, infrastructure, credentials, and acceptance checks. It favors the simplest solution that preserves current requirements, data protection, and component responsibilities.

Includes model-specific guidance for GPT-6 Astra, GPT-6.1 Sol, Kimi K3, and Kimi K3.1 Pro, including Highspeed. A Python selector reads the executing Codex agent's actual model and returns the shared rules plus its matching profile. Other identified models receive the shared rules. Skill instructions are written in Russian.

The guard questions whether each substantial mechanism serves a current requirement, whether existing capabilities suffice, and whether its benefit justifies its operating cost. This includes credentials and deployment roles, defensive checks, abstractions, and acceptance conditions that reject valid work after unrelated changes.

## Install

Installation requires Node.js and Git. Execution currently supports Codex and requires Python 3.10+ with its standard library. Run in your project and select Codex:

```sh
npx skills add svishniakov/arch-simplicity-guard
```

To install globally for all projects:

```sh
npx skills add svishniakov/arch-simplicity-guard -g
```

## Use

Ask your agent to apply `arch-simplicity-guard` to a plan or architecture decision. Include the requirements and relevant code or context.

| Mode | Execution |
| --- | --- |
| Standalone | The parent starts one generic subagent with native model and reasoning inheritance. That subagent performs the review without further delegation. Agent Flow is not required. |
| Agent Flow | The assigned architect applies the guard while preparing or revising a decision. The existing independent reviewer checks the plan before dependent implementation and architecture-sensitive code before product QA. No extra guard agent is created. |

In both modes, the executor runs the selector inside its own session. The skill changes neither the model nor reasoning effort. Reviews do not authorize edits.

Example in Codex:

```text
Use $arch-simplicity-guard to review this implementation plan.
Identify unnecessary mechanisms and acceptance checks, explain each
finding, and suggest simpler alternatives. Do not edit files.
```

The existing task response or report states the conclusion, substantive findings, limitations, and selected model/profile. A blocking finding explains the requirement, the unnecessary mechanism, a direction for simplification, and what would resolve it. The author revises the decision and returns it for review before dependent implementation.

## How instruction selection works

1. Inside the executing agent, run `python3 <skill-directory>/scripts/render_instructions.py`.
2. The script resolves `CODEX_THREAD_ID` through the local Codex index and reads the latest active turn's actual model. Copied parent metadata in a full-history fork does not change the owner of that journal.
3. Code selects [shared criteria](references/core.md) plus one matching profile. The executor reads and applies the complete returned `instructions`.
4. A new review turn runs the selector again, so a model change does not reuse an old profile.

The JSON result contains `model`, `reasoning_effort` (when available), `profile` (a path relative to the skill, or `null`), and `instructions`. The script does not accept a manual `--model` override. Profile selection is deterministic; invoking and applying the instructions remains the agent's responsibility.

An identified model without a matching profile receives only the shared criteria. Missing runtime metadata or required instruction files produces a nonzero exit and leaves the dependent review unperformed. It does not silently fall back to generic instructions.

The reader uses `$CODEX_HOME`, or `~/.codex` when unset, and depends on Codex's internal `state_5.sqlite` and JSONL formats. It expects the current `task_started` and `turn_context` to be recorded before the agent executes the command. If those formats change, the reader needs an update. A plain terminal outside an active Codex turn cannot provide the required context.

Only Codex execution is implemented. Including Kimi model guidance does not imply support for the Kimi Code runtime. Model IDs and aliases are maintained in the selector's `PROFILES` table.

## Development

Run the behavior tests from the repository root:

```sh
python3 -B -m unittest discover -s tests
```

Tests use temporary fixtures and need no Codex account. They cover profile routing, missing metadata/files, full-history forks, turn changes, and refusal to use stale context. Validate actual inheritance and instruction delivery separately inside running Codex subagents.

To add a model, use the [original source instructions](references/architecture-simplicity-gate-source.md) and official guidance from its developer, following [SKILL.md](SKILL.md). Add the model-specific reference and update `PROFILES` and the routing tests. Keep shared criteria in `references/core.md` and the original source document unchanged. The source is for developing adaptations; ordinary reviews do not load it.
