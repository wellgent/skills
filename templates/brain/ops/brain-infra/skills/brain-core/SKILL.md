---
name: brain-core
description: "The core workflow: the daily cross-check of the brain against the shared core and of the routine manifest against the main agent's crons. Core changes flow into the brain; a brain departure or a cron drift becomes a needs-attention issue. Use when running the core-check routine, answering one of its issues, or debugging it."
---

# Brain Core

The **shared core** is the placeholder-bearing reference copy of every file all brains carry, under `templates/brain/` in the core repository that `config.json` names.
The brain keeps its own concrete copies, and this workflow keeps them aligned with the core.
It runs on the `brain-routines` framework and reports to the `core` workflow channel.

## The cross-check

`scripts/core.py align` fetches the core into `<state_dir>/core/` and judges every core file by the core's own rules: `setup/setup-brain/core-check` at the core head, where placeholders match anything, blank lines are ignored and `AGENTS.md` is checked by section.

- **Aligned**: the file matches the core head.
- **Behind**: the file matches an older core version. The core change since that version is merged in with the brain's values and the lines it adds at the core's local slots, and all such changes land as one maintenance commit per run.
  - A core file the brain lacks is added, filled with the values the brain's other files agree on.
  - A file the core dropped is removed when the brain's copy still matches its last core text, and stays as a brain-local file otherwise.
- **Departed**: the file matches no core version since the base commit, or the brain lost a core file. Needs attention.
- **Conflict**: the file is behind, but the core change collides with brain-local lines. Needs attention.
- **Unfilled**: a new core file needs a placeholder value no brain file carries. Needs attention.

A deviating file that changed in the brain or the core within `settle_minutes` waits for the next run, so a change that lands in both repositories is never caught halfway.

`ops/brain-infra/core-sync.json` records the **base**: the core commit the whole brain last matched.
A file may match any core version from the base onward, which is how a newer core is told apart from a brain that departed from it.
The routine moves the base forward, in its own commit, whenever the whole brain matches a new core head.

Then `routine.py sync --check` compares the routine manifest with the main agent's crons and workspace skill links.
Drift is needs attention, except within `settle_minutes` of a manifest change.

Open issues of this routine whose finding is gone are closed with a comment.

## The `core-check` routine

A daily agentTurn of the main agent.
The model only judges; `core.py` does every write.

1. Run `routine.py begin core-check` from the `brain-routines` scripts. It prints the `run_id` and `run_dir`.
2. Run `scripts/core.py align --run <run_id>` from this skill. It prints JSON.
   When `differs` is false, run its `end` command and end the turn with `NO_REPLY`.
3. Otherwise judge each finding from its evidence and `question`:
   - **departure** - promote when the brain's change is an improvement every brain should carry and holds nothing brain-specific; revert when it is a slip, brain-specific, or contradicts the rest of the core; settle by hand when it belongs in a new placeholder.
   - **conflict** - take the core text when the colliding brain lines are trivial or restated by the core change; merge by hand when they carry brain facts.
   - **unfilled** - read the brain for each placeholder value the core file needs and pass them as `values`; recommend writing it by hand when a value cannot be found.
   - **drift** - sync, unless a cron differs on purpose (for example, disabled during an incident).
4. Write `[{"id": "<finding id>", "recommended": <option number>, "reason": "<clause>", "values": {...}}]` to `<run_dir>/verdicts.json`.
   The reason completes "Recommended: N, ..." and starts lowercase; `values` is for unfilled findings only.
5. Run `scripts/core.py flag --run <run_id> <run_dir>/verdicts.json`, which files one needs-attention issue per finding.
6. Run align's `end` command and end the turn with `NO_REPLY`.
   If `align` or `flag` fails, end with `--status failed --summary "<the error>"` instead.

Never edit the brain or the core by hand in this turn.

## Options

The reply loop runs the owner's chosen option at the start of the next run:

- `core.py revert <path>` - restores the core text: the brain's newest aligned version of the file, brought to the core head with its values and local-slot lines, where colliding lines give way to the core.
- `core.py promote <path>` - writes the brain's text into the core template, turns placeholder values back into placeholders, and commits it to the core as the maintenance writer; every brain then takes it as a core change.
- `core.py add <path> <values json>` - writes a new core file with the given values.
- `core.py crons` - runs `routine.py sync`.
- A "by hand" option closes the issue; the next run files it again while the finding lasts.

Every brain write is one commit by the maintenance writer, listed in the run update with its revert command.

## Operating

- The core clone lives in `<state_dir>/core/` and is fetched at every run; `promote` commits and pushes from it.
- `config.json` holds the core repository, its branch and root, the base file and `settle_minutes`.
- A manual cross-check from any checkout: `setup/setup-brain/core-check brain <checkout>` in the core repository.
