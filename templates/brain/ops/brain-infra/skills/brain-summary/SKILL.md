---
name: brain-summary
description: "The weekly brain summary: one post per week in #brain-summary with the open needs-attention items and their recommended options, the routine health grid and subscription load, the week's maintenance changes by workflow, page counts per area, the ledger areas, the eval trend and judge misses. Use when running the summary-weekly routine, or when changing what the summary reports."
---

# Brain Summary

The **summary** workflow tells {{owner}} once a week what is in the brain and what the maintenance system did to it, sized for 15 to 30 minutes of reading and acting.
Its routine `summary-weekly` is an agentTurn of the main agent on the `brain-routines` framework, posting to `#brain-summary`.
Code states every fact: `scripts/summary.py` gathers the week with zero LLM calls and renders every section.
The agent writes only the narrative: a headline, the week's changes by workflow and a one-line gist per open needs-attention item.
The summary writes nothing to the brain.

## The `summary-weekly` routine

Run every command with the paths below; `S` is `{{host_home}}/{{name}}/ops/brain-infra/skills`.

1. **Begin.** `python3 $S/brain-routines/scripts/routine.py begin summary-weekly` prints the run id.
2. **Gather.** `python3 $S/brain-summary/scripts/summary.py gather --run <run_id>` writes the packet and prints its path, the `narrative_file` to write, the commit count per workflow, the commits the narrative `must_cite` and the open issue numbers.
3. **Write the narrative** from the packet into `narrative_file`, by the contract below.
4. **Check.** `summary.py post --run <run_id> --dry-run` prints the rendered summary, or `{"errors": [...]}`. Fix every error and rerun until it renders.
   When the narrative still fails after three attempts, use `post --fallback`, which renders the changes from commit subjects.
5. **Post.** `summary.py post --run <run_id>` posts the summary to `#brain-summary` and ends the run, which posts the one-line run update.
6. End the turn with `NO_REPLY`; the summary and the run update are the only output.

## The narrative

`narrative_file` is one JSON object:

```json
{"headline": "<1-3 sentences>", "workflows": {"<workflow>": ["<bullet>", "..."]}, "attention": {"<issue number>": "<gist>"}}
```

- **headline**: what {{owner}} most needs from this week, first what waits on {{owner}}, then anything not green, then the biggest change. At most 400 characters.
- **workflows**: one entry for every workflow in the packet's `changes`, at most 8 bullets each. Group commits by what they did and why, from their `subject` and `reason`: "archived four people whose engagements ended (...)", never one bullet per commit. Each bullet states the reason and cites its commits as `{sha}`, at most 12 per bullet; post turns them into commit links.
  Every archive move, restore and listed page deletion in `must_cite` is cited. Commits from {{owner}}'s replies (`owner_choice`) read as {{owner}}'s choices.
- **attention**: for each open needs-attention item, one plain sentence of what the issue is about, from its `finding`, so {{owner}} can decide without opening it. At most 200 characters. The recommended option is rendered from the issue itself.
- Cite an open issue as `{#n}`. Raw URLs are refused.

## What the summary reports

In posting order:

1. **Header**: the window (the 7 days before the run started) and the headline.
2. **Needs you**: every open `needs-attention` issue, oldest first, with its workflow, age, gist and recommended option parsed from the issue body.
3. **Routines**: a grid per manifest routine with scheduled runs due in the window, started runs (forced ones included), ok, partial and failed counts, runs the subscription guard deferred, runs the cron never started, and the last status.
   Failed counts the larger of the runs that ended `failed` and the cron's own errors, so a timed-out turn shows.
   Then the **subscription load**: the provider windows from OpenClaw (the last `<state_dir>/load.jsonl` reading when that fails), next to the points maintenance agentTurns moved each window in the week from their before and after readings in `load.jsonl`, token use of every maintenance agentTurn in the window from `openclaw cron runs`, the other agent crons, and the engine's own chat calls from `gbrain call get_usage`. The budget rules link issue `budget_issue`.
4. **Changes by workflow**: per workflow, the maintenance writer's commits counted by kind (archive move, restore, page deletion, span deletion, filing move, edit, other), then the narrative bullets.
5. **Brain**: markdown pages per area now and their change over the window, the ledger areas in `config.json` `ledger` with their commits by writer and last change, and the week's commits per writer.
6. **Search and judges**: the last `eval_runs` retrieval eval runs from `<state_dir>/eval/history.jsonl`, and the judge-miss rate per workflow from `<state_dir>/judge-misses.json`, recomputed when it is older than `judge_miss_max_age_hours`.

A data source that cannot be read becomes a "Missing data" line under the header and a journal problem, so the run ends partial and pages `#ops-alerts`.

## Operating

- Force a run with `routine.py force summary-weekly`.
- Each run directory keeps `packet.json`, `narrative.json` and the posted `summary.md`.
- Areas, ledger areas, window and narrative limits are in `config.json`; schedule, model and effort are in `ops/brain-infra/routines.json`.
