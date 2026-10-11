# The flow command

`flow help` lists the commands and their arguments.
This page holds what the commands read and write, which no `--help` shows.

## The flow config

`flow spawn` reads `flow.json` from the driving brain: `$FLOW_CONFIG`, or the file in the current directory or a parent.
The template is [`templates/brain/flow.json`](../templates/brain/flow.json).

- `tracker`: the driving brain's repository, where the request issues live.
- `projects["<owner>/<repo>"].checkout`: where the project is checked out on this host. A spawned session starts there unless `--cwd` names a worktree.
- `projects["<owner>/<repo>"].card`: the project card's path in the driving brain. The lead reads it first.
- `projects["<owner>/<repo>"].iteration`: the open iteration, as the iteration map's issue number, while a map runs. `flow ledger` writes to that iteration's file; without the entry, rows go to the month's file.
- `harness.claude`, `harness.codex`: arguments every session of that harness starts with.
- `steps.<step>`: `model` and `effort`. The model's prefix picks the harness: `claude-*` runs in Claude Code, `gpt-*` in Codex. Model ids are full ids, never aliases.
- `fallback.model`: the model a step stalled at a usage limit is respawned on, and the lead switches to when stalled itself.
- An empty step entry starts the lead's harness with no model or effort arguments, so the session runs on the host defaults the lead started from. When the lead runs on something else, `FLOW_LEAD_MODEL` and `FLOW_LEAD_EFFORT` in the lead's environment name it.

`flow spawn` remembers the config it used for the project's repository under `$FLOW_STATE` (default `~/.local/state/flow`), so `flow gate` and `flow land`, which run in a project worktree with no `flow.json` in reach, find the brain through it.

A session keeps its model for its whole life.
One stopped at a usage limit resumes on the same setting once the window resets; one stalled there for 30 minutes is respawned on the fallback model (see the tick).

## Returning at once

`flow spawn`, `flow gate` and `flow land` return as soon as their slow part is under way and deliver its result into the lead's session as one line, the way run-end reports arrive: `herdr agent prompt <lead> "<line>"`.
The lead is `FLOW_LEAD` inside a spawned step, the calling pane (`HERDR_PANE_ID`) in the lead's own session, or `--lead <agent>`.
`--wait` runs the slow part in the foreground instead and sets the exit code; outside herdr it is the only mode.

- `spawn: <step> <target> <run> started (pane <id>)`, `... blocked at startup: answer its prompt in pane <id> (...)`, or `... failed: <reason>`.
- `gate: <target> <verdict> <diff class> <result path>`.
- `health: <target> <commit> appended <n> measures: ...`, `... failed: <reason>`, or `... skipped: <reason>`.

## What a spawned session gets

- Its start prompt: the step, the target, the absolute path of its stage skill, the lead's herdr agent, and the two commands below.
- Its herdr name: `flow-<repo>-<step tag>-<issue>-<HHMMSS>`, at most 32 characters (the step tags are in `flow-spawn`; a long repo name is cut), a tab in the workspace `<repo>-flow`.
- `FLOW_LEAD`, `FLOW_STEP`, `FLOW_TARGET`, `FLOW_RUN` and `FLOW_HOME` in its environment.

A session talks to the lead with two commands:

- `flow ask "<question>"`, or `flow ask --conflict "<what disagrees>"` for a conflict exit. The lead answers with `herdr agent prompt <session name> "<answer>"`, and the session waits for that message.
- `flow report <outcome> <artifact link>` as its last act. The lead receives `run-end: <step> <target> <outcome> <link> <session id> (<session name>)`.

How the start can go, each reported in the `spawn:` line:

- The harness runs and took its start prompt: `started`. A session that goes straight to work runs past herdr's readiness wait, so herdr reports a timeout or an unknown name; `flow spawn` sees the harness in the pane, names it and reports `started`.
- The harness waits on a startup prompt of its own, such as folder trust: `blocked`. The start prompt is kept and runs once the prompt is answered in the tab. Each harness asks for folder trust once per repository per host (`flow trust` writes it); a worktree of a trusted checkout starts without it.
- The pane holds no agent after the wait: `flow spawn` closes the tab and starts once more in a fresh one; a second miss is `failed` with the reason, and the record carries it.

