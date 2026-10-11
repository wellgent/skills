# Alignment before Build

Headers: `FLOW.md`, stages 3 to 5.
Two paths run here: the design note for a one shot that touches a hard-to-reverse edge, and the spec's stages for a grilled feature.
Both hand to [landing](landing.md) at Build.
After every run-end report: append the row (`flow ledger run`), read the artifact, check the stage's quality bar, then take the next step here.

## The design note

For a ticket whose change is small and touches a hard-to-reverse edge (`<target>` is the ticket).

1. Write the design note from `templates/artifacts/design-note.md` as a comment on the ticket: the edge, the behavioural contracts at it with examples in literal values, covering the three cases (one per combination of the stored rows the operation decides from, the value past every bound, browser-only behaviour as observable cases), and the migration or production write with the line that governs it.
   A new hard-to-reverse call gets an ADR on a `design/<ticket>` branch, in the format `domain-modeling` gives.
2. `flow spawn system-design-second <target> --note "<templates/artifacts/second-opinion-note.md, filled>"`, naming the latest Audit report's path (or `none`) and the note's link.
3. Merge the second opinion into the note's comment: each sentence it changed, with the new wording, under "Second opinion".
   Where you keep your wording against the opinion, say why in the same place.
4. `flow ledger stage system-design <target> done <comment link>`, then [landing](landing.md) with the note's link in Build's `--note`.

## A spec through its stages

One spec is one issue on the project tracker (`<target>` is `<owner>/<repo>#<spec>`) whose body is the spec brief Shape wrote, and one integration branch.

### 1. UX design

Only when the brief names a user-visible surface with real alternatives. Otherwise `flow ledger stage ux-design <target> skipped --reason "<no surface | one way to show it>"`.

1. `flow spawn ux-design <target>`.
2. Answer the designer's questions by kind: the spec's intent is yours, as product owner; gaps in `DESIGN.md` are yours, from the code; audience, brand and tone (`PRODUCT.md`) are the client's, once per project, in a request.
3. When the designer reports its options, put them to the client as a design question per [requests](rounds.md) and send the pick back.
4. Done at the run-end report: the chosen prototype branch and the UX notes comment on the spec issue.

### 2. System design

1. `flow spawn system-design <target> --note "Audit report: <path | none>"`.
2. The architect posts the record and asks for approval with `flow ask`.
   `flow spawn system-design-second <target> --note "<templates/artifacts/second-opinion-note.md, filled>"` on every record, and merge the second opinion into the record's comment yourself, each changed sentence with its new wording.
3. Approve the record when all four hold: the second opinion is merged, every hard-to-reverse call has an ADR, behavioural contracts with literal examples covering the three cases exist wherever the spec touches authorization, money or data integrity, and the data model serves every state in the UX notes.
   Otherwise answer the architect's session with what is missing.
4. Re-ask the two questions of [triage](triage.md) on the approved record: a spec that turned out small is de-escalated to a ticket carrying the record as its design note.

### 3. Plan

1. Write the spec with `to-spec`, its template unchanged, replacing the brief as the issue body and linking the UX notes and the design record.
   Append `flow ledger stage plan <target> done <issue link>`.
2. `flow spawn grooming <target>`.
   The groomer sends its proposed breakdown with `flow ask` before it publishes; judge it against step 3 and reply.
3. Approve the ticket graph when every contract example and every UX state is covered by a ticket, each ticket names the contract examples it implements, and blocking edges serialize every pair of tickets that cannot run in parallel.
4. Then [landing](landing.md), with the spec as the target.
