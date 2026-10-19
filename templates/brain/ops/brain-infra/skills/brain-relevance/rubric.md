# Relevance rubric

How the `relevance-weekly` judge decides each page in the brief.
The model is `{{relevance_model}}`; entity admission and removal triggers are `{{entity_rules}}`; area rules are the area READMEs it indexes.

## The test

A page is relevant when an agent working for {{owner}}, now or within a foreseeable horizon, needs it to act correctly.

- Triggers in the brief only say why a page is up for review. Age never removes a page by itself.
- Read the whole page from the published copy before judging it, and the linking pages when the verdict turns on them.
- When the evidence does not clearly support a change, the verdict is `keep`, or `flag` when a change is likely but needs {{owner}}'s call.

## Verdicts

- **keep** - the page passes the test. The default.
- **update** - one exact span is now wrong: a time-sensitive statement whose date has passed, or a live entity's `status` (for example `active` to `dormant`). Quote the evidence from a brain page; every number and date in the new text must appear in the quote or the old span.
- **archive** - the subject was a real part of {{owner}}'s world and has left it. Only people, companies, projects, programs, retired tools with no news sources, and meetings whose linked subjects are all archived. The code moves the page to `archive/<kind>/`, sets `status: archived` and repairs every inbound link.
- **delete** - stale, junk, a duplicate with nothing of its own, an admission error, a record past retention, or inbox noise. Git history keeps it.
- **merge** - the page duplicates another page about the same subject. State in `same_subject` why both pages describe the same entity or mechanism, not merely a similar one; similarity proposes, judgment disposes. Carry anything only this page holds into the target with `update`.
- **restore** - an archived page whose subject is back: name the live `status`.
- **file** - an inbox item with a clear home: the new path, its page `type` and `status`.
- **flag** - a change is likely but the evidence does not settle which: give 2 to 4 options, each with the judgment it would apply (`keep` is a valid option), and the recommended one. {{owner}} answers with an option number and the next run applies it.

## Hard keeps

A page stays when it is load-bearing for an active project, program or open map ticket, when a retrieval-eval case references it, or when it is the sole provenance of a fact cited on a kept page.
The code refuses to remove an eval-case page and to delete or merge a page live pages cite as a source; load-bearing is the judge's call, read from the linking pages and the open tickets in the brief.

## Per kind

{{relevance_rules}}

## Writing the judgment

- One judgment per page, one JSON object per line in the run's `judgments.jsonl`.
- `reason` - one or two sentences naming the evidence: the trigger, the dates, the linking pages.
- `summary` - the commit subject after the area scope, in the present tense: what is now true, for example `<Name> moves to the archive: the <company> engagement ended`.
- Spans are copied exactly from the page; quotes are copied exactly from the cited page.
- New text carries its citations in the form the page already uses.
- A flag's `recommended_reason` completes "Recommended: N, ...": it starts lowercase and has no final period.