`--model <id>` and `--effort <level>` override the step's config entry for this run.
The spawn record under `$FLOW_STATE/runs/<run>.json` carries the model, effort, pane, tab and how the start went; `flow ledger run` reads it.

## What the gate reads

`flow gate` and `flow land` run in the directory where the target's branch is checked out, with a clean working tree.
The gate reads five lines from the project's `docs/agents/dev-loop.md`:

```markdown
- **Check command:** `<command>`
- **Journey tests:** `<command>`
- **Protected paths:** `<glob>`, `<glob>`
- **Surface paths:** `<glob>`, `<glob>`
- **Prose paths:** `<glob>`, `<glob>`
```

The check command is required.
The protected paths extend the defaults in [`protected-paths`](protected-paths).
A glob is matched against each changed file's full path and its file name, and `*` spans directories.

The **diff class** comes from the surface and prose lists over the files changed against the main branch:

- `prose-only`: every changed file matches a prose path. No Review, no QA.
- `no-surface-path`: no changed file matches a surface path. Review, no QA.
- `surface-path`: a changed file matches a surface path. Review and QA. A project with no surface-paths line gets this class for every diff that is not prose only, since the gate cannot prove otherwise.

The gate result is JSON on stdout and in `<git dir>/flow/gate/<commit>.json`, with the check logs beside it: the commit and its tree, the diff class with the file counts behind it, the check and journey results, the protected-change flags each with kind, file, line, text and its acceptance, and the verdict.

- `pass` (exit 0 with `--wait`): the checks are green and no flag is open.
- `red` (exit 1): a check failed. The target goes back to Build.
- `flagged` (exit 2): the checks are green and the protected-change script has open flags. The lead judges each one, then `flow gate <target> --accept "<reason>"` or sends the target back to Build.

Flags are judged once per target.
A flag's identity is its kind, file and text, without the line.
`--accept` records the reason against every open flag of the result on HEAD under `<git dir>/flow/accepted/<target>.json` and rewrites that result as passed; it runs nothing.
A later gate on the same target carries the flags already accepted (each with the commit it was accepted on) and is flagged only on new ones.

Flag kinds: `check-config`, `test-deleted`, `test-removed`, `assertion-loss`, `test-skip`, `suppression`.
A suppression without a reason on its line says so in its text.
A loosened matcher is not detected by script; Review judges it.

## What land does

`flow land` needs a `pass` result for `HEAD`.
It rebases the branch when the main branch moved or the branch holds merge commits, so the main branch stays linear.
A rebase that leaves the tree identical to the gated one keeps the gate result; one that changes the tree exits 3, and the gate runs again on the rebased branch.
Then it pushes `HEAD` to the remote main branch as a fast-forward and brings the local main branch along.

After the push it runs the **health check**: the scanner pass declared in the `## Scanner pass` section of `docs/agents/dev-loop.md`, one line per measure or group of measures,

```markdown
- `<measure>`: `<command>`
- `<measure>`, `<measure>`: `<command>`, `<command>`
```

one command per measure in the same order, each printing its number as the last line of its stdout.
The numbers go to the ledger with `flow ledger health <owner>/<repo> --commit <landed commit> <measure>=<number> ...`, and the `health:` line reports the row, a measure that gave no number, or a project with no scanner pass.
The commands' logs sit beside the gate results.

## The tick

`flow tick arm` adds one crontab entry for the lead session, running every 30 minutes with the flow config it found, and `flow tick disarm` removes it.
Each run does nothing when the lead session does not exist. Otherwise:

