---
name: brain-alignment
description: "The daily alignment of the brain: each day's changed pages judged against their one-hop links, backlinks and semantic neighbours, with guarded edits and needs-attention flags. Use when running the alignment-daily routine, or when debugging or tuning the alignment."
---

# Brain Alignment

The **alignment** workflow keeps the brain coherent after each day's writes.
Its routine `alignment-daily` is an agentTurn of the main agent on the `brain-routines` framework; its applied edits and flags reach the owner in the daily digest.
Code writes, the model judges: `scripts/alignment.py` builds every packet with zero LLM calls, and every edit goes through the alignment guards and then `apply.py`.

Scope comes from the relevance model (`{{relevance_model}}`), set in `config.json` `areas`:

{{alignment_scope}}

## The `alignment-daily` routine

Run every command with the paths below; `S` is `{{host_home}}/{{name}}/ops/brain-infra/skills`.

1. **Begin.** `python3 $S/brain-routines/scripts/routine.py begin alignment-daily` prints the run id; it takes the maintenance lease and applies {{owner}}'s replies on open alignment issues.
2. **Prep.** `python3 $S/brain-alignment/scripts/alignment.py prep --run <run_id>` queues every page changed since the last run by any writer except the maintenance writer, oldest change first, after the pages carried over from earlier runs.
3. **Rubric.** Read `$S/brain-alignment/rubric.md` once; it governs every verdict.
4. **Batch loop.** Repeat until `next` prints `"done": true`:
   1. `alignment.py next --run <run_id>` prints the batch number and the packet path.
   2. Read the packet and judge every target under the rubric, reading full pages from the packet's `repo`, the maintenance clone.
   3. Write the verdict list to the packet's `verdicts_file` as `{"verdicts": [...]}`; the formats are below.
   4. Run the packet's `apply` command and read its output. The batch is done when that command has run, whatever it applied or refused.
      Its commit links are the receipt: the reconciler indexes every push, so the batch needs no further verification.
5. **Finish.** `alignment.py finish --run <run_id>` runs `routine.py end`, which writes the run record.
   The status is `ok` by default: refused verdicts, flags and pages left in the queue are normal outcomes the run record holds.
   Pass `--status failed --summary "<what broke>"` only when a command failed and the run could not finish its batches.
6. End the turn with `NO_REPLY`; the run posts nothing.

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

`alignment.py apply` refuses, before `apply.py` sees them:

- a page outside the packet, a second verdict on one page, an edit on a read-only page or on a record that is not the target;
- MOVE and whole-page DELETE, which belong to the relevance routine;
- an edit on a page the maintenance writer changed in the last `cooldown_days`: the page is queued again with this batch's targets as context, and is judged once its cooldown ends.

`apply.py` then enforces the framework guards: content hash, a unique span, cited quotes found, every new number or date cited, and the 20% tripwire.
There is no edit cap.

## Queue and overflow

`<state_dir>/alignment/state.json` holds the cursor (the last commit prep read) and the queue.
`next` hands out batches oldest first and stops at `max_pages` pages per run or once the run has used `budget_seconds`; everything left carries to the next run, and the run record says how many pages carried over.
A page that goes `max_attempts` batches without an apply leaves the queue and makes the run partial.

## Operating

- Force a run with `routine.py force alignment-daily`.
- Each run directory keeps `alignment.json`, every `batch-<n>.json` packet, the verdict files and each apply output.
- Tune scope, batch size, page cap, budget and cooldown in `config.json`; the routine's schedule, model and effort are in `ops/brain-infra/routines.json`.
- `alignment-daily` is deferrable: the `brain-routines` subscription guard holds it back while the shared quota window is too full, and its queue waits for the next run.
