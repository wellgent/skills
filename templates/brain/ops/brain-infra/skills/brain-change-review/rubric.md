# Change Review Rubric

The judge reads one batch packet and returns one verdict list.
The goal is **coherence**: after the day's changes, every page an agent reads tells the same current truth.

## Reading a batch

For each target, read the full page and its diff from the maintenance clone (`repo` in the packet), then the neighbours that bear on what changed.
A neighbour's `why` says how it was found: a page that still carries an old phrase, a semantic neighbour, or a one-hop link.

Triage each target first:

- **cosmetic** (formatting, links, citations, wording): only its lint findings need a verdict.
- **additive** (new facts, a new page): check the neighbours for statements the new facts make stale, and the target for claims its neighbours already contradict.
- **claim-changing** (a value replaced): check every `propagation` hit and the neighbours for the old claim.

A target with `stale_compiled_truth` has timeline evidence newer than its compiled truth: bring the compiled truth above `<!-- timeline -->` up to that evidence.

## The contradiction rule

Two statements conflict only when both cannot be true at once, about the same attribute of the same entity at the same time.

- Explicit evidence decides: a dated, cited statement that the old state ended, was replaced or moved.
- Recency alone settles nothing. A newer page, a later `updated` date or a bigger number is no evidence.
- Different times are no conflict: an older timeline row stays as the record of its date.
- Authority runs from {{owner}}'s own statements, to cited primary sources, to synthesis.

When the evidence settles it, edit. When it does not, FLAG with an option per outcome.

## Verdicts

One verdict per page per batch; a page with nothing to do needs none, and NOOP is the default.

- **UPDATE** replaces a stale statement with the current one: on a neighbour that still carries the old claim, or in compiled truth that lags its timeline.
- **ADD** inserts text after an anchor span, for a missing current fact the evidence states outright.
- **DELETE** with `old` removes a span the evidence shows is no longer true and that holds nothing worth keeping.
- **FLAG** opens a needs-attention issue: a conflict the evidence cannot settle, a duplicate page or an entity that seems to have left {{owner}}'s world, or a change to the schema, page types, directory layout or resolver rules.
- **NOOP** records that a page was judged and is fine.

Page deletions, merges and archive moves belong to the relevance routine; FLAG them.
Records (pages of class `records`) are evidence of their period: a record target gets only its own lint repaired, and records are never edited as neighbours.
Pages marked `"editable": false` in the packet are context.

## Writing an edit

- `old` and `after` are exact text copied from the file, unique in it; a sentence or a full bullet is the usual unit.
- `new` states current truth in the page's own style, with a `[Source: ...]` citation carried over from the evidence.
- `evidence` quotes the exact text that justifies the edit, with its page path; every number and date in `new` appears in a quote or in `old`.
- `summary` is the commit subject after the area scope `apply.py` puts in front: what is now true, in a few words.
- `reason` is one sentence naming the evidence.
- Lint repairs cite the page itself: a missing `title` from its H1, a placeholder date from a dated row, an empty section removed.

Write current truth: the page states what is, and the history lives in its timeline and in Git.

## FLAG options

Each option has a `label`, an optional `detail`, and an optional `verdict`: the UPDATE, ADD or span DELETE that option means, written exactly like an edit verdict (no `sha256` needed).
When {{owner}} replies with that option, the next run applies its verdict against the page as it is then.
An option without a verdict closes the issue.
Give a `fingerprint` that names the pages and the attribute (`<page-slug>:<attribute>`), so the same conflict never files twice, plus `title`, `finding`, `why`, `evidence` (quotes with paths), `recommended` (the option number) and `recommended_reason`.
