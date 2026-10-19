# Cron Via Minions Convention

Autonomy And Maintenance convention for scheduled GBrain-backed agent work.

This file is included so managed brain skillpacks track upstream GBrain direction, but scheduled work should be reviewed under Autonomy And Maintenance, not Agent Access.

## Rule

Scheduled agent work should run through a durable job surface when the install supports it.

For GBrain Minion-enabled installs, cron should submit a Minion job rather than launching an untracked ad hoc agent turn.

## Why

Minion-backed cron gives:

- restart durability
- inspectable job history
- progress and transcript state
- idempotency keys for overlapping schedule slots
- a clean place to steer or retry work

## Conservative default

If Minions are not deliberately enabled, keep existing host cron routines simple, explicit, and observable:

- use one purpose per cron entry
- log to a known path
- use locks/idempotency for recurring jobs
- alert on failure
- avoid autonomous write/fix behavior without approval boundaries

## Setup boundary

Do not convert existing host cron to Minions just because this convention exists.

Convert only after an Autonomy And Maintenance review answers:

- which jobs should survive restarts
- which handlers are registered and tested
- what approval boundary applies to writes/fixes
- how failures alert the owner
- how job state is inspected

## Related

- `skills/conventions/subagent-routing.md`
- `skills/gbrain-advisor/SKILL.md`
