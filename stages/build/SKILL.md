---
name: build
description: The Build stage of the development flow - one spec built on its integration branch with implement-spec, a batch of findings fixed on it, or one bug ticket diagnosed and fixed.
disable-model-invocation: true
---

# Build

- **Role:** implementers and merger inside one session (step `build`); the lead runs the **gate**.
- **Runs:** per spec, and again for each batch of Review or QA findings.
- **Input:** the spec and ticket graph, or one bug ticket.
- **Output:** the integration branch with every ticket merged, and a gate result.
- **Quality bar:** `flow gate` passes on the branch tip: the check command green and the protected-change script clean on the whole spec diff.
- **Tools:** `implement-spec` unpatched (`tdd`, its own `code-review`); for a single bug `diagnosing-bugs` and `implement`; the `AGENTS.md` must-read list; `flow gate`.

You run Build for the target named in your start prompt.
The header above is this stage's entry in `FLOW.md`; terms are in `GLOSSARY.md`, both at the root of this repository.

`implement-spec`, `implement`, `tdd`, `code-review` and `diagnosing-bugs` are pinned in the project; when the harness does not list one, read its `SKILL.md` from the project's skills directory and follow it as written.
The project's `AGENTS.md` carries the rules every implementer and the merger work under: the check command green before reporting or merging, the conflict exit, the test tiers and the must-read list.
This skill adds only what the flow needs around them.

## Pick the run

- **The lead's note names failing checks, gate flags or finding tickets** → [A fix run](#a-fix-run).
- **The target has a ticket graph** (sub-issues) → [A spec](#a-spec).
- **The target is a single bug ticket** → [A bug ticket](#a-bug-ticket).

## A spec

1. Create the integration branch `spec/<spec issue number>-<slug>` from the main branch in its own worktree, set up per the project's worktree section in `docs/agents/dev-loop.md`.
   When the spec has a design branch, `design/<spec issue number>`, merge it in first.
   The project checkout stays on the main branch.
2. From that worktree, run `implement-spec` on the spec, with that branch as its integration branch.
   The design record's "Test seams" are the agreed seams `tdd` asks about.
   The chosen prototype is the reference for what the screens show; its code is throwaway and is rebuilt test-first.
3. Finish per [Before reporting](#before-reporting).

## A fix run

Work in the worktree that holds the integration branch.

- **Finding tickets**: one implementer fixes every ticket the note names, with `tdd`.
  A finding that carries a failing repro test is fixed when that test passes unchanged.
- **A failing check**: fix the cause in the code.
- **Gate flags**: each flag names a file and line.
  Restore the test, check setting or line the flag points at, or give it what the lead's note says it lacks.

Then finish per [Before reporting](#before-reporting).

## A bug ticket

1. Create the branch `fix/<ticket number>-<slug>` from the main branch in its own worktree, as for a spec.
2. Run `diagnosing-bugs` on the ticket until a failing test reproduces the report with the report's own values.
   That test is the bug's acceptance test.
3. A bug whose correct fix has no seam to land at, because the modules as they stand put the behaviour in the wrong place, is a structural problem.
   Stop there: post the diagnosis as a comment on the ticket, push the branch with the repro test, and end with `flow report no-correct-seam <link to the comment>`.
4. Otherwise run `implement` on the ticket in the same session, then finish per [Before reporting](#before-reporting).

## The conflict exit

When a ticket, its tests or the spec disagree, the work on that ticket stops and the disagreement is reported in place of making them agree.
An implementer reports it to you; you send it to the lead with `flow ask --conflict "<ticket>: <what disagrees with what>"` and carry the lead's reply back.
Tickets the conflict does not block keep running.

Every other question an implementer cannot settle from the spec, the design record or the code goes to the lead with `flow ask`.

## Before reporting

1. The branch tip holds every ticket of the run, and the project's check command is green on it.
2. Push the branch.
   Landing is the lead's: the main branch stays untouched.
3. Post one comment on the target issue, headed "Build run":
   - the branch, its tip commit and the worktree path;
   - `tickets=<n>`, the number of tickets merged in this run, with their links;
   - each test removed, skipped or weakened, each check setting loosened and each inline suppression added, with the ticket that asked for it.
4. End the session with `flow report done <link to the comment>`.
