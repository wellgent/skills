---
name: brain-relevance
description: "The relevance workflow's weekly routine: judge one area slice of the brain plus the inbox window, research retention and archive restores against the relevance model, and archive, delete, merge, update or flag through the guarded apply script. Use when running, forcing, debugging or extending the relevance routine, or when running the baseline pass."
---

# Brain Relevance

The relevance workflow keeps the brain to pages an agent working for the owner needs, under the brain's relevance model (`{{relevance_model}}`).
Its one routine, `relevance-weekly`, is an agentTurn on the `brain-routines` framework: `scripts/relevance.py` selects pages and guards verdicts with zero LLM, the agent judges under `rubric.md`, and `apply.py` writes.
Every brain value lives in `config.json` here and in the `brain-routines` `config.json`.

## What a run covers

- **One slice**: an area from `config.json` `slices`, taken from the queue first, then the `rotation` in order. A slice whose pages were not all judged runs again next week.
- **The standing rules**, every run: inbox items past the window, research records past retention or superseded by a newer run, and archived pages that show new interaction evidence.
- **A drift sample**: up to `drift_sample` slice pages with no other trigger whose compiled truth pairs a past date with time-sensitive wording.

`prep` picks a slice page when a trigger of the model fires: a terminal or in-place archived status, no interaction evidence for the trigger's window, a quiet open project or program, a retired tool with no news sources, a meeting whose subjects are all archived, or a knowledge page no live page links that has not changed for `knowledge_quiet` days.
Ledger areas, `tasks/`, `archive/` (except restore checks), READMEs and the paths in `not_reviewed` are never judged.
A page with an open relevance needs-attention issue waits for the owner's reply instead.

## The routine `relevance-weekly`

Scripts live at `{{host_home}}/{{name}}/ops/brain-infra/skills`; run each with `/usr/bin/python3`.

1. `brain-routines/scripts/routine.py begin relevance-weekly` - prints the run id and run directory.
2. `brain-relevance/scripts/relevance.py prep --run <run_id>` - builds `packet.json` and `brief.md` in the run directory and prints the slice and page count.
3. Read `brief.md` and `brain-relevance/rubric.md`. For each page in the brief, read the page in the published copy (and its linking pages when the verdict turns on them) and append one judgment line to `<run dir>/judgments.jsonl`. The judgment format is in the `relevance.py` docstring; only the brief's allowed verdicts pass.
4. `brain-relevance/scripts/relevance.py apply --run <run_id>` - checks the judgments, applies them through `apply.py` and prints what was applied, flagged, rejected or invalid, and which pages are not judged yet. Fix an invalid judgment and run `apply` again; settled pages are skipped. A verdict `apply.py` rejected stays rejected: the page is judged again on the next run of its slice.
5. `brain-relevance/scripts/relevance.py finish --run <run_id>` - writes the run record with the summary, every applied change with its commit link and the revert command for each deletion and move, and advances the rotation.

If a step fails and the run cannot finish, end it with `brain-routines/scripts/routine.py end <run_id> --status failed --summary "<what failed>"`.
End the turn with `NO_REPLY`: the run posts nothing, and the daily digest reports its changes and flags.

## Guards in code

On top of the `apply.py` guards (content hash, exact spans, cited quotes, numbers in the source, the tripwire per area per run):

- a judgment must name a page in this run's packet, one per page, with a verdict the brief allows for it;
- archive moves go to `archive/<kind>/<slug>.md` with `status: archived`, only for archivable kinds, a tool only when it is retired with no news sources, a meeting only when every linked subject is or becomes archived;
- a page a retrieval-eval case names is never archived, deleted or merged, and a page live pages cite as a source is never deleted or merged;
- a merge stays within one area and must state why both pages are the same subject; links to the merged page are repointed to the target;
- filing an inbox item creates a new page under `file_targets` with its type and status;
- a flag stores each option's verdicts, and choosing an option applies them on the next run (`relevance.py option`), still under the content hash.

The tripwire holds every deletion and archive move of an area when they pass `tripwire_share` of it in one run, and opens a needs-attention issue that offers to apply them.

## Operating

- `relevance.py status` prints the rotation, the queue and the last slices.
- `relevance.py queue <slice>...` puts slices ahead of the rotation; a slice can also be page paths, comma-separated, for a review on request. Queued slices do not move the rotation.
- Force a run with `routine.py force relevance-weekly`.
- `relevance-weekly` is deferrable: the `brain-routines` subscription guard holds it back while the shared quota window is too full. A deferred run leaves the rotation where it is, so its slice runs the following week.
- The baseline pass is this routine over every slice: queue them all and force runs until the queue is empty.
- Revert a change with the `git revert <sha>` from its run record, in a writer clone.
{{local}}
