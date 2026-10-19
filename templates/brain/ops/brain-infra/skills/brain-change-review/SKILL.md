---
name: brain-change-review
description: "The daily change review of the brain: each day's changed pages judged against their one-hop links, backlinks and semantic neighbours, with guarded edits, needs-attention flags and judge-miss tracking. Use when running the review-daily routine, or when debugging or tuning the change review."
---

# Brain Change Review

The **review** workflow keeps the brain coherent after each day's writes.
Its routine `review-daily` is an agentTurn of the main agent on the `brain-routines` framework, reporting to `#brain-review`.
Code writes, the model judges: `scripts/review.py` builds every packet with zero LLM calls, and every edit goes through the review guards and then `apply.py`.

Scope comes from the relevance model (`{{relevance_model}}`), set in `config.json` `areas`:

{{review_scope}}

## The `review-daily` routine

Run every command with the paths below; `S` is `{{host_home}}/{{name}}/ops/brain-infra/skills`.

1. **Begin.** `python3 $S/brain-routines/scripts/routine.py begin review-daily` prints the run id; it takes the maintenance lease and applies {{owner}}'s replies on open review issues.
2. **Prep.** `python3 $S/brain-change-review/scripts/review.py prep --run <run_id>` queues every page changed since the last run by any writer except the maintenance writer, plus pages carried over from earlier runs.
3. **Rubric.** Read `$S/brain-change-review/rubric.md` once; it governs every verdict.
4. **Batch loop.** Repeat until `next` prints `"done": true`:
   1. `review.py next --run <run_id>` prints the batch number and the packet path.
   2. Read the packet and judge every target under the rubric, reading full pages from the packet's `repo`, the maintenance clone.
   3. Write the verdict list to the packet's `verdicts_file` as `{"verdicts": [...]}`; the formats are below.
   4. Run the packet's `apply` command and read its output. The batch is done when that command has run, whatever it applied or refused.
5. **Finish.** `review.py finish --run <run_id>` checks judge misses, measures the load, and runs `routine.py end`, which posts the run update. Pass `--status failed --summary "<what broke>"` when a step failed and the run cannot finish its batches.
6. End the turn with `NO_REPLY`; the run update is the only output.

Verdict shapes (the full contract is the `apply.py` docstring in `brain-routines`):

```json
{"op": "UPDATE", "path": "people/x.md", "old": "<exact text>", "new": "<text>", "evidence": [{"path": "companies/y.md", "quote": "<exact text>"}], "summary": "<commit subject>", "reason": "<one sentence>"}
{"op": "ADD", "path": "...", "after": "<exact anchor text>", "new": "<text to insert after it>", "evidence": [...], "summary": "...", "reason": "..."}
{"op": "DELETE", "path": "...", "old": "<exact span>", "evidence": [...], "summary": "...", "reason": "..."}
{"op": "NOOP", "path": "..."}
{"op": "FLAG", "fingerprint": "...", "title": "...", "finding": "...", "why": "...", "evidence": [...], "options": [{"label": "...", "detail": "...", "verdict": {"op": "UPDATE", ...}}], "recommended": 1, "recommended_reason": "..."}
```

`sha256` is optional; `apply` fills it from the packet.

## The packet

Each target carries its diff since it was queued, its authors, `lint` findings (minus the rules in `lint_ignore`, which other workflows own), `stale_compiled_truth` (newest timeline date against the last change above `<!-- timeline -->`), `propagation` (phrases the diff replaced that other pages still carry) and its `neighbours`.
Neighbours come in this order up to `neighbour_cap`: propagation hits, the top `semantic_hits` from `gbrain query` on the title and lede, then one-hop links and backlinks, editable areas first.
`pages` maps every page in the batch to its hash, class and `editable` flag.

## Guards

`review.py apply` refuses, before `apply.py` sees them:

- a page outside the packet, a second verdict on one page, an edit on a read-only page or on a record that is not the target;
- MOVE and whole-page DELETE, which belong to the relevance routine;
- an edit on a page the maintenance writer changed in the last `cooldown_days`: the page is queued again with this batch's targets as context, and is judged once its cooldown ends.

`apply.py` then enforces the framework guards: content hash, a unique span, cited quotes found, every new number or date cited, and the 20% tripwire.
There is no edit cap.

## Queue and overflow

`<state_dir>/review/state.json` holds the cursor (the last commit prep read) and the queue.
`next` stops handing out batches once the run has used `budget_seconds`, and everything left rolls to the next run.
A page that goes `max_attempts` batches without an apply leaves the queue and makes the run partial.

## Judge misses

A **judge miss** is a maintenance edit whose span another writer reverts or rewrites within 14 days.
`scripts/judge_misses.py` reads them from Git for every workflow, from the `Routine:` and `Op:` lines `apply.py` writes into each commit, and `finish` writes `<state_dir>/judge-misses.json` for the weekly brain summary.
When the review's own rate over the last 28 days passes 10%, `finish` files a needs-attention issue with the missed edits: option 1 keeps the routine as it is, option 2 holds the review writes.
While writes are held, runs judge and report but apply nothing, and an open issue offers the release (`review.py hold --off`).

## Load

`prep` and `finish` read the subscription quota windows and credits from `openclaw status --usage`, and `finish` reads this run's session tokens and the previous run's usage from OpenClaw.
The run update carries them as a `Load:` note, and `<state_dir>/review/load.jsonl` keeps one line per run.

## Operating

- Force a run with `openclaw cron run <job id>` (the job's declaration key is `{{name}}-routine-review-daily`).
- Each run directory keeps `review.json`, every `batch-<n>.json` packet, the verdict files and each apply output.
- Tune scope, batch size, budget and cooldown in `config.json`; the routine's schedule, model and effort are in `ops/brain-infra/routines.json`.
