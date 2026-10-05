# Shape

Header: `FLOW.md`, stage 2.
Shape turns the client's destination into spec briefs, one per slice, and runs for the whole iteration: a slice whose decisions are settled moves into its per-spec stages while later slices are still being shaped.

## Working the map

Drive the map with `wayfinder`. Only you edit the map body.

- **Research tickets** → one background subagent per ticket, in parallel, each running `research` and resolving its own ticket.
- **Grilling tickets** → a client [round](rounds.md), its questions in the `grilling` format.
- **A decision about what the user sees** is made on a coded prototype or live data, never on text.
  Open the slice's spec brief with that decision named as the UX design round's, and let the [UX design stage](spec.md) put its options to the client.
  You build no prototype yourself.
- **Work only a person can do** → a human-work issue per [rounds](rounds.md).
- A new domain term goes into the project's `GLOSSARY.md` through `domain-modeling`.
- A durable decision is written to the brain's pages for the project as the brain's `AGENTS.md` directs.

## Findings that arrive mid-iteration

Exploration findings, non-blocking Review and QA findings and Audit findings come to you; triage each with `triage`.

- A bug → a bug ticket on the project tracker with its origin spec, taken through the single-bug path in [spec](spec.md).
  Set the origin spec from `git blame` on the lines at fault, `unknown` when the cause predates the flow, and append `flow ledger bug` when the origin spec was already released.
- A product change → a ticket on the map, decided in a round.
- A structural problem → its own slice, whose spec starts at System design.

## Spec brief

A slice is ready when the client has decided every behaviour in it, each decision with its basis, and the only decisions left are the ones its UX design round will settle on prototypes.

Open the spec's issue on the project tracker with the brief from `~/repos/wellgent-skills/templates/artifacts/spec-brief.md` as its body, and add native blocking edges to the sibling specs it must follow.
Append `flow ledger stage shape <owner>/<repo>#<spec> done <issue link>`, then start the spec's stages per [spec](spec.md).
