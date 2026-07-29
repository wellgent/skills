# Dev-loop protocol

The shared semantics of the dev loop: how orchestrator sessions, specs, tickets, takes, and gates work.
This document ships with the `orchestrate` skill and is read in place - it is not copied into projects, and skill updates carry protocol updates with no per-project reconcile.
The project's contract at `docs/agents/dev-loop.md` declares what is project-specific (ports, scripts, gate proofs - see [dev-loop-declarations.md](dev-loop-declarations.md)); on conflict, the contract wins - a deviation is a decision, stated there, never silent drift.
The tracker is the loop's only memory: any session must be able to decide what to do - and recover from a died session - from tracker state alone.

## Operating model

- Work runs in **orchestrator sessions**: human-launched, one spec at a time.
  The session grooms the spec if ungroomed, delivers its board, and closes the spec - the spec boundary is the handoff seam: the session ends there, or rolls into the next spec when real context headroom remains.
- Roles are fixed.
  The **driver** grooms, gates, lands, pushes, and owns every tracker write.
  The **implementer** is always a spawned fresh session - never the driver's own context.
- Sessions are single-flight: at most one orchestrator session runs at a time.
  The crash-recovery rules below depend on this.

## Invocation

`/orchestrate [spec]` launches a session.
The no-arg form is canonical: run the session-start procedure and take what it selects.
The argument is a human override that picks among legal choices only: it refuses a blocked or claimed spec, and an open `fix-main` ticket still outranks it.
One spec at a time, never a guaranteed deliverable - a session may fix main, clear a standalone ticket, only groom, or exit mid-board at a ticket boundary.
A closed spec is a continuation seam: when real context headroom remains, the session may re-run selection and roll into the next spec - one spec remains the normal session; continuation is the exception headroom earns, and never starts a spec the session might not finish gating.
Every continuation is declared in its reports (see Session end).

## Hierarchy: specs and tickets

Two tiers, nothing else.

- A **spec issue** (label `spec`) is the parent: the durable what-and-why, published by `/to-spec`.
  Ordering between bodies of work is native blocking edges **between spec issues**.
  A body of work too big for one spec becomes several specs with edges.
- A **ticket** is a native **sub-issue** of its spec, published by grooming (`/to-tickets`), with blocking edges among siblings.
  Parentless tickets are legal for small standalone work.
- No milestones.
  The closed spec issue is the durable done-marker; closing it is what unblocks the next spec.

## Labels and claims

Two independent dimensions:

