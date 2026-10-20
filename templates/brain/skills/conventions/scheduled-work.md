# Scheduled Work Convention

Convention for recurring work on the brain: maintenance, checks and any other job that runs on a schedule.

## Rule

Every recurring job that reads or writes the brain is a routine.
A routine is an entry in the brain's routine manifest `ops/brain-infra/routines.json`, run on the `brain-routines` framework as a cron of the brain host's main agent.

- A mechanical job is a command routine with no model turn.
- A job that needs judgment is an agentTurn routine: the agent judges, and `apply.py` writes under code guards.
- The routine's skill and scripts live in the brain under `ops/brain-infra/skills/`.
- A routine is added, changed or removed by a manifest change landed on `main`, followed by `routine.py sync` from the published copy. The agent's crons are never edited by hand.

Brain work is never scheduled any other way: no host crontab entry, no Minion job submitted from a cron, and no agent cron outside the manifest.

## What every routine gets

- the brain maintenance lease, so two routines never run at once
- a run record on the host after every run, with its changes and needs-attention items reported in the daily digest in `#brain-review`
- a heartbeat that the health workflow checks against the schedule
- failure paging to `#ops-alerts`, once per incident
- needs-attention issues with options for anything the routine cannot settle

## Related

- `ops/brain-infra/skills/brain-routines/SKILL.md`
- `skills/conventions/subagent-routing.md`
