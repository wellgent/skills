---
name: brain-routines
description: "The framework every brain maintenance routine runs on: the routine manifest and its crons, the runner with its lease, heartbeat, run update and alerts, the apply script and its guards, and needs-attention issues with the reply loop. Use when building, registering, running or debugging a routine."
---

# Brain Routines

A **routine** is one scheduled, unattended job inside a **workflow** (health, review, relevance, core, summary), each workflow with its own Discord channel.
Every routine is a cron of the host's main agent, registered from the brain's **routine manifest**.
Mechanical routines are **command jobs** with no model turn; judgment routines are **agentTurns** where the agent judges and `apply.py` writes.

Every brain value (repo, paths, channels, agent, owner) lives in `config.json`.
The code is cross-checked against the shared-core reference copy in wellgent/skills `templates/brain/ops/brain-infra/skills/brain-routines/`.

## The manifest

`ops/brain-infra/routines.json` lists the routines with a `timezone` for every schedule.
Each routine has:

- `id`, `workflow`, `kind` (`command` or `agentTurn`), `schedule` (a 5-field cron expression), `skill` (the skill directory under `ops/brain-infra/skills/` that owns its code), `model` (`null` for command jobs).
- Command jobs: `run`, the step argv with its script path relative to the skill directory, and optional `sync_lock: true` to hold the reconciler's sync lock around the whole step.
- agentTurns: `thinking` (the effort, by the routing rule: high for writes, highest for deletions, merges and judges).
- Optional `timeout_seconds` and `enabled`.

After changing the manifest, push it, wait for the published copy, then on the host run `python3 <published>/ops/brain-infra/skills/brain-routines/scripts/routine.py sync`.
Sync makes the crons (declaration key `<brain>-routine-<id>`) match the manifest, removes crons whose routine left it, and links each routine's skill into the agent workspace.
`sync --check` reports drift without changing anything and exits 1 on drift.
A new skill also goes on the main agent's skill allowlist and its workspace link is committed in the runtime repo.

## Scheduling

Every routine takes the one maintenance lease, so the slots are what keeps scheduled runs from waiting on each other.
Place a slot by these rules:

