---
name: orchestrate
description: Run one dev-loop session as the driver - preflight, select, one spec end to end. Harness-generic - grooming drafts run in fresh subagents of the driving harness; takes run on the executor the project contract names (native subagents by default, or an external harness via a runner file); the gate stays yours.
argument-hint: "[spec issue ref or URL - omit to let the session-start procedure select]"
disable-model-invocation: true
---

# Orchestrate (dev-loop driver)

One orchestrator session: preflight, select, drive **one spec** end to end, tear down, report.
Roles are fixed.
You (the agent running this skill, in whatever harness) are the **driver**: you groom, gate, land, push, and own every tracker write.
The **executor** implements: every take runs in a fresh session at token-zero on the take executor the contract names - your harness's native subagent mechanism unless the contract names an external runner (see The take).
Grooming breakdowns come from a fresh subagent of your own harness - one session shapes spec, another builds to spec, and review never leaves you.

The state contract is `docs/agents/dev-loop.md`; tracker mechanics are `docs/agents/issue-tracker.md`.
Read both before the first write - the contract's rules win over this summary.
The tracker is the loop's only memory: a session can die at any point, and the next one recovers from tracker state alone.

## Invocation

The no-arg form is canonical: run the session-start procedure and take what it selects.
A spec argument is a human override that picks among **legal choices only**: refuse a blocked or claimed spec, and an open `fix-main` ticket still outranks it.
One spec per session is the ceiling, not a guaranteed deliverable - a session may fix main, clear a standalone ticket, only groom, or exit mid-board at a ticket boundary.

## Session start

Per the contract's session-start procedure, in order:

1. **Workspace preflight** - a dirty tree hard-stops the session with a report of what you found; only work you can identify may be stashed, committed, or discarded.
   Then `git fetch` + rebase onto `origin/main`, health-check the browser tooling, and reap stale loop-owned dev servers on the contract's gate and takes ports - the human's interactive port is untouchable.
   Servers stay ephemeral: spun up when a gate needs one, none started here.
2. **Recovery sweep** - any assigned open item is a died session (the loop is single-flight).
   Apply the contract's recovery table: `in-progress` ticket → revert to `ready-for-agent` and unassign; `in-progress` spec → **wipe-and-regroom** (close its orphaned sub-issues, revert, unassign).
3. **Tracker preflight** - read CI and deploy status on `main`'s head.
   Either red → find-or-create the single open `fix-main` ticket (title names the failing check and sha, body carries the evidence).
   Green with a stale open `fix-main` → close it with a note.
4. **Select**, in priority order: the open `fix-main` ticket; else the oldest open, unblocked, unassigned `ready-for-agent` ticket; else the first open, unblocked, ungroomed `ready-for-agent` spec; else say so and stop.
   `needs-triage` and `needs-info` items are invisible to the loop.

## Driving the spec

- Selected a **spec** → groom it (below), then drive its fresh board.
- Selected a **ticket** → deliver it (below); when it belongs to a spec, continue with that spec's board.
- Repeat delivery on the board's frontier - oldest open, unblocked, unassigned ticket - one ticket at a time.
- **Ticket boundaries are the exit seams.** At each boundary check your own context pressure and stop rather than start a take you might not gate - take commits are local and die with the session.
  Anything the next session needs goes as a comment on the relevant ticket; the tracker is the only handoff surface.
  Resuming is just invoking this skill again.
- All sub-issues closed → **close the spec**; the closed spec is the durable done-marker that unblocks its dependent specs, and its closing comment is the session report.

## Grooming a spec

Never groom ahead: a spec is groomable only when its blocking specs are closed, so tickets are written against the codebase they land on rather than an imagined one.

1. **Claim the spec**: flip `ready-for-agent` → `in-progress` and assign yourself, before any other work.
2. **Spawn a fresh subagent** whose prompt directs it to follow the repo's `to-tickets` skill **through its drafting steps only** (gather context, explore the codebase as it stands today, draft vertical tracer-bullet slices with blocking edges) and report the breakdown back - the skill's quiz step is the exchange with you below, and its publish step is yours.
   The report carries, per ticket: title, full body (acceptance criteria included), and its blocking edges.