- The **label** carries lifecycle state: `ready-for-agent`, `in-progress`, `needs-human` (plus the triage states, see the project's `triage-labels.md`).
- The **assignee** carries the claim: assigned means a live session owns it right now.
  Every claim is "assign yourself"; every clean handback is "unassign".

Ticket lifecycle:

    ready-for-agent → in-progress → closed        (delivery: take + gate + land, atomic in-session)
    in-progress → ready-for-agent                 (died-session revert)
    any → needs-human                             (escalation: budget spent, or a decision only the human can make)
    needs-human → ready-for-agent | closed        (the human unblocks and hands back, or kills it)

`needs-human` means exactly one thing: the loop is blocked on human input.
The human never implements - they answer, decide, or re-scope, then flip back to `ready-for-agent` or close.

## Spec state is derived, never stored

- Open, unblocked, no sub-issues → **ungroomed**: groomable.
- `in-progress` + assigned → **being groomed** (or a died groom - see crash safety).
- Sub-issues exist, spec not `in-progress` → **board live**: drive the tickets.
- All sub-issues closed → **done**: close the spec.

## Grooming protocol

See the driver skill for the full protocol; the state moves are: claim (`in-progress` + assign) → breakdown + quiz → publish sub-issues → unclaim (the atomic "board is live" flip).
Never groom ahead: a spec is only groomable when its blocking specs are closed, so tickets are always written against the codebase they land on.

## Crash safety

Under single-flight, **any assigned item at session start is a died session**.
Recovery is mechanical, per state:

- Ticket `in-progress` + assigned → revert to `ready-for-agent`, unassign.
  Take commits sit on the dead session's take worktree, which the workspace preflight removes; nothing to salvage.
- Spec `in-progress` + assigned → **wipe-and-regroom**: close the orphaned sub-issues, revert the spec to `ready-for-agent`, unassign.
  Grooming is cheap; a partial-publish reconciliation protocol is not.

## Session-start procedure

Every orchestrator session runs this before any work:

1. **Workspace preflight** - a dirty tree hard-stops the session with a report of what it found; only work the session can identify may be stashed, committed, or discarded.
   Then `git fetch` and rebase onto the default branch, health-check the browser-verification tooling, reap stale loop-owned dev servers on the contract's gate and takes ports via its dev-server script - never the off-loop port, which belongs to work outside the loop - and remove stale take worktrees with their branches (leftovers are died sessions).
   No dev server is started here: servers stay ephemeral, spun up when a gate needs one.
2. **Recovery sweep** - find assigned items, apply the crash-safety table above.
3. **Tracker preflight** - read CI and deploy status on the default branch's head.
   Either red → find-or-create the `fix-main` ticket (label `fix-main` + `ready-for-agent`, title names the failing check and sha, body carries the evidence); at most one open at a time.
   Green with a stale open `fix-main` → close it with a note.
4. **Select**, in priority order:
   1. the open `fix-main` ticket - fixing main outranks all other work;
   2. the oldest open, unblocked, unassigned `ready-for-agent` ticket;
   3. the first open, unblocked, ungroomed `ready-for-agent` spec;
   4. nothing → say so and stop.

`needs-triage` and `needs-info` items are invisible to the loop; triage is a separate surface.

## Session end

Every session, however it exits:

- **Teardown** - stop loop-owned dev servers and browser sessions.
- **Report** - one spec-level comment per spec driven: the closing comment when the spec closes, a status comment otherwise.
  A session that touched no spec lands the same report on the last ticket it delivered.
  It summarizes tickets shipped, bounces, escalations, and commits, names the driver session id literally (never "this session") plus, when the session drove more than one spec, this spec's ordinal within it - the anchor for post-factum cost attribution - and ends with the loop's blockers: open `needs-human` items and whether any ready spec remains.
- **Observations** - anything actionable (a tooling defect, a gate blind spot, a skill gap) becomes an issue labelled `needs-triage`; narrative context goes in the report's Observations section.

Mid-board exits happen at ticket boundaries only.
At each boundary the driver checks its own context pressure and stops rather than starting a take it might not gate - the take's commits are local and die with the session.
Anything the next session needs goes as a comment on the relevant ticket; the tracker is the only handoff surface.
Resuming is just invoking the driver skill again.

## Between sessions

The human side of the seam - pull-based, no fixed cadence:

1. Read the last session's report comment - the single catch-up surface.
2. Clear `needs-human` items: answer, re-scope, or kill; each flips back to `ready-for-agent` or closes.
3. Triage `needs-triage`, including observation issues filed by sessions.
4. Refill the spec pipeline via `/to-spec` when few unblocked, ungroomed specs remain.
   Writing specs ahead is fine; only grooming ahead is forbidden.

## The implementer contract

Grooming breakdowns come from a fresh subagent of the driving harness.
Takes are fresh sessions at token-zero on the driving harness's **native subagent mechanism** - whichever harness runs the driver runs the takes; there is no per-project executor choice.
Only an explicit invocation-time request routes takes through an external runner instead (the skill's `runners/` folder, e.g. `runners/codex.md`).
Whichever way a take spawns, the contract holds:

- Fresh session at token-zero; the prompt carries the complete spec and grounding pointers.
- The take works in its **own worktree** on a take branch, never in another session's working copy - the harness's native worktree isolation when it has one, plain `git worktree` otherwise.
  The driver scaffolds it per the contract's worktree scaffold line (untracked env files, dependency install) and removes it, branch included, once the ticket lands or escalates.
- Worktrees isolate files, not shared runtime: the dev backend is still one per project, so sessions stay single-flight.
- The session is continuable - the groom quiz loop and delivery bounces resume the same session, same worktree.
- A terse report comes back; the driver never reads raw logs wholesale.
- Commits stay local and unpushed; every tracker write and every push belongs to the driver.

## Two reviews, by design

- The implementer **self-reviews** inside the take (`/implement` ends with `/code-review`).
  Cheap pre-flight; shares the author's blind spots by construction.
  The review runs inline in the take's own context - both axes sequentially, overriding the code-review skill's parallel sub-agents; a take never spawns sub-agents and never blocks waiting on agent messages or notifications.
- The driver **gates** in the delivery loop: the four axes (spec fidelity, repo standards, design direction, elegance) judged on the diff with fresh eyes, plus the fact re-run - the driver re-runs checks and `/verify` itself, never trusting the report.
  The gate verdict is non-delegable.
  Push only on green: a push to the default branch deploys in most setups.

## Gate proofs

The project's check command is the baseline fact re-run; the contract's **Gate proofs** section maps diff shapes to the repo-specific proofs that cover what the check command structurally cannot see - the gate runs what production runs.
The same section names advisory review inputs per surface (never pass/fail).
Both the gate and take prompts consume it.

## Skill map

- `/to-spec` - conversation → spec issue (from the engineering skill set).
- `/orchestrate` - the driver loop: session-start procedure, then specs end to end - grooms via a fresh subagent following `/to-tickets`, delivers via fresh takes following `/implement`, gates itself.
- Source of truth for the driver skill and this protocol is wellgent/skills, pinned in `skills-lock.json`.
