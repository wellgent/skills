# The flow command

`flow help` lists the commands and their arguments.
This page holds what the commands read and write, which no `--help` shows.

## The flow config

`flow spawn` reads `flow.json` from the driving brain: `$FLOW_CONFIG`, or the file in the current directory or a parent.
The template is [`templates/brain/flow.json`](../templates/brain/flow.json).

- `projects["<owner>/<repo>"].checkout`: where the project is checked out on this host. A spawned session starts there unless `--cwd` names a worktree.
- `projects["<owner>/<repo>"].card`: the project card's path in the driving brain. The lead reads it first.
- `projects["<owner>/<repo>"].iteration`: the open iteration, as the iteration map's issue number. `flow ledger` writes to that iteration's file.
- `harness.claude`, `harness.codex`: arguments every session of that harness starts with.
- `steps.<step>`: `model` and `effort`. The model's prefix picks the harness: `claude-*` runs in Claude Code, `gpt-*` in Codex. Model ids are full ids, never aliases.
- An empty step entry starts the lead's harness with no model or effort arguments, so the session runs on the host defaults the lead started from. When the lead runs on something else, `FLOW_LEAD_MODEL` and `FLOW_LEAD_EFFORT` in the lead's environment name it.

A session keeps its model for its whole life.
One stopped at a usage limit is asked to continue by each hourly tick and resumes on the same setting once the window resets.

## What a spawned session gets

- Its start prompt: the step, the target, the absolute path of its stage skill, the lead's herdr agent, and the two commands below.
- Its herdr name: `flow-<repo>-<step>-<issue>-<HHMMSS>`, a tab in the workspace `<repo>-flow`.
- `FLOW_LEAD`, `FLOW_STEP`, `FLOW_TARGET`, `FLOW_RUN` and `FLOW_HOME` in its environment.

A session talks to the lead with two commands:

- `flow ask "<question>"`, or `flow ask --conflict "<what disagrees>"` for a conflict exit. The lead answers with `herdr agent prompt <session name> "<answer>"`, and the session waits for that message.
- `flow report <outcome> <artifact link>` as its last act. The lead receives `run-end: <step> <target> <outcome> <link> <session id> (<session name>)`.

`flow spawn` exits 4 when the harness waits on a startup prompt of its own, such as folder trust.
The start prompt is kept and runs once the prompt is answered in the tab.
Each harness asks for folder trust once per repository per host: a worktree of a trusted checkout starts without it.

## What the gate reads

`flow gate` and `flow land` run in the directory where the spec's branch is checked out, with a clean working tree.
The gate reads three lines from the project's `docs/agents/dev-loop.md`:

```markdown
- **Check command:** `<command>`
- **Journey tests:** `<command>`
- **Protected paths:** `<glob>`, `<glob>`
```

The check command is required.
The protected paths extend the defaults in [`protected-paths`](protected-paths).

The gate result is JSON on stdout and in `<git dir>/flow/gate/<commit>.json`, with the check logs beside it: the commit and its tree, the check and journey results, the protected-change flags each with kind, file, line and text, and the verdict.

- `pass` (exit 0): the checks are green and no flag is open.
- `red` (exit 1): a check failed. The spec goes back to Build.
- `flagged` (exit 2): the checks are green and the protected-change script has flags. The lead judges each one, then re-runs with `--accept "<reason>"` or sends the spec back to Build.

Flag kinds: `check-config`, `test-deleted`, `test-removed`, `assertion-loss`, `test-skip`, `suppression`.
A suppression without a reason on its line says so in its text.
A loosened matcher is not detected by script; Review judges it.

## What land does

`flow land` needs a `pass` result for `HEAD`.
It rebases the branch when the main branch moved or the branch holds merge commits, so the main branch stays linear.
A rebase that leaves the tree identical to the gated one keeps the gate result; one that changes the tree exits 3, and the gate runs again on the rebased branch.
Then it pushes `HEAD` to the remote main branch as a fast-forward and brings the local main branch along.

## The tick

`flow tick arm` adds one hourly crontab entry for the lead session and `flow tick disarm` removes it.
Each tick asks sessions stopped at a usage limit to continue, then types `lead tick: check runs` into the lead's session.
It does nothing when the lead session does not exist.

## The ledger

`flow ledger` appends to `ledger/<repo>/<iteration>.jsonl` beside the flow config and never commits; the lead commits and pushes the file.
The rows, the cost rules and the two Retro triggers are in [`ledger/README.md`](../ledger/README.md).

- `flow spawn` keeps each run's spawn record, and `flow ask` each question and conflict exit, under `$FLOW_STATE` (default `~/.local/state/flow`). `flow ledger run` reads them, so it runs on the host the step was spawned on.
- `flow ledger run` takes the run-end line as the lead received it, in quotes.
- `flow ledger gate` reads the gate result from the project checkout named in the flow config.
- `flow cost` and `flow ledger fill` read transcripts from `~/.claude/projects` and `~/.codex/sessions` (`CLAUDE_CONFIG_DIR` and `CODEX_HOME` move them).
