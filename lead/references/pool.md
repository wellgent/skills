# The pool triage

Headers: `FLOW.md`, "The triage" and stage 2.
A request to work through a project's open issues enters here: you sort every open issue once, write it up as one **triage report**, then work the result to a clean board in your own order.
The board holds only scheduled work. Nothing is parked: every issue in scope ends in a batch, a spec, a client decision that turns it into one of those, or a drop.

## 1. Scope and input

- **Scope:** every open issue on the project tracker, except the issues of an open spec or iteration, the sub-issues of a batch in flight, and issues the input names as left out.
  List each exclusion with its reason in the report.
- **Input:** when the input names a classification of the issues (a research record, an earlier report), it is the triage as it stands, and you do not re-read the pool.
  Otherwise sort each issue by the two questions of [triage](triage.md), from the issue and the code it touches.
  A ticket that turns out misfiled leaves its batch by conflict exit, as any ticket does.

## 2. The four classes

- **Batch:** related tickets grouped by surface or module, about ten tickets or 400 changed lines, each group one landing per [triage](triage.md), "Batches".
- **Spec:** groups whose fix needs a design. Judge each group against the notable bar in `GLOSSARY.md`: a notable group becomes a spec issue you open on the grill-then-build path; a group below the bar is dropped. Both lists go in the report.
- **Decide:** tickets that need a client decision (user-visible behaviour with real alternatives, money). They go into one request at the start, holding only what you cannot decide; you decide the rest yourself and list the rulings under "Decided by the lead". Tickets waiting on the request carry `needs-human`.
- **Drop:** closed with `wontfix` and one comment naming the reason class and, for an Audit finding, its finding id.

## 3. The triage report

1. Write the report from `templates/artifacts/triage-report.md` as one comment on the pool's lead-input issue: per ticket its class and a one-line reason, the batches in landing order, and the counts per class.
   It is done when every issue in scope appears exactly once.
2. `flow ledger triage <owner>/<repo> --link <report comment url> batch=<n> spec=<n> decide=<n> drop=<n> scope=<n>`; commit and push the ledger.
3. The report comment is the client's FYI: no veto window, so execution starts at once. The client reverses any line whenever seen; a reversal is a decision row with `--reverses`, and a reopened drop is triaged again.

## 4. Execution, in your order

1. Open the decide request per [requests](rounds.md). Each answer turns its tickets into batch tickets, a spec or drops; remove `needs-human` as it does.
2. Close the drops.
3. Open the batch issues and land them one by one per [landing](landing.md), in the order of value you judge:
   user-facing defects by surface first, then tooling and dead code, then duplication.
   Test-gap tickets land only on a test harness the project keeps: after the spec that settles the harness, or dropped with it.
4. Open each notable spec when its turn comes and take it through [shape](shape.md) and [spec](spec.md).
5. A finding that leaves a batch by conflict exit, and every issue that arrives while the pool runs, is an intake: triage it on its own.

Run as many landings in parallel as Readiness's usage and load lines allow.

## 5. Close

The pool is done when every issue in scope has landed, been dropped, or belongs to a spec that has released.
Post one closing comment on the lead-input issue with the final counts per class and the landings, close it, and append `flow ledger lead <owner>/<repo> <this session's id>`; commit and push the ledger.

A future Audit keeps the board this way: it files one issue per picked batch, one per picked spec and a bug ticket per picked escaped defect, and nothing for the rest ([audit](audit.md)).
