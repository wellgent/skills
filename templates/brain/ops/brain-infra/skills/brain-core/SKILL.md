---
name: brain-core
description: "The core workflow: the daily cross-check of the brain and the main agent's workspace against the shared core, of the routine manifest against the main agent's crons, and of the brain's pinned skills against upstream. Core changes flow into the brain and the workspace; a departure, a cron drift or a pinned skill that changed upstream becomes a needs-attention issue. Use when running the core-check routine, answering one of its issues, or debugging it."
---

# Brain Core

The **shared core** is the placeholder-bearing reference copy of every file all brains carry, in the core repository that `config.json` names.
It has two **targets**, each under its own core root in `config.json` `targets`:

- **brain** (`templates/brain/`): the brain's own files, written from the maintenance clone.
- **workspace** (`templates/workspace/`): the brain section of the main agent's workspace `AGENTS.md`. The workspace is the parent of `brain-routines` `openclaw.workspace_skills`. It is written from its own maintenance clone `<workspace>-maintenance`, which the first run clones from the workspace's origin with the maintenance writer's name. Each run resets that clone to origin like the brain's.

Each target keeps its own concrete copies, and this workflow keeps them aligned with the core.
It runs on the `brain-routines` framework; its changes and needs-attention items reach the owner in the daily digest.

## The cross-check

`scripts/core.py align` fetches the core into `<state_dir>/core/` and judges every core file of each target by the core's own rules: `setup/setup-brain/core-check` at the core head, where placeholders match anything, blank lines are ignored and `AGENTS.md` is checked by section.

- **Aligned**: the file matches the core head.
- **Behind**: the file matches an older core version. The core change since that version is merged in with the target's values and the lines it adds at the core's local slots. All such changes land as one maintenance commit per target and run.
  - A core file the target lacks is added, filled with the values its other files agree on. The workspace also takes values from the brain.
  - A file the core dropped is removed when the target's copy still matches its last core text, and stays as a local file otherwise.
  - A line the core drops next to a local slot still matches the head as a local line. The file is behind when it also matches its base version and the base reading holds that line as a core line, so the removal flows out.
- **Departed**: the file matches no core version since the target's base commit, or the target lost a core file. Needs attention.
- **Conflict**: the file is behind, but the core change collides with local lines. Needs attention.
- **Unfilled**: a new core file needs a placeholder value no file carries. Needs attention.

A block placeholder right before a local slot takes the target's first paragraph there, and the rest are local lines, so a core line added between the two lands between them.

A deviating file that changed in the target or the core within `settle_minutes` waits for the next run, so a change that lands in both repositories is never caught halfway.

`ops/brain-infra/core-sync.json` records each target's **base**: the core commit the whole target last matched.
A file may match any core version from its target's base onward, which is how a newer core is told apart from a target that departed from it.
The routine moves a target's base forward, in a brain commit, whenever the whole target matches a new core head.

The workspace is the main agent's live working tree, so the routine never commits in it.
It commits and pushes from the workspace maintenance clone, then fast-forwards the live workspace when that is clean, on its branch and only behind its origin.
Otherwise the run record notes that the live workspace lags, and the next run tries again.

Then `routine.py sync --check` compares the routine manifest with the main agent's crons and workspace skill links.
Drift is needs attention, except within `settle_minutes` of a manifest change.

Last, the skills the brain pins in `skills-lock.json` from each source in `config.json` `pins` are compared with that source's `main`.
A pinned skill whose directory changed upstream since its pin is one needs-attention issue per brain, with each skill's change and its `SKILL.md` diff.
A newer upstream change edits the open issue to the new head rather than filing another.
After a hold, the brain is asked again only when a pinned skill changes upstream past the held head, which `<state_dir>/core-pins.json` records.

Open issues of this routine whose finding is gone are closed with a comment.

## The `core-check` routine

A daily agentTurn of the main agent.
The model only judges; `core.py` does every write.

1. Run `routine.py begin core-check` from the `brain-routines` scripts. It prints the `run_id` and `run_dir`.
2. Run `scripts/core.py align --run <run_id>` from this skill. It prints JSON.
   When `differs` is false, run its `end` command and end the turn with `NO_REPLY`.
3. Otherwise judge each finding from its evidence and `question`. A finding's `target` says whether it concerns the brain or the workspace.
   - **departure** - promote when the change is an improvement every brain should carry and holds nothing brain-specific; revert when it is a slip, brain-specific, or contradicts the rest of the core; settle by hand when it belongs in a new placeholder. Only the core's owner brain (`config.json` `owner`) is offered promote; in any other brain, an improvement every brain should carry is settled by hand and raised with the owner.
   - **conflict** - take the core text when the colliding local lines are trivial or restated by the core change; merge by hand when they carry brain facts.
   - **unfilled** - read the brain for each placeholder value the core file needs and pass them as `values`; recommend writing it by hand when a value cannot be found.
   - **drift** - sync, unless a cron differs on purpose (for example, disabled during an incident).
   - **pins** - bump when the upstream changes fit how the brain uses the skills; hold when one would break a convention the brain relies on; settle by hand when a pinned skill was renamed or removed upstream, since the core setup must learn the new name.
4. Write `[{"id": "<finding id>", "recommended": <option number>, "reason": "<clause>", "values": {...}}]` to `<run_dir>/verdicts.json`.
   The reason completes "Recommended: N, ..." and starts lowercase; `values` is for unfilled findings only.
5. Run `scripts/core.py flag --run <run_id> <run_dir>/verdicts.json`, which files one needs-attention issue per finding.
6. Run align's `end` command and end the turn with `NO_REPLY`.
   If `align` or `flag` fails, end with `--status failed --summary "<the error>"` instead.

Never edit the brain, the workspace or the core by hand in this turn.

## Options

The reply loop runs the owner's chosen option at the start of the next run.
Each file action takes `--target workspace` for a workspace file; the brain is the default.

- `core.py revert <path>` - restores the core text: the target's newest aligned version of the file, brought to the core head with its values and local-slot lines, where colliding lines give way to the core.
- `core.py promote <path>` - writes the target's text into the core template, turns placeholder values back into placeholders, and commits it to the core as the maintenance writer; every brain then takes it as a core change. Only the owner brain promotes, and only its maintenance writer has write access to the core repository; every other brain consumes the core.
- `core.py add <path> <values json>` - writes a new core file with the given values.
- `core.py crons` - runs `routine.py sync`.
- `core.py pins bump <source@sha>` - moves every pinned skill still upstream to that head through `npx skills` (remove, then add with `--agent codex --copy`), relinks `.claude/skills/`, and commits the skills and the lock; a skill gone upstream keeps its pin.
- `core.py pins hold <source@sha>` - keeps the pins and records the held head.
- A "by hand" option closes the issue; the next run files it again while the finding lasts.

Every write is one commit by the maintenance writer, listed in the run record with its revert command.

## Operating

- The core clone lives in `<state_dir>/core/` and is fetched at every run; `promote` commits and pushes from it.
- `config.json` holds the core repository, its branch, its owner brain, the core root of each target, the base file, `settle_minutes` and the pinned sources in `pins`.
- Fingerprints are `core-check:file:<path>` for brain files, `core-check:workspace:<path>` for workspace files, `core-check:crons` for cron drift and `core-check:pins` for the pinned skills.
- A manual cross-check from any checkout: `setup/setup-brain/core-check brain <checkout>` or `core-check workspace <workspace checkout>` in the core repository.
