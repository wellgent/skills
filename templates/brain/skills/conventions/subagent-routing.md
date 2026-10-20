# Subagent Routing Convention

Convention for choosing native runtime subagents versus durable GBrain Minion jobs.

It guides the owner's Minion decision and gates no other work.

## Default posture

Read the brain owner's current Minion preference when available:

```bash
cat ~/.gbrain/preferences.json 2>/dev/null
```

Expected modes:

- `off` - do not suggest Minions
- `pain_triggered` - use native subagents until durability pain appears
- `always` - route background agent work through Minions

If the preference is missing, treat `pain_triggered` as the conservative default.

## Pain-triggered switch signals

Suggest Minions when one or more of these recur:

- gateway/runtime restart loses task state
- long-running work exceeds normal session comfort
- parallelism above three child agents is needed
- the user asks for progress tracking, pause/resume, or durable transcripts
- background work keeps dropping or becoming hard to inspect

## Inline work stays inline

Keep work inline when it is:

- a single quick tool call
- read-only and short
- a real-time user question
- safer to inspect directly than queue

## Boundaries

- Native subagents are fine for normal bounded investigations.
- Minions are for durable background work that should survive restarts and have inspectable job state.
- Do not flip `minion_mode` without explicit owner direction.

## Related

- `skills/conventions/scheduled-work.md`
{{local}}