- **Space by the worst case.** A routine starts no earlier than the previous routine's slot plus that routine's `timeout_seconds` plus 5 minutes (a killed turn's lease lives 300 s past its timeout), minus the lease wait (`timing.lease_wait_seconds`, 30 minutes by default). Then a scheduled run never fails on the lease, even after a predecessor that ran to its timeout. Typical runs are far shorter than their timeouts, so on a normal day no scheduled run waits at all.
- **Order by data.** The purge runs before the nightly cycle, so the cycle works on the purged index. The change review follows the nightly cycle and the brain's intake crons. Weekly relevance follows the review. The doctor follows them, so its deadman checks the night's heartbeats the same morning. The core check and the weekly eval come last. The weekly summary runs after the week's last review, relevance and eval runs.
- **Keep out of 02:00-02:59 local time.** Daylight-saving changes skip or repeat that hour.
- **Count the wait in the timeout.** A routine's wait for the lease runs inside its own cron timeout, so a routine that can wait keeps a timeout covering the wait plus its work.

The deadman reads each routine's due time from its slot, timeout, lease wait and grace, so a slot change needs no deadman change.
`routine.py status` shows each routine's last run time in seconds; check a slot against those durations and the timeouts.

## A run

Every run, of either kind, goes through the same lifecycle:

1. **Begin.** Take the brain maintenance lease (one routine at a time, granted in arrival order; a crashed run's lease is taken over at expiry; a run still waiting after `timing.lease_wait_seconds` fails), reset the maintenance clone to `origin/main` (wiped leftovers are reported), and run the reply loop for the workflow.
2. **Work.** The routine's step runs from the published copy and writes only to its run directory and, through `apply.py`, the maintenance clone; every write into the published copy pauses publication. Steps that run `gbrain sync`, `gbrain embed` or a full doctor hold the sync lock (`routinelib.sync_lock(cfg)`).
3. **End.** Post the run update to the workflow channel, page `#ops-alerts` for a partial run, write the heartbeat (`<state_dir>/heartbeats/<id>` and `<state_dir>/routines/<id>.json`), release the lease.

- **Command job.** The cron runs `routine.py run <id>`, which does all three. The step gets `ROUTINE_ID`, `ROUTINE_RUN_ID`, `ROUTINE_RUN_DIR`, `ROUTINE_WORKFLOW` and `BRAIN_MAINTENANCE_REPO`, and can `import routinelib`. It reports by writing `$ROUTINE_RUN_DIR/result.json`: `{"status": "ok" | "partial", "summary": "<one line>", "counts": {"<silent-tier item>": n}}`. A non-zero exit is a failed run.
- **agentTurn.** The turn runs `routine.py begin <id>` (prints the run id and run dir), builds its packet, judges, applies with `apply.py --run <run_id>`, and finishes with `routine.py end <run_id> --status ok|partial|failed --summary "<one line>" --counts '<json>'`. The turn ends with `NO_REPLY`; the run update is the only output.

## Run update

One message per run in the workflow channel: a status line (ok, partial or failed, with the duration and summary), silent-tier counts, each applied change with its commit link, the revert command for page deletions and moves, needs-attention items filed or resolved, notes, and alert sends that failed since the last update.
A run with nothing to report posts one line.
The update is built from the run journal (`$ROUTINE_RUN_DIR/journal.jsonl`), which `apply.py` and the needs-attention helpers fill; a step adds to it with `routinelib.journal(cfg, run_id, 'note' | 'problem', text=...)`. A `problem` makes the run partial.

## Alerts

- A failed command job exits non-zero and its cron `failureAlert` pages `#ops-alerts` (after 1 failure, one alert per incident, 24 h cooldown). An errored or timed-out turn pages the same way.
- The runner pages a partial run, and an agentTurn that ends `failed`, itself: once per fingerprint per day (`routinelib.alert`).
- A failed send is logged and listed in the next run update, including cron failure alerts OpenClaw could not deliver.
- The health workflow checks every heartbeat against its routine's schedule; the reconciler checks the health routine's heartbeat through its `deadman` list.

## Apply

`scripts/apply.py` is the only way a routine writes the brain.
It takes structured verdicts (NOOP, ADD, UPDATE, DELETE, MOVE, FLAG); the verdict format is in its docstring.
Each applied verdict is one commit by the maintenance writer, pushed at the end of the batch; the output lists the commit links.

Guards, each rejecting the verdict with its reason:

- the page's `sha256` matches the packet it was judged from, so give each page one verdict per batch;
- the old or anchor span occurs exactly once;
- ADD, UPDATE and span DELETE cite evidence quotes found in the cited files, and every number or date the new text introduces appears in a cited quote;
- the **tripwire**: when page deletions and archive moves would take more than `tripwire_share` of an area in one run, that area's are held and a needs-attention issue offers to apply them.

A MOVE (archive or restore, with `status`) and a page DELETE repair every inbound link in the same commit: a move repoints them, a delete unlinks them.
An archive move drops the page from the frontmatter lists that hold live subjects only, which `active_lists` in `config.json` names per top-level directory.
Every other link and path value is repointed to `archive/`.

## Needs attention

An item a routine cannot settle becomes one issue on the brain repo, labelled `needs-attention` and `workflow:<workflow>`, assigned to the owner, deduped by a `<!-- fingerprint: <routine>:<key> -->` marker.
File it with `routinelib.file_attention` or a FLAG verdict: the finding, why the routine could not settle it, the evidence, numbered options each with an action, and the recommended option.
Actions are `{"type": "close"}` or `{"type": "command", "argv": ["scripts/<x>", ...]}` run from the filing routine's skill directory (or the one an optional `"skill"` names) with `ATTENTION_ISSUE`, `ATTENTION_OPTION` and `ATTENTION_REPLY`; a command may print a last-line JSON `{"note", "commits"}`.

The **reply loop** runs at the start of each run of the workflow.
It reads the owner's latest reply after the framework's last comment, takes a leading number or "option N", runs that option's action, comments the result with its commits and closes the issue.
A reply it cannot read gets one comment asking for the number; a failed action leaves the issue open and makes the run partial, and the next run retries it.
Reconciler rescue issues (`reconciler-rescue:<branch>`, workflow health) carry no option actions; their options are built in: 1 lands the branch's changes on `main` through the maintenance clone, 2 deletes the branch.

## Operating

- `routine.py status` prints the lease, the runs queued for it and each routine's last run.
- Force a run with `openclaw cron run <job id>`; `openclaw cron runs <job id>` shows the history.
- Run directories live in `<state_dir>/runs/` for 14 days, with `run.json` (its final `status` and `summary` once the run ends), `journal.jsonl`, the step's `result.json` and each apply output.