- Every `flow-` session that is not working and shows a usage-limit message is asked to `continue`, which resumes it once the window resets. One that has shown the message for 30 minutes is reported as `limit: <run> stalled <minutes> min ...` with the `flow spawn` command that respawns the step on the fallback model at the same effort and in the same directory; the lead runs it and ledgers the stalled run when its report arrives.
- The lead session itself, stalled for 30 minutes, is switched to the fallback model (`/model <fallback>` plus the confirmation Claude Code asks for) and asked to continue. A Codex lead is asked to continue only.
- Every open request issue (label `lead:round` on the config's tracker) whose last comment is newer than the previous tick is reported as `request: <url> "<title>" has a new comment by <login> at <time>`.
- Then `lead tick: check runs` nudges the lead.

First sightings of a limit and the previous tick's time live under `$FLOW_STATE/limits` and `$FLOW_STATE/ticks`; the last run's output is in `$FLOW_STATE/ticks/<lead>.log`.

## The ledger

`flow ledger` appends to `ledger/<repo>/<iteration>.jsonl` beside the flow config and never commits; the lead commits and pushes the file.
The rows and the cost rules are in [`ledger/README.md`](../ledger/README.md).

- `flow spawn` keeps each run's spawn record, and `flow ask` each question and conflict exit, under `$FLOW_STATE`. `flow ledger run` reads them, so it runs on the host the step was spawned on.
- `flow ledger run` takes the run-end line as the lead received it, in quotes.
- `flow ledger gate` reads the gate result from the project checkout named in the flow config.
- `flow ledger health` is what `flow land` runs for the health check row; `flow ledger triage` records the pool triage report; `flow ledger lead` costs a lead session (`--stage audit` or `retro` for an occasional flow's lead).
- `flow ledger bug` exits 2 for an escaped defect with an area; nothing runs on it but the lead's advise line.
- `flow ledger rollup` reports over the Retro window, every row since the last Retro row across the project's files.
- `flow cost` and `flow ledger fill` read transcripts from `~/.claude/projects` and `~/.codex/sessions` (`CLAUDE_CONFIG_DIR` and `CODEX_HOME` move them).

## The status view

`flow status <owner>/<repo>` prints the status view as Markdown and changes nothing.
It finds the flow config like the other commands, or through the configs `flow spawn` remembered, so it runs from any directory on a run host where a step of the project has been spawned.

- From the ledger: the window (the open iteration's rows, else the Retro window), each target with rows but no Release row, with its latest stage or gate result, and the cost split into steps and lead.
- From the spawn records and `herdr agent list`: the live `flow-` sessions of the project, each with its step, target, `working` or `idle`, the last question or conflict exit it sent, a usage limit (first seen by the tick under `$FLOW_STATE/limits`, or showing on its pane), and how long ago it started; the live sessions with no ledger row yet are counted against the cost.
- From the tracker with `gh`: the iteration map's title and state, the open `batch` issues of the project, and the open `lead:round` issues with their age, assignee and last comment. An unreachable tracker is said so on the line.

## The source log and the propagation check

- `flow sources` reads [`source-log.md`](../source-log.md), whose head describes the entry format, and prints one line per source: `same`, `changed`, `read` or `unknown`, the name, the version seen and the upstream's current one. It needs `gh` and `npm`; `FLOW_SOURCE_LOG` names another log.
- `flow sources seen <name> [<version>]` writes the Seen line with today's date and, on a skill source, the Pin line with the commit that version resolves to. It never commits.
- `flow ready` reads [`setup/requires.json`](../setup/requires.json) (the skills, labels and files a brain and a project must carry, the `docs/agents/dev-loop.md` lines the gate needs and the measures the scanner pass must name), the pins from the source log, and each `skills-lock.json`, where a pinned skill carries its commit as `ref`. Every `behind` line names its fix or the setup skill step that owns it.
- `flow trust` writes `hasTrustDialogAccepted` for the directory into Claude Code's `~/.claude.json` (`CLAUDE_CONFIG_DIR` moves it) and a `[projects."<dir>"]` table with `trust_level = "trusted"` into `~/.codex/config.toml` (`CODEX_HOME` moves it). The Claude Code key is undocumented state: when a release stops honouring it, `flow spawn` reports `blocked` and the prompt is answered once in the tab.
