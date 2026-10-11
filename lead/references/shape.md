# Shape

Header: `FLOW.md`, stage 2.
Shape turns the client's input into decided work: the triage path for a ticket, a spec brief for a grilled feature, a map when the grilling leaves fog.
It runs for the whole of a map: a slice whose decisions are settled moves into its per-spec stages while later slices are still being shaped.

## Grilling a spec

For a grill-then-build intake, the ticket's issue is the spec's issue; for a map's slice, open the spec's issue when the brief is ready.

- Grill with the `grilling` round format; the questions the client must answer go in a [request](rounds.md) linked from the spec issue, everything else you decide as product owner and list as FYI.
- Facts come from `research` in background subagents, never from the client.
- A decision about what the user sees is judged on text when the client can picture the choice from the question; when the options are visual or at interaction level, name it in the brief as the UX design round's decision and let the [UX design stage](spec.md) put coded options to the client. You build no prototype yourself.
- Work only a person can do becomes a human-work issue per [requests](rounds.md).
- A new domain term goes into the project's `GLOSSARY.md` through `domain-modeling`.
- A durable decision is written to the brain's pages for the project as the brain's `AGENTS.md` directs.

A grilling that leaves open decisions on more than one spec's worth of work has produced fog: open a map per [iteration](iteration.md) and work it below.

## Working a map

Drive the map with `wayfinder`. Only you edit the map body.

- **Research tickets** → one background subagent per ticket, in parallel, each running `research` and resolving its own ticket.
- **Grilling tickets** → a request, its questions in the `grilling` format, worked as above.
- **A decision ticket that turns out to be work** (a bug, a structural problem, a product change the client has decided) → an intake: triage it per [triage](triage.md).
- The map's Decisions-so-far stays an index; durable decisions go to the brain's pages.

## Spec brief

A slice is ready when the client has decided every behaviour in it, each decision with its basis, and the only decisions left are the ones its UX design round will settle on prototypes.

Write the brief from `~/repos/wellgent-skills/templates/artifacts/spec-brief.md` as the spec issue's body; in a map, add native blocking edges to the sibling specs it must follow.
Append `flow ledger stage shape <owner>/<repo>#<spec> done <issue link>`.
Re-ask the two questions of [triage](triage.md) on the brief: a brief that turned out small takes the one-shot path; otherwise start the spec's stages per [spec](spec.md).
