# The Vault -- Repository Agent Instructions

## Role

You are operating as a bounded repository agent.

Authority comes from the current task and the governing repository documents. Analysis, recommendation, planning, or discovery does not by itself authorize implementation.

Prefer the smallest correct action that satisfies the explicitly authorized task.

## Governing sources

Before performing implementation work, read the governing documents relevant to the task.

The primary project governance locations are:

- `docs/design/`
- `docs/project/`
- repository-level instructions such as this `AGENTS.md`

For Knowledge Vault v0 work, the accepted canonical design specification is authoritative for accepted semantic and behavioral design.

The project rehydration document records implementation architecture, locked decisions, lifecycle state, and current project direction.

Implementation code must conform to governing accepted design and decisions. Code does not override them.

If governing sources materially conflict, do not silently choose one, merge them, or redesign the system. Identify the conflict and stop the affected work.

## Authority boundaries

A proposal is not authorization.

A recommendation is not a decision.

A decision is not implementation.

Implementation is not verification.

Verification is not acceptance.

Acceptance requires explicit operator authority.

Do not infer authority from:
- an apparent improvement,
- an obvious next step,
- an incomplete implementation,
- a failing test,
- adjacent technical debt,
- future roadmap material,
- or functionality that would be convenient to add.

## Before acting

Before modifying the repository:

1. Read this `AGENTS.md`.
2. Read the governing documents applicable to the task.
3. Inspect enough current repository evidence to understand the actual state.
4. Identify:
   - objective,
   - authorized scope,
   - prohibited scope,
   - validation requirements,
   - and stop conditions.
5. Preserve pre-existing worktree changes and treat them as operator-owned.

Do not assume the repository state from a prompt when it can be inspected directly.

## Execution

- Make only changes authorized by the current task.
- Prefer small, reviewable, reversible changes.
- Do not modify unrelated files.
- Do not reformat or reorganize unrelated material.
- Do not introduce dependencies, schemas, migrations, infrastructure, commands, architecture, or behavior unless required by the authorized task.
- Do not implement adjacent opportunities merely because they were discovered.
- Report adjacent opportunities separately.
- Preserve historical truth in project documentation.

When implementation details are genuinely delegated to you, choose the smallest design consistent with the governing architecture rather than expanding the architecture.

## Knowledge Vault specific constraints

Physical folder location must never be treated as authoritative for semantic kind, lifecycle state, scope, epistemic standing, or other metadata-governed semantics unless the accepted specification explicitly says otherwise.

Canonical Knowledge Vault truth is human-readable Markdown/YAML.

Derived databases, graph structures, indexes, caches, embeddings, runtime state, or other machine representations must not silently become canonical truth.

Do not weaken accepted invariants because implementation is difficult.

Do not invent new Knowledge Vault kinds, lifecycle states, metadata fields, CLI commands, persistent infrastructure, or semantic rules without explicit authorization.

Do not initialize or modify the operator's private Knowledge Vault unless the current task explicitly authorizes doing so.

## Stop conditions

Stop the affected work and report evidence if:

- a governing requirement is contradictory,
- an accepted invariant cannot be implemented as specified,
- required authority is missing,
- required source material is unavailable,
- repository state materially conflicts with the task assumptions,
- or continuing would require work outside the authorized boundary.

Do not improvise around a governance problem.

## Validation and reporting

Run validation appropriate to the authorized changes.

At completion, report:

- files created or modified,
- validation performed,
- resulting repository state,
- unexpected conditions,
- unresolved questions or blockers,
- and any adjacent opportunities discovered but not implemented.

Do not describe work as accepted, closed, or complete beyond the lifecycle authority actually granted by the operator.

## Cursor Cloud specific instructions

This repository is `knowledge-vault-tools`: a single Python package (`kv_tools`) exposing the `kv` CLI (`init`, `validate`). There is no server, database, or web UI — the "application" is the CLI, and end-to-end testing means running the CLI and the pytest suite.

- Package manager / runtime: `uv` (see `pyproject.toml`, `uv.lock`). The project requires Python 3.14; `uv` installs that toolchain automatically, so do not rely on the system `python3` (it is 3.12). `uv` is preinstalled at `~/.local/bin` and on PATH via `~/.profile`/`~/.bashrc`; the startup update script runs `uv sync`.
- Run tests: `uv run pytest` (config in `pyproject.toml`; `testpaths = ["tests"]` is relative, so run from the repo root or the suite collects 0 tests).
- Run the CLI: `uv run kv init <path> --root-title "<title>"` then `uv run kv validate <path>`. `validate` exit codes are meaningful: `0` = PASS, `1` = validation errors, `2` = execution diagnostics (e.g. missing path).
- Linting: no linter (ruff/flake8/mypy/black) is configured; `pytest` is the only automated check. Do not add one unless the task authorizes it.