3. **Quiz the breakdown.** The to-tickets quiz is yours to answer - judge it as the human would:
   - **Granularity** - each slice fits one fresh context window and is demoable alone.
   - **Edges** - only genuine gates, nothing serialized out of caution.
   - **Coverage** - every requirement of the spec lands in some ticket.
   - **Reality** - verify any "already exists, no ticket needed" claim against the code yourself before accepting it.
   Iterate by continuing the same subagent when your harness can resume one; otherwise spawn a fresh subagent carrying the prior breakdown plus your objections.
4. **Publish it yourself** - every tracker write is the driver's, running `to-tickets`' publish step: one ticket per slice using its issue template, in dependency order (blockers first, so edges reference real ids), each a native sub-issue of the spec with native blocking edges among siblings and `ready-for-agent` on it.
   Verify the publication: enumerate the sub-issues, spot-check the edges.
5. **Unclaim the spec**: drop `in-progress`, unassign - the atomic "board is live" flip.
   A spec with sub-issues but still `in-progress` is a half-published board and never selectable.

## Delivering a ticket

One ticket → closed, atomic in-session: take + gate + land.
Start from a **clean working tree** on the branch the ticket lands on - the diff you gate must be exactly the take.

1. **Claim**: flip `ready-for-agent` → `in-progress`, assign yourself - before any work.
2. **Take**: spawn a fresh take session on the contract's executor (see The take). Each attempt is a **take**; every take commits, so the issue timeline reads as the full attempt history.
3. **Gate** (see The gate). Green → step 5; not green → step 4.
4. **Bounce**: comment the specific defect on the issue - the auditable record of what review found - then **continue the same take session** with the finding and the fix expectation, same contract. Re-gate at step 3.
   Budget is **three takes**; if the third still misses, escalate: label `needs-human`, drop `in-progress`, unassign, and leave the commits and comments in place as the record.
   The driver stays out of the code - escalation, not takeover.
5. **Land and close**: scan the take's commit messages for wrong `#<N>` mentions and for closing-keyword + `#<N>` collisions, amend any before pushing, then push the take commits, comment what shipped (including token telemetry - see Telemetry), and close the issue - closing is what unblocks its dependents.
   **Push only on green**: red takes never reach the remote - in most setups a push to main deploys production.
6. **Teardown**: stop any dev server or browser session the gate started.

### The take

Every take is a fresh session at token-zero on the **take executor**, working in the same checkout on the same branch.
The contract's implementer section names the executor; the branch decides the mechanics:

- **Native subagents** (the default) - spawn the take with your harness's native subagent mechanism.
  Bounces continue the same take session where your harness can resume one - cheaper than fresh, and the take's context survives; where it cannot, spawn a fresh subagent whose prompt carries the original contract verbatim, the prior take's report, and the bounce finding.
- **External runner** - the contract names a runner file in this skill's `runners/` folder; follow it for spawn, resume, and take metering.
  [`runners/codex.md`](runners/codex.md) runs takes as `codex exec` sessions.

Either way a bounce continuation counts against the three-take budget.
Long takes run in the background where the harness supports it; let quiet runs under 30 minutes keep working.
Your context takes only the take's final report - never pull the take's transcript, diffs, or file dumps into the driver session; the gate reads the diff from git, not from the report.

**The prompt contract.** The take starts with zero context - no spec thread, no driver conversation, no house rules beyond what its harness injects.
Spec quality decides the take.
Every take prompt carries:

- the goal: issue number, title, and full body verbatim (acceptance criteria included), plus the parent spec reference - inline the spec's own language for the parts this ticket implements
- the process pointer: follow the project's `implement` skill (`.agents/skills/implement/`) if present
- grounding pointers: the repo's domain glossary (`CONTEXT.md`), any generated stack guidelines the repo ships (they override trained knowledge), and the design-direction docs when the issue has UI surface
- constraints and non-goals lifted from the issue
- proof expected: the project's exact check command, plus every deploy-shaped proof the diff will trigger per the contract's Gate proofs section - the take runs them too, so bounces are cheap
- runtime rules: if the take needs a running app, it spins up its own ephemeral server via the dev-server script and takes-port the contract names, and stops it on exit
- commit rules: commit locally referencing `#<N>` as a plain mention - the mention must not directly follow any GitHub closing keyword (fix, fixes, fixed, close, closes, closed, resolve, resolves, resolved), even in ordinary prose, since GitHub would auto-close the issue before the gate runs; reword the sentence if needed - and **never push**
- delegation rule: the take does its own work - it never spawns nested agent sessions or shells out to another agent CLI, which would hide tokens and code provenance from the loop
- output shape: a terse report only - what shipped, proofs green (y/n), files touched, commit shas, blockers hit

