---
name: build
description: The Build stage of the development flow - one ticket, a batch or a spec built on its own branch, or a fix run on gate flags or Review and QA findings, ending at the gate.
disable-model-invocation: true
---

# Build

- **Role:** implementers inside one session (step `build`); the lead runs the **gate**.
- **Runs:** per landing (a one shot, a batch or a spec), and as a fix run for each batch of Review or QA findings.
- **Input:** one ticket, a batch, or the spec and its ticket graph; the design note when one exists; the design branch for a spec.
- **Output:** the branch tip with every ticket merged, a Build run comment, and a gate result with its diff class.
- **Quality bar:** `flow gate` passes on the branch tip: the check command and the journey tests green, the protected-change script clean on the whole diff; a fix run has run `code-review` plus the correctness pass on its own diff and fixed what it confirms; a session that changes files has the check green before it reports, a session that changes none runs no check; a decision the ticket lacks or a hard-to-reverse thing it did not name is a conflict exit; an answer that departs from a contract example, an invariant or an ADR sentence names that sentence and its new wording, and the fix run edits it.
- **Tools:** `implement-spec` unpatched for a spec (`tdd`, its own `code-review`); `implement` for a one shot or a batch, with `diagnosing-bugs` for a bug; the `AGENTS.md` must-read list; `flow gate`.

You run Build for the target named in your start prompt: a ticket, a batch or a spec.
The header above is this stage's entry in `FLOW.md`; terms are in `GLOSSARY.md`, both at the root of this repository.

`implement-spec`, `implement`, `tdd`, `code-review` and `diagnosing-bugs` are pinned in the project; when the harness does not list one, read its `SKILL.md` from the project's skills directory and follow it as written.
The project's `AGENTS.md` carries the rules every implementer works under: check before report, the conflict exit, the test tiers and the must-read list.
An implementer subagent proves its tickets with the lint, the typecheck and the test files its diff touches; the full check runs once per run, in [Before reporting](#before-reporting).
A subagent's end arrives as the harness's task notification, which is what the session waits on.
This skill adds only what the flow needs around them.

## Pick the run

- **The lead's note names finding tickets, a failing check or gate flags** → [A fix run](#a-fix-run).
- **The target is labelled `batch`** → [A ticket or a batch](#a-ticket-or-a-batch).
- **The target has a ticket graph** (sub-issues) → [A spec](#a-spec).
- **The target is one ticket** → [A ticket or a batch](#a-ticket-or-a-batch).

## A spec

1. Create the integration branch `spec/<spec issue number>-<slug>` from the main branch in its own worktree, set up per the worktree section in `docs/agents/dev-loop.md`.
   When the spec has a design branch, `design/<spec issue number>`, merge it in first.
   The project checkout stays on the main branch.
2. From that worktree, run `implement-spec` on the spec, with that branch as its integration branch.
   The design record's "Test seams" are the agreed seams `tdd` asks about.
   The chosen prototype is the reference for what the screens show; its code is throwaway and is rebuilt test-first.
3. Finish per [Before reporting](#before-reporting).

## A ticket or a batch

A batch is a parent issue whose sub-issues are its tickets; it is built as one set on one branch.

1. Create the branch `ticket/<target issue number>-<slug>`, or `batch/<target issue number>-<slug>` for a batch, from the main branch in its own worktree, set up as for a spec.
2. When the lead's note names a design note, read it on its ticket.
   Its contract examples are tests with the note's literal values.
   A note that links an ADR on `design/<ticket number>`: merge that branch in first.
3. A bug ticket goes through `diagnosing-bugs` first, until a failing test reproduces the report with the report's own values.
   That test is the bug's acceptance test.
   A bug whose correct fix has no seam to land at, because the modules as they stand put the behaviour in the wrong place, is a structural problem: post the diagnosis as a comment on the bug ticket and push the repro test.
   On a one shot, end there with `flow report no-correct-seam <link to the comment>`; in a batch, send it to the lead as a conflict exit and build the rest.
4. Run `implement` in this session on the ticket, or on the batch's open sub-issues as its set of tickets, one commit per ticket.
5. Finish per [Before reporting](#before-reporting).

## A fix run

Work in the worktree the newest Build run comment names, and note the tip the run starts on.

1. Fix what the note names:
   - **Finding tickets**: one implementer fixes every ticket the note names, with `tdd`.
     A finding that carries a failing repro test names the test's commit: cherry-pick it onto the branch, and the finding is fixed when that test passes unchanged.
     A finding whose steps ran on a deployment is fixed when those steps, replayed on the worktree's deployment, give the expected answers.
   - **A failing check**: fix the cause in the code.
   - **Gate flags**: each flag names a file and line.
     Restore the test, check setting or line the flag points at, or give it what the lead's note says it lacks.
   - **A ruling that departs from a source of truth**: when the note or a reply from the lead names a contract example, an invariant or an ADR sentence with its new wording, edit that sentence where it lives (the ADR file on the branch, or the design record or design note comment on its issue) and make the code and tests follow it.
2. Review your own diff from the tip the run started on, each pass in a fresh subagent:
   - `code-review` as written on that diff;
   - the correctness pass, with the brief in `stages/review/SKILL.md` step 3.

   Read the code at every reported line and fix each finding you confirm there.
3. Finish per [Before reporting](#before-reporting).

## The conflict exit

The work on a ticket stops and is reported, in place of deciding, when:

- the ticket, its tests or the spec disagree;
- the ticket needs a decision it does not hold;
- the ticket touches a hard-to-reverse thing it does not name: stored-data shape or a migration, an external contract (MCP tools, agent skills, a public API), money, authorization, a production delete.

An implementer reports it to you; you send it to the lead with `flow ask --conflict "<ticket>: <what disagrees with what, or the decision or edge it lacks>"` and carry the lead's reply back.
Tickets the conflict does not block keep running.
A ticket the lead takes out of a batch leaves the run, and the batch is built without it.
A ticket that turns out larger than it looked is built in full: size is the lead's to judge, at the triage and the gate.

Every other question an implementer cannot settle from the ticket, the spec, the design note or record, or the code goes to the lead with `flow ask`.

## Before reporting

1. The branch tip holds every ticket of the run, apart from tickets the lead took out.
   A run that changed files has the project's check command green on its final tip, run once after its own review's fixes landed; a run that changed none runs no check.
2. Push the branch.
   Landing is the lead's: the main branch stays untouched.
3. Post one comment on the target issue, headed "Build run":
   - the branch, its tip commit and the worktree path;
   - `tickets=<n>`, the number of tickets merged in this run, with their links, and each ticket taken out of the run with the lead's reason;
   - each test removed, skipped or weakened, each check setting loosened and each inline suppression added, with the ticket that asked for it;
   - on a fix run, each finding its own review confirmed and the commit that fixed it, each source-of-truth sentence it edited, and each deployment step replayed with its answer.
4. End the session with `flow report done <link to the comment>`.
