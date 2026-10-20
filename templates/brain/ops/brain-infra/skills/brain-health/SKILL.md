---
name: brain-health
description: "The brain health workflow: the nightly derived-maintenance cycle, the daily purge, and the daily doctor with timeline repair, writer roster, entity lint, the routine deadman and the reconciler rollup, and the weekly retrieval eval. Use when reading a #brain-health run update, debugging a health routine, or changing what the health workflow checks or repairs."
---

# Brain Health

The **health** workflow keeps the index, embeddings and host machinery of the brain sound.
Its routines run on the `brain-routines` framework, command jobs except the retrieval eval agentTurn, listed in `ops/brain-infra/routines.json` with ids `health-*`, and each posts its run update to `#brain-health`.
The command steps live in `scripts/health.py`; health values live in `config.json`, and engine paths come from the `gbrain-host-reconciler` config.

## Routines

- **`health-nightly`** runs the `gbrain dream` phases in `nightly_phases` on the published copy. A phase passes only when its own entry reads `ok`; any other result fails the run.
- **`health-purge`** runs `gbrain pages purge-deleted --yes`, hard-deleting pages soft-deleted more than 72 h ago.
- **`health-doctor`** runs the checks below in order and posts one run update holding all of them.
- **`health-eval`** is the weekly agentTurn that verifies retrieval eval candidates, promotes them into a new set version and scores the set with `gbrain eval gate --qrels`. Its steps, the set and its alerts are in `eval/EVAL.md`.

The three command jobs hold the reconciler's `sync.lock` for the whole run (manifest `sync_lock`), because each writes the engine or reads it whole.

## The doctor run

1. **Timeline repair** (silent). Markdown is the record, so a timeline row with no bullet in its page is dropped from the database. `scripts/timeline-db-only.ts list` asks the engine's own classifier about one row at a time; `drop` deletes exactly those ids in one transaction that rolls back unless every id goes. Guards:
   - rows an earlier page version produced, and rows that cannot round-trip, are left alone;
   - more than `timeline_max_rows` rows in one run drops nothing and pages;
   - a dropped row is remembered for `timeline_memory_days`; one that comes back is kept and pages, since a writer regenerates it.
   The dropped rows are saved in the run directory as `timeline-dropped.json`.
2. **Doctor.** `gbrain doctor --json --budget-ms 0` with the brain's skills directory and nightly-cadence freshness hours. It pages on any `fail`, any non-ok check in `doctor.page` (`git_held_files`) and any check whose health is unknown at the entry budget. Checks in `doctor.ignore` (`harness_wiring`, `skill_currency`) are skipped by name. Other warnings are listed in one note.
3. **Writer roster.** `brain-transport/scripts/writer-roster-check` from the published copy; each finding pages.
4. **Entity lint.** The brain's `entity_lint` script, run with `bun` in the published copy. Pages that break the archive status rule (`status: archived` only inside `archive/`) are a counted note, left to the relevance workflow's archive moves. Every other lint error pages.
5. **Deadman.** For every enabled manifest routine, the heartbeat `<state_dir>/heartbeats/<id>` must be newer than its last scheduled run that should have finished (schedule plus timeout, lease wait and `deadman_grace_seconds`). A missing or older heartbeat pages, and so does a manifest routine with no cron. A routine is not due before its cron was registered.
6. **Reconciler.** Its `heartbeat_at` must be under `reconciler_stale_seconds` old, else it pages. `reconciler.py rollup --hours 24` becomes the daily reconciler note: publishes, imports, embeds, blocked ticks, alerts, rescues and restarts. Failed reconciler alert sends page.

A finding pages through the framework: the run ends partial and `#ops-alerts` gets one alert a day listing the findings.
A check that crashes becomes a finding and the others still run.

The reconciler watches this run in turn: its `deadman` config lists the `health-doctor` heartbeat, so a doctor that stops running pages from the reconciler.

## Operating

- Force a run with `routine.py force <id>`; `routine.py status` shows each routine's last run, and `<state_dir>/runs/<run_id>/` holds the raw `dream-*.json`, `purge.json` and `doctor.json`.
- Needs-attention issues labelled `workflow:health`, reconciler rescues included, get their reply loop at the start of every health run.
- Restoring dropped timeline rows: they are in the run's `timeline-dropped.json` for 14 days; the page text never held them.