### The gate

Review is never delegated and never skipped.

**The diff first.** `git status -sb`, then read the full diff and judge it like a contributor PR, on four axes:

- **Spec fidelity** - every acceptance criterion met, nothing shipped beyond the issue's scope.
- **Repo standards** - the glossary's vocabulary, the established patterns (function builders, test seams, fixtures), the generated stack guidelines; new code reads like the code around it.
- **Design direction** - UI diffs against the repo's standing design docs; flag drift rather than restyling by taste.
- **Elegance** - the diff earns its size: reuse over reinvention, no gratuitous abstraction, tests assert behavior at settled seams rather than implementation detail.

**Then the facts.** The report is a claim; the fact is your own re-run.
Run the project's check command yourself, and verify the app end to end (the repo's verify skill, if it ships one) when the issue has runtime surface - on your own ephemeral dev server (the contract's gate port), with the human's interactive port untouched.

**Deploy-shaped proofs.** The local check chain structurally cannot see deploy-only failures; the gate runs what production runs.
The contract's **Gate proofs** section maps diff shapes to the repo's proof commands (schema changes, destructive data changes, production-build-only errors); run every proof the diff triggers.

**Advisory signals.** The same section names the repo's review skills and analyzers per surface (UI guidelines, stack analyzers, copy review); run the ones the diff touches and weigh their findings as review input on the standards/elegance axes - never as a pass/fail gate step.

### Telemetry

Token accounting is measured, never estimated, and covers everything the session ran: the driver's own session, every subagent it spawned, and every take on the executor.
How to read the numbers is harness-specific; what must be recorded is not.

**What a number is.** Token categories differ in cost by orders of magnitude, so a number is only a measurement with its category label on it: record every category the harness reports - output at minimum, plus fresh-input, cache-creation, and cache-read input where reported.

**Per ticket** - the shipped comment carries the numbers, so every issue thread is self-sufficient for later cost analysis:

1. The takes: record each take's token usage from its executor's native accounting (subagent completion reports where the harness meters subagents individually; the runner file's metering recipe for an external executor), plus whatever session or subagent id the executor assigns - the handle later analysis needs.
2. The driver: record a cumulative snapshot at ticket close, keyed by the driver session id, and say explicitly whether subagent tokens sit inside or outside that counter - so later analysis can diff consecutive snapshots sharing a session id without double-counting or dropping a side.
   Where the harness shows no live counter, its session log on disk is the measured source - sum the per-call usage records there.
   When Claude Code is the driving harness, [`telemetry-claude-code.md`](telemetry-claude-code.md) carries the exact transcript paths and queries.

**At session end** - the session report repeats the final snapshot and the per-take numbers across the session's tickets: the total accounting for the session.

**Coverage invariant** - every token the session caused lands in some recorded counter.
Subagents and runner takes are metered by their own harnesses; the only leak is a take shelling out to a nested agent CLI (`codex exec`, `claude -p`, ...) whose tokens no recorded counter carries.
The prompt contract forbids it; still scan the take's report and command history for nested agent spawns and flag any in the shipped comment rather than silently under-counting.

## Session end

Every session, however it exits:

- **Teardown** - stop loop-owned dev servers and browser sessions.
- **Report** - exactly one spec-level comment: the closing comment when the spec closes, a status comment otherwise.
  It summarizes tickets shipped, bounces, escalations, and commits, carries the session telemetry block (driver, grooming subagents, takes - see Telemetry), and ends with the loop's blockers: open `needs-human` items and whether any ready spec remains.
- **Observations** - anything actionable (a tooling defect, a gate blind spot, a skill gap) becomes its own issue labelled `needs-triage`; narrative context goes in the report's Observations section.
